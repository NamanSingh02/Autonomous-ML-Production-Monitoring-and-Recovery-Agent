"""Loading trusted model bundles after integrity and contract checks."""

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

from ml_service.artifacts import runtime_versions, sha256_file
from ml_service.contracts import (
    CLASS_THRESHOLD, EXAMPLE_FEATURES, FEATURE_BOUNDS, FEATURE_NAMES,
    PREPROCESSING_VERSION, feature_matrix, validate_version,
)


class ModelLoadError(RuntimeError):
    """Representing a rejected or unavailable model bundle."""


@dataclass(frozen=True)
class LoadedModel:
    estimator: RandomForestClassifier
    version: str
    preprocessing_version: str
    threshold: float

    def predict(self, features: dict[str, float]) -> tuple[float, int]:
        probability = float(self.estimator.predict_proba(feature_matrix(features))[0, 1])
        if not np.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("Model returned an invalid probability.")
        return probability, int(probability >= self.threshold)


def load_model(root: Path, version: str) -> LoadedModel:
    try:
        validate_version(version)
        directory = root.resolve() / version
        if directory.is_symlink() or directory.resolve().parent != root.resolve():
            raise ValueError("Model version must resolve directly inside the trusted model root.")
        metadata_path = directory / "metadata.json"
        if metadata_path.is_symlink():
            raise ValueError("Model metadata cannot be a symlink.")
        metadata = json.loads(metadata_path.read_text())
        expected = {
            "format_version": 1, "model_version": version,
            "preprocessing_version": PREPROCESSING_VERSION,
            "feature_names": list(FEATURE_NAMES),
            "feature_bounds": {name: list(bounds) for name, bounds in FEATURE_BOUNDS.items()},
            "class_threshold": CLASS_THRESHOLD, "classes": [0, 1],
            "estimator": "RandomForestClassifier", "quality_gate_passed": True,
            "runtime_versions": runtime_versions(),
        }
        for name, value in expected.items():
            if metadata.get(name) != value:
                raise ValueError(f"Model metadata is incompatible: {name}.")
        files = metadata.get("files", {})
        required = {
            "model.joblib", "metrics.json", "dataset_manifest.json",
            "reference.json", "model_card_metadata.json", "model_card.md",
        }
        if set(files) != required:
            raise ValueError("Model bundle file manifest is incomplete.")
        for name in required:
            path = directory / name
            if path.is_symlink() or sha256_file(path) != files[name]:
                raise ValueError(f"Model bundle checksum mismatch: {name}.")
        metrics = json.loads((directory / "metrics.json").read_text())
        for split in ("validation", "test"):
            quality = metrics[split]
            if not (
                0.80 <= quality["roc_auc"] <= 1
                and 0 < quality["positive_rate"] < 1
                and quality["positive_rate"] < quality["pr_auc_average_precision"] <= 1
            ):
                raise ValueError("Model quality metrics do not pass the release gate.")
        estimator = joblib.load(directory / "model.joblib")
        if not isinstance(estimator, RandomForestClassifier):
            raise ValueError("Model artifact must contain a RandomForestClassifier.")
        if estimator.n_features_in_ != len(FEATURE_NAMES) or list(estimator.classes_) != [0, 1]:
            raise ValueError("Model dimensions or class order do not match the contract.")
        loaded = LoadedModel(estimator, version, PREPROCESSING_VERSION, CLASS_THRESHOLD)
        loaded.predict(EXAMPLE_FEATURES)
        return loaded
    except Exception as error:
        raise ModelLoadError(f"Could not load model version {version}: {error}") from error
