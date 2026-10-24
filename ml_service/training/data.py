"""Generating isolated synthetic data splits without external downloads."""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

import numpy as np

from ml_service.artifacts import sha256_file, write_json
from ml_service.contracts import FEATURE_NAMES, GENERATOR_VERSION, validate_matrix

DEFAULT_SIZES = {"train": 30_000, "validation": 5_000, "test": 5_000}


def sample_features(rng: np.random.Generator, count: int) -> np.ndarray:
    load = 100 * rng.beta(2, 2, count)
    temperature = np.clip(30 + 0.65 * load + rng.normal(0, 9, count), 0, 120)
    vibration = np.clip(
        1 + 0.06 * load + 0.12 * np.maximum(temperature - 65, 0) + rng.normal(0, 0.9, count),
        0, 20,
    )
    pressure = np.clip(8 + 0.025 * (load - 50) + rng.normal(0, 1.5, count), 0, 20)
    hours = 50_000 * rng.beta(2, 3, count)
    values = np.column_stack((temperature, vibration, pressure, hours, load))
    validate_matrix(values)
    return values


def risk_score(values: np.ndarray) -> np.ndarray:
    temperature, vibration, pressure, hours, load = values.T
    return (
        0.16 * (temperature - 65)
        + 1.15 * (vibration - 4.5)
        + 0.00006 * (hours - 20_000)
        + 0.45 * np.maximum(6 - pressure, 0)
        + 0.06 * np.maximum(load - 75, 0)
    )


def failure_probability(values: np.ndarray, intercept: float) -> np.ndarray:
    return 1 / (1 + np.exp(-np.clip(risk_score(values) + intercept, -40, 40)))


def calibrate_intercept(training_values: np.ndarray, target_rate: float = 0.30) -> float:
    lower, upper = -40.0, 40.0
    for _ in range(80):
        middle = (lower + upper) / 2
        if float(failure_probability(training_values, middle).mean()) < target_rate:
            lower = middle
        else:
            upper = middle
    return (lower + upper) / 2


def generate_dataset(output: Path, seed: int = 42, sizes: dict[str, int] | None = None) -> Path:
    output = output.resolve()
    sizes = dict(DEFAULT_SIZES if sizes is None else sizes)
    if set(sizes) != set(DEFAULT_SIZES) or any(size < 100 for size in sizes.values()):
        raise ValueError("Each train, validation, and test split needs at least 100 rows.")
    if output.exists():
        raise FileExistsError(f"Dataset already exists: {output}. Choose a new output directory.")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".dataset-", dir=output.parent))
    try:
        children = np.random.SeedSequence(seed).spawn(3)
        split_seeds = {
            name: int(child.generate_state(1, dtype=np.uint64)[0])
            for name, child in zip(DEFAULT_SIZES, children)
        }
        intercept = None
        splits = {}
        for name in DEFAULT_SIZES:
            count = sizes[name]
            rng = np.random.default_rng(split_seeds[name])
            values = sample_features(rng, count)
            if name == "train":
                intercept = calibrate_intercept(values)
            if intercept is None:
                raise ValueError("The training split must be generated before held-out splits.")
            labels = rng.binomial(1, failure_probability(values, intercept)).astype(np.int64)
            if len(np.unique(labels)) != 2:
                raise ValueError(f"The {name} split must contain both label classes.")
            path = staging / f"{name}.npz"
            np.savez_compressed(path, features=values, labels=labels)
            splits[name] = {
                "rows": count, "seed": split_seeds[name],
                "sha256": sha256_file(path), "positive_rate": float(labels.mean()),
            }
        write_json(staging / "manifest.json", {
            "format_version": 1, "generator_version": GENERATOR_VERSION,
            "root_seed": seed, "feature_names": FEATURE_NAMES,
            "target_positive_rate": 0.30, "intercept": intercept,
            "label_rule": "Bernoulli(sigmoid(risk_score(features) + intercept))",
            "recipe_source": "ml_service/training/data.py",
            "recipe_source_sha256": sha256_file(Path(__file__)),
            "numpy_version": np.__version__,
            "splits": splits,
        })
        staging.rename(output)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return output


def load_dataset(directory: Path) -> tuple[dict, dict[str, tuple[np.ndarray, np.ndarray]]]:
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest["format_version"] != 1 or manifest["generator_version"] != GENERATOR_VERSION:
        raise ValueError("Unsupported dataset manifest version.")
    if manifest["feature_names"] != list(FEATURE_NAMES):
        raise ValueError("Dataset feature order does not match the serving contract.")
    if set(manifest["splits"]) != set(DEFAULT_SIZES):
        raise ValueError("Dataset must contain exactly train, validation, and test splits.")
    seeds = [manifest["splits"][name]["seed"] for name in DEFAULT_SIZES]
    if len(set(seeds)) != 3:
        raise ValueError("Dataset split seeds must be distinct.")
    result = {}
    for name in DEFAULT_SIZES:
        path = directory / f"{name}.npz"
        if sha256_file(path) != manifest["splits"][name]["sha256"]:
            raise ValueError(f"Dataset checksum mismatch: {name}.")
        with np.load(path, allow_pickle=False) as data:
            values, labels = data["features"], data["labels"]
        validate_matrix(values)
        if len(values) != manifest["splits"][name]["rows"]:
            raise ValueError(f"Dataset row count mismatch: {name}.")
        if labels.shape != (len(values),) or set(np.unique(labels)) != {0, 1}:
            raise ValueError(f"Invalid binary labels in {name}.")
        result[name] = (values, labels)
    return manifest, result


def main() -> None:
    parser = argparse.ArgumentParser(description="Generating versioned synthetic equipment data.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/equipment-v1"))
    parser.add_argument("--seed", type=int, default=42)
    arguments = parser.parse_args()
    try:
        result = generate_dataset(arguments.output, arguments.seed)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Dataset generation failed: {error}\n")
    print(f"Generated dataset: {result}")


if __name__ == "__main__":
    main()
