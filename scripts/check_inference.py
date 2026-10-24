"""Checking a running inference service with the Python standard library."""

import argparse
import json
import math
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description="Checking health, predictions, and validation over HTTP.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--expected-version", default="baseline-v1")
    arguments = parser.parse_args()
    base = arguments.base_url.rstrip("/")

    def call(path: str, payload: dict | None = None):
        body = json.dumps(payload).encode() if payload is not None else None
        request = Request(base + path, data=body, headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.load(response), response.headers.get("X-Request-ID")
        except HTTPError as error:
            return error.code, json.load(error), error.headers.get("X-Request-ID")

    try:
        for path in ("/health/live", "/health/ready", "/model"):
            status, value, request_id = call(path)
            if status != 200 or not request_id:
                raise ValueError(f"{path} failed: {status} {value}")
            if path != "/health/live" and value["model_version"] != arguments.expected_version:
                raise ValueError("The service loaded an unexpected model version.")
        payload = {"temperature": 65, "vibration": 5, "pressure": 8, "operating_hours": 12000, "load": 55}
        status, prediction, request_id = call("/predict", payload)
        if status != 200 or prediction.get("request_id") != request_id:
            raise ValueError(f"Prediction request failed: {status} {prediction}")
        if prediction["model_version"] != arguments.expected_version:
            raise ValueError("Prediction used an unexpected model version.")
        probability = prediction["failure_probability"]
        latency = prediction["inference_latency_ms"]
        if not math.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("Invalid probability in prediction response.")
        if prediction["predicted_class"] != int(probability >= prediction["class_threshold"]):
            raise ValueError("Predicted class does not match the declared threshold.")
        if not math.isfinite(latency) or latency < 0 or not prediction["preprocessing_version"]:
            raise ValueError("Invalid latency or missing preprocessing version.")
        status, _, _ = call("/predict", {**payload, "temperature": "invalid"})
        if status != 422:
            raise ValueError(f"Invalid features should return HTTP 422, received {status}.")
    except (OSError, URLError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Inference check failed: {error}\n")
    print(json.dumps({"status": "passed", "prediction": prediction}, indent=2))


if __name__ == "__main__":
    main()
