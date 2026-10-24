"""Checking the baseline workflow using small temporary fixtures."""

import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ml_service.artifacts import sha256_file, write_json
from ml_service.contracts import EXAMPLE_FEATURES, FEATURE_NAMES, feature_matrix
from ml_service.inference.app import create_app
from ml_service.inference.runtime import ModelLoadError, load_model
from ml_service.inference.schemas import PredictionRequest
from ml_service.training.data import generate_dataset, load_dataset
from ml_service.training.train import train_model


class DatasetTests(unittest.TestCase):
    def test_seeded_splits_are_repeatable_and_disjoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sizes = {"train": 800, "validation": 200, "test": 200}
            first = generate_dataset(root / "first", sizes=sizes)
            second = generate_dataset(root / "second", sizes=sizes)
            manifest, splits = load_dataset(first)
            _, repeated = load_dataset(second)
            self.assertEqual(len(set(item["seed"] for item in manifest["splits"].values())), 3)
            rows = []
            for name in sizes:
                np.testing.assert_array_equal(splits[name][0], repeated[name][0])
                np.testing.assert_array_equal(splits[name][1], repeated[name][1])
                rows.extend(map(tuple, splits[name][0]))
            self.assertEqual(len(rows), len(set(rows)))
            self.assertAlmostEqual(manifest["target_positive_rate"], 0.30)
            with self.assertRaises(FileExistsError):
                generate_dataset(first, sizes=sizes)

    def test_modified_split_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = generate_dataset(Path(temporary) / "data", sizes=dict.fromkeys(("train", "validation", "test"), 200))
            with (root / "train.npz").open("ab") as stream:
                stream.write(b"changed")
            with self.assertRaisesRegex(ValueError, "checksum"):
                load_dataset(root)

    def test_feature_order_is_explicit(self):
        reversed_features = dict(reversed(list(EXAMPLE_FEATURES.items())))
        result = feature_matrix(reversed_features)
        self.assertEqual(result.tolist(), [[EXAMPLE_FEATURES[name] for name in FEATURE_NAMES]])


class ServingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.data = generate_dataset(cls.root / "data", sizes={"train": 800, "validation": 200, "test": 200})
        cls.models = cls.root / "models"
        cls.bundle = train_model(cls.data, cls.models, trees=8, max_depth=6)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_bundle_contains_provenance_metrics_and_model_card(self):
        metadata = json.loads((self.bundle / "metadata.json").read_text())
        for name, digest in metadata["files"].items():
            self.assertEqual(sha256_file(self.bundle / name), digest)
        self.assertEqual(metadata["feature_names"], list(FEATURE_NAMES))
        self.assertEqual(metadata["parameters"]["n_jobs"], 1)
        self.assertTrue(metadata["quality_gate_passed"])
        metrics = json.loads((self.bundle / "metrics.json").read_text())
        self.assertGreaterEqual(metrics["test"]["roc_auc"], 0.80)
        card = (self.bundle / "model_card.md").read_text()
        for heading in ["Purpose", "Training Data", "Features", "Evaluation Metrics", "Limitations", "Deployment Assumptions"]:
            self.assertIn(heading, card)
        reference = json.loads((self.bundle / "reference.json").read_text())
        self.assertEqual(reference["source_split"], "validation")
        self.assertEqual(reference["rows"], 200)

    def test_duplicate_version_is_not_overwritten(self):
        with self.assertRaises(FileExistsError):
            train_model(self.data, self.models)

    def test_low_quality_model_is_not_published(self):
        with patch("ml_service.training.train.evaluate", return_value={"roc_auc": 0.5, "pr_auc_average_precision": 0.3, "positive_rate": 0.3}):
            with self.assertRaisesRegex(ValueError, "quality gate failed"):
                train_model(self.data, self.models, version="rejected", trees=1, max_depth=1)
        self.assertFalse((self.models / "rejected").exists())

    def test_traversal_version_is_rejected(self):
        with self.assertRaises(ModelLoadError):
            load_model(self.models, "../baseline-v1")

    def test_checksum_is_checked_before_deserialization(self):
        with patch("ml_service.inference.runtime.sha256_file", return_value="invalid"):
            with patch("ml_service.inference.runtime.joblib.load") as deserialize:
                with self.assertRaisesRegex(ModelLoadError, "checksum"):
                    load_model(self.models, "baseline-v1")
                deserialize.assert_not_called()

    def test_runtime_mismatch_is_rejected(self):
        with patch("ml_service.inference.runtime.runtime_versions", return_value={"python": "0.0"}):
            with self.assertRaisesRegex(ModelLoadError, "runtime_versions"):
                load_model(self.models, "baseline-v1")

    def test_feature_contract_mismatch_is_rejected(self):
        path = self.bundle / "metadata.json"
        original = path.read_text()
        try:
            metadata = json.loads(original)
            metadata["feature_names"] = list(reversed(FEATURE_NAMES))
            write_json(path, metadata)
            with self.assertRaisesRegex(ModelLoadError, "feature_names"):
                load_model(self.models, "baseline-v1")
        finally:
            path.write_text(original)

    def test_health_and_prediction_api(self):
        with TestClient(create_app(self.models)) as client:
            self.assertEqual(client.get("/health/live").status_code, 200)
            self.assertEqual(client.get("/health/ready").json()["status"], "ready")
            self.assertEqual(client.get("/model").json()["features"], list(FEATURE_NAMES))
            response = client.post("/predict", json=EXAMPLE_FEATURES)
            self.assertEqual(response.status_code, 200)
            value = response.json()
            self.assertEqual(value["request_id"], response.headers["x-request-id"])
            self.assertEqual(value["model_version"], "baseline-v1")
            self.assertGreaterEqual(value["failure_probability"], 0)
            self.assertLessEqual(value["failure_probability"], 1)
            self.assertEqual(value["predicted_class"], int(value["failure_probability"] >= 0.5))
            self.assertTrue(math.isfinite(value["inference_latency_ms"]))
            self.assertGreaterEqual(value["inference_latency_ms"], 0)

    def test_invalid_inputs_are_rejected(self):
        invalid = [
            {key: value for key, value in EXAMPLE_FEATURES.items() if key != "load"},
            {**EXAMPLE_FEATURES, "load": "55"},
            {**EXAMPLE_FEATURES, "load": True},
            {**EXAMPLE_FEATURES, "temperature": 121},
            {**EXAMPLE_FEATURES, "unexpected": 1},
        ]
        with TestClient(create_app(self.models)) as client:
            for payload in invalid:
                with self.subTest(payload=payload):
                    response = client.post("/predict", json=payload)
                    self.assertEqual(response.status_code, 422)
                    self.assertEqual(response.json()["request_id"], response.headers["x-request-id"])
            for token in ("NaN", "Infinity", "-Infinity"):
                body = json.dumps(EXAMPLE_FEATURES).replace('"load": 55.0', f'"load": {token}')
                response = client.post("/predict", content=body, headers={"Content-Type": "application/json"})
                self.assertEqual(response.status_code, 422)

    def test_nonfinite_values_are_rejected_by_the_contract(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValidationError):
                PredictionRequest(**{**EXAMPLE_FEATURES, "load": value})

    def test_missing_model_is_unready_but_alive(self):
        with TestClient(create_app(self.root / "missing")) as client:
            self.assertEqual(client.get("/health/live").status_code, 200)
            self.assertEqual(client.get("/health/ready").status_code, 503)
            self.assertEqual(client.get("/model").status_code, 503)
            self.assertEqual(client.post("/predict", json=EXAMPLE_FEATURES).status_code, 503)

    def test_prediction_failure_is_correlated_and_not_leaked(self):
        app = create_app(self.models)
        with TestClient(app) as client:
            with patch.object(type(app.state.model), "predict", side_effect=ValueError("private details")):
                response = client.post("/predict", json=EXAMPLE_FEATURES)
            self.assertEqual(response.status_code, 500)
            self.assertTrue(response.headers["x-request-id"])
            self.assertNotIn("private details", response.text)


if __name__ == "__main__":
    unittest.main()
