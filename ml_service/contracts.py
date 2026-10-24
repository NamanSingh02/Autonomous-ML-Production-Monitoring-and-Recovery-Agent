"""Defining the shared training and serving feature contract."""

import re

import numpy as np

FEATURE_BOUNDS = {
    "temperature": (0.0, 120.0),
    "vibration": (0.0, 20.0),
    "pressure": (0.0, 20.0),
    "operating_hours": (0.0, 50_000.0),
    "load": (0.0, 100.0),
}
FEATURE_NAMES = tuple(FEATURE_BOUNDS)
PREPROCESSING_VERSION = "sensor-contract-v1"
GENERATOR_VERSION = "equipment-v1"
CLASS_THRESHOLD = 0.5
EXAMPLE_FEATURES = dict(zip(FEATURE_NAMES, (65.0, 5.0, 8.0, 12_000.0, 55.0)))


def validate_version(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", value):
        raise ValueError("Version must contain 1-64 letters, digits, dots, underscores, or hyphens.")
    return value


def validate_matrix(values: np.ndarray) -> None:
    if values.ndim != 2 or values.shape[1] != len(FEATURE_NAMES) or not len(values):
        raise ValueError("Features must be a nonempty matrix with five ordered columns.")
    if not np.isfinite(values).all():
        raise ValueError("Features must contain only finite numbers.")
    for column, (lower, upper) in enumerate(FEATURE_BOUNDS.values()):
        if np.any((values[:, column] < lower) | (values[:, column] > upper)):
            raise ValueError(f"Feature {FEATURE_NAMES[column]} is outside its contract bounds.")


def feature_matrix(features: dict[str, float]) -> np.ndarray:
    values = np.asarray([[features[name] for name in FEATURE_NAMES]], dtype=np.float64)
    validate_matrix(values)
    return values
