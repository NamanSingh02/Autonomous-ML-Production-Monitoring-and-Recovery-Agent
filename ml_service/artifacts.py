"""Recording artifact integrity and runtime compatibility information."""

import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

RUNTIME_PACKAGES = ("numpy", "scipy", "scikit-learn", "joblib")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def runtime_versions() -> dict[str, str]:
    versions = {name: importlib.metadata.version(name) for name in RUNTIME_PACKAGES}
    versions["python"] = ".".join(platform.python_version_tuple()[:2])
    return versions


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
