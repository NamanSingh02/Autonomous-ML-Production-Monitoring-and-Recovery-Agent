# Phase 1 - Baseline ML Service

The Phase 1 source code is implemented. The full 40,000-row dataset, baseline-v1 model,
Docker image, and a running service are created locally by the commands below. They are
not committed to Git. The small automated tests use temporary files and do not substitute
for the full baseline's metrics or a container runtime check.

## Local Setup

Run commands from the repository root. The pinned environment uses Python 3.11.
The current macOS setup supports the pinned native wheels; the NumPy and SciPy wheels
require macOS 14 or newer on Apple Silicon. Docker provides a Linux alternative.

```bash
cd '/Users/naman/1)Projects/agentic AI projects/Autonomous-ML-Production-Monitoring-and-Recovery-Agent'
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
```

Use a Python 3.11 executable for the venv if `python3 --version` reports another minor
version. No LLM credentials, PostgreSQL, Redis, or external dataset download is needed.
The development requirements include the runtime pins and the in-process HTTP test client.

## Lightweight Checks

```bash
python -m unittest discover -s tests -v
```

The tests generate 800 training rows and 200 rows for each held-out split, fit eight
trees, and remove the temporary data and artifacts afterward. They check reproducibility,
split separation, artifact integrity, quality-gate rejection, model compatibility, request
validation, health states, structured prediction responses, and failure handling.

## Generate the Full Dataset

```bash
python -m ml_service.training.data --output data/generated/equipment-v1 --seed 42
```

This creates train.npz (30,000 rows), validation.npz (5,000 rows), test.npz (5,000 rows),
and manifest.json. Each NPZ contains `features` and `labels`. The manifest records seeds,
feature order, the training-only calibrated intercept, prevalence, checksums, generator
version, NumPy version, and the recipe source hash. The generator code defines the
correlated sensor distributions and nonlinear Bernoulli label process.

Existing dataset directories are never overwritten. Reuse a valid generated dataset
for another training run, or select a different output path for a new dataset version.
The frozen recipe and independent split seeds avoid tuning labels on held-out data.
Production traffic and delayed label release belong to Phase 2 and are not active here.

## Train and Record the Baseline

```bash
python -m ml_service.training.train --data-dir data/generated/equipment-v1 --model-root artifacts/models --version baseline-v1
```

Training uses a RandomForestClassifier with 100 trees, maximum depth 12, minimum leaf
size 5, seed 17, and one job. The class threshold stays at 0.5. The optional `--trees`,
`--max-depth`, and `--seed` arguments are recorded in the bundle; changing a training
configuration requires a new model version. Tune experiments using development data,
not repeated selection against the held-out test set.

Publication requires training prevalence between 20% and 40%, validation and test
ROC-AUC each at least 0.80, and average precision above each split's positive prevalence.
Failure prints measured metrics and publishes no serving bundle. Metrics are measured
when training runs; no full-data quality claim has been made in advance.

Successful training atomically publishes:

```text
artifacts/models/baseline-v1/
├── model.joblib
├── metadata.json
├── metrics.json
├── dataset_manifest.json
├── reference.json
├── model_card_metadata.json
└── model_card.md
```

The model card contains the model purpose, data, features and ranges, measured training/
validation/test metrics, limitations, and deployment assumptions. Metrics include ROC-AUC,
average precision (the selected PR-AUC summary), F1, precision, recall, Brier score, and
prevalence. Reference statistics use the validation split, not the held-out test split.
They are inputs for later monitoring, not an implemented drift detector.

Existing model version directories are immutable. For another version:

```bash
python -m ml_service.training.train --version baseline-v2
```

## Start and Check the API

Run the server in the first terminal:

```bash
MODEL_VERSION=baseline-v1 python -m uvicorn ml_service.inference.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Open a second terminal, return to the same repository root, and activate `.venv`:

```bash
source .venv/bin/activate
python scripts/check_inference.py --base-url http://127.0.0.1:8000 --expected-version baseline-v1
```

The check calls the live and ready endpoints, verifies the loaded version, submits a real
prediction request, checks probability/class consistency and timing, and confirms that
invalid input returns HTTP 422. It exits nonzero on failure. Stop the server with Ctrl+C.

The API exposes:

| Endpoint | Behavior |
|---|---|
| GET /health/live | HTTP 200 while the application is responding |
| GET /health/ready | HTTP 200 with loaded versions, or HTTP 503 when no valid model is loaded |
| GET /model | Model version, preprocessing version, feature order, and threshold |
| POST /predict | Strictly validated sensor input and a versioned prediction response |

Example request:

```bash
curl --fail-with-body http://127.0.0.1:8000/predict -H 'Content-Type: application/json' -d '{"temperature":65,"vibration":5,"pressure":8,"operating_hours":12000,"load":55}'
```

All five features are required; extra fields, numeric strings, booleans, non-finite
numbers, and out-of-range values are rejected. The sensor contract preserves units and
explicit feature order without scaling or imputation. Predictions include request ID,
failure probability, predicted class, threshold, model/preprocessing versions, and
inference_latency_ms. This timing covers feature preparation and model prediction;
the JSON request log separately records application request duration. Client-observed
network latency must be measured later for the end-to-end latency target.

JSON logs contain correlated request IDs, paths, statuses, durations, and versions.
Sensor bodies and labels are not logged. Model loading happens once in application
lifespan. An unavailable or incompatible bundle is logged and leaves the service alive
but unready; training is never invoked by startup. Fix the bundle or configuration and
restart the process. `MODEL_ROOT` overrides the default repository artifacts/models path.

## Docker

After local training, start Docker Desktop and run:

```bash
docker compose up --build -d inference
docker compose ps
docker compose logs inference
python scripts/check_inference.py --expected-version baseline-v1
```

The container uses the same pinned runtime, loads the local artifacts read-only, listens
on the host's loopback interface, and runs as a non-root user. Compose caps it at one CPU
and 512 MiB. The image has a readiness healthcheck; an untrained or incompatible model
correctly makes it unhealthy. The read-only container has a small temporary filesystem.
No training happens during image build or startup.

For a different already-trained version:

```bash
MODEL_VERSION=baseline-v2 docker compose up -d --force-recreate inference
python scripts/check_inference.py --expected-version baseline-v2
```

Stop the container:

```bash
docker compose down
```

As an alternative to a host Python environment, build once and generate/train in the
same image. Run this alternative from the repository root before starting Compose:

```bash
docker build -t ml-inference:phase1 .
mkdir -p data/generated artifacts/models
docker run --rm --user "$(id -u):$(id -g)" --mount "type=bind,source=$PWD,target=/workspace" --workdir /workspace ml-inference:phase1 python -m ml_service.training.data
docker run --rm --user "$(id -u):$(id -g)" --mount "type=bind,source=$PWD,target=/workspace" --workdir /workspace ml-inference:phase1 python -m ml_service.training.train
```

These commands create the same local generated paths. Choose either host or container
generation; do not run both into an existing dataset/model version. Model deserialization
is allowed only from trusted local artifacts. Checksums detect changes, not malicious
replacement of an entire bundle. Exact recorded library versions and Python major/minor
must match training; regenerate a version using the pinned environment if they differ.

## Execution Status

The source and small fixture tests are validated separately from the full baseline run.
Full dataset generation, 100-tree training, actual baseline metrics, live HTTP verification,
Docker build, and container health verification are pending local execution. Phase 2
traffic generation, incident injection, persistence, and monitoring are not implemented.
