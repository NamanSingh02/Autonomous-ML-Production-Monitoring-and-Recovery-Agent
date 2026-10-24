"""Training and publishing an immutable baseline model bundle."""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score, brier_score_loss, f1_score,
    precision_score, recall_score, roc_auc_score,
)

from ml_service.artifacts import runtime_versions, sha256_file, write_json
from ml_service.contracts import (
    CLASS_THRESHOLD, FEATURE_BOUNDS, FEATURE_NAMES, PREPROCESSING_VERSION, validate_version,
)
from ml_service.training.data import load_dataset


def evaluate(model: RandomForestClassifier, values: np.ndarray, labels: np.ndarray) -> dict:
    probabilities = model.predict_proba(values)[:, 1]
    predictions = (probabilities >= CLASS_THRESHOLD).astype(int)
    return {
        "rows": len(labels), "positive_rate": float(labels.mean()),
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "pr_auc_average_precision": float(average_precision_score(labels, probabilities)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "brier_score": float(brier_score_loss(labels, probabilities)),
    }


def model_card(metadata: dict, metrics: dict) -> str:
    feature_rows = "\n".join(
        f"| {name} | {bounds[0]} | {bounds[1]} |" for name, bounds in FEATURE_BOUNDS.items()
    )
    metric_rows = "\n".join(
        f"| {split} | {values['rows']} | {values['roc_auc']:.4f} | "
        f"{values['pr_auc_average_precision']:.4f} | {values['f1']:.4f} | "
        f"{values['precision']:.4f} | {values['recall']:.4f} | {values['brier_score']:.4f} |"
        for split, values in metrics.items()
    )
    return f"""# Equipment Failure Model Card

## Purpose

I trained {metadata['model_version']} to classify synthetic equipment operating snapshots.
The output is a failure probability and a binary class using threshold {CLASS_THRESHOLD}.
This model supports repeatable monitoring experiments; it is not validated for industrial safety decisions.

## Training Data

The equipment-v1 generator produced independent seeded training, validation, and test splits.
The nonlinear label function used a training-only calibrated intercept and Bernoulli sampling.
Training used only the training split; evaluation did not tune the model or threshold.
The bundled dataset_manifest.json records split sizes, seeds, prevalence, and checksums.

## Features and Expected Ranges

| Feature | Minimum | Maximum |
|---|---:|---:|
{feature_rows}

Temperature is measured in degrees Celsius, vibration in mm/s, pressure in bar,
operating_hours in hours, and load as a percentage. These are synthetic contract limits.
Preprocessing {PREPROCESSING_VERSION} preserves these units and the listed feature order;
it performs no scaling, imputation, or unit conversion. Missing or invalid features are rejected.

## Evaluation Metrics

| Split | Rows | ROC-AUC | PR-AUC (average precision) | F1 | Precision | Recall | Brier score |
|---|---:|---:|---:|---:|---:|---:|---:|
{metric_rows}

Validation and test ROC-AUC must each be at least 0.80 and average precision must exceed
the corresponding positive prevalence before the artifact is approved for serving.
Training prevalence must be between 20% and 40%. The serving gate passed for this bundle.

## Deployment Assumptions

I use one immutable version directory per model. Serving checks the feature contract,
artifact checksum, release gate, and exact recorded NumPy, SciPy, scikit-learn, and joblib
versions plus the Python major/minor version before loading the model.
The bundle is loaded only from a trusted local directory; its checksum detects corruption,
but does not establish authenticity. No user-supplied model upload is supported.

## Limitations

The labels and feature relationships are synthetic. Accuracy and probability calibration
may change under drift. The fixed threshold does not encode industrial failure costs.
Reported metrics do not establish serving latency, live availability, drift detection,
or autonomous recovery performance. Production traffic and delayed-label monitoring
are implemented in later phases.
"""


def train_model(
    data_dir: Path,
    model_root: Path,
    version: str = "baseline-v1",
    trees: int = 100,
    max_depth: int = 12,
    seed: int = 17,
) -> Path:
    validate_version(version)
    if not 1 <= trees <= 500 or not 1 <= max_depth <= 30:
        raise ValueError("Trees must be between 1 and 500 and max depth between 1 and 30.")
    model_root = model_root.resolve()
    destination = model_root / version
    if destination.exists():
        raise FileExistsError(f"Model version already exists: {version}. Choose a new version.")
    dataset_manifest, splits = load_dataset(data_dir)
    train_values, train_labels = splits["train"]
    if not 0.20 <= float(train_labels.mean()) <= 0.40:
        raise ValueError("Training prevalence must be between 20% and 40%.")
    parameters = {
        "n_estimators": trees, "max_depth": max_depth,
        "min_samples_leaf": 5, "random_state": seed, "n_jobs": 1,
    }
    model = RandomForestClassifier(**parameters)
    model.fit(train_values, train_labels)
    metrics = {name: evaluate(model, *splits[name]) for name in splits}
    approved = all(
        metrics[name]["roc_auc"] >= 0.80
        and metrics[name]["pr_auc_average_precision"] > metrics[name]["positive_rate"]
        for name in ("validation", "test")
    )
    if not approved:
        raise ValueError(
            "Baseline quality gate failed; no serving artifact was published. "
            f"Measured metrics: {json.dumps(metrics, allow_nan=False)}. "
            "Investigate the recipe using development data; do not tune against the held-out test split."
        )
    model_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".training-", dir=model_root))
    try:
        model_path = staging / "model.joblib"
        joblib.dump(model, model_path, compress=3)
        write_json(staging / "metrics.json", metrics)
        write_json(staging / "dataset_manifest.json", dataset_manifest)
        quantiles = np.linspace(0, 1, 11)
        validation_values, _ = splits["validation"]
        write_json(staging / "reference.json", {
            "source_split": "validation", "rows": len(validation_values),
            "feature_quantiles": {
                name: np.quantile(validation_values[:, index], quantiles).tolist()
                for index, name in enumerate(FEATURE_NAMES)
            },
            "probability_quantiles": np.quantile(
                model.predict_proba(validation_values)[:, 1], quantiles,
            ).tolist(),
            "quality": metrics["validation"],
        })
        metadata = {
            "format_version": 1, "model_version": version,
            "preprocessing_version": PREPROCESSING_VERSION,
            "feature_names": FEATURE_NAMES, "feature_bounds": FEATURE_BOUNDS,
            "class_threshold": CLASS_THRESHOLD, "classes": [0, 1],
            "estimator": "RandomForestClassifier", "parameters": parameters,
            "runtime_versions": runtime_versions(), "quality_gate_passed": True,
            "training_source_sha256": sha256_file(Path(__file__)),
        }
        write_json(staging / "model_card_metadata.json", metadata)
        (staging / "model_card.md").write_text(model_card(metadata, metrics))
        metadata["files"] = {
            name: sha256_file(staging / name)
            for name in (
                "model.joblib", "metrics.json", "dataset_manifest.json",
                "reference.json", "model_card_metadata.json", "model_card.md",
            )
        }
        write_json(staging / "metadata.json", metadata)
        staging.rename(destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Training a single-core versioned baseline model.")
    parser.add_argument("--data-dir", type=Path, default=Path("data/generated/equipment-v1"))
    parser.add_argument("--model-root", type=Path, default=Path("artifacts/models"))
    parser.add_argument("--version", default="baseline-v1")
    parser.add_argument("--trees", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--seed", type=int, default=17)
    arguments = parser.parse_args()
    try:
        result = train_model(
            arguments.data_dir, arguments.model_root, arguments.version,
            arguments.trees, arguments.max_depth, arguments.seed,
        )
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Training failed: {error}\n")
    print(f"Published model bundle: {result}")


if __name__ == "__main__":
    main()
