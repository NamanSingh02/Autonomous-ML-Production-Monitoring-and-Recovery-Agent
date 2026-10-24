"""Exposing readiness, model metadata, and validated predictions."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ml_service.inference.logging import service_logger
from ml_service.inference.runtime import ModelLoadError, load_model
from ml_service.inference.schemas import PredictionRequest, PredictionResponse


def create_app(model_root: Path | None = None, model_version: str | None = None) -> FastAPI:
    root = model_root or Path(os.environ.get(
        "MODEL_ROOT", str(Path(__file__).resolve().parents[2] / "artifacts/models"),
    ))
    version = model_version or os.environ.get("MODEL_VERSION", "baseline-v1")
    logger = service_logger()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.model = None
        try:
            application.state.model = load_model(root, version)
            logger.info("model_loaded", extra={"fields": {"model_version": version}})
        except ModelLoadError as error:
            logger.error("model_load_failed", extra={"fields": {
                "model_version": version, "reason": str(error),
            }})
        yield
        application.state.model = None

    application = FastAPI(
        title="Equipment Failure Prediction Service", version="0.1.0", lifespan=lifespan,
    )

    @application.middleware("http")
    async def request_logging(request: Request, call_next):
        started = perf_counter()
        request.state.request_id = str(uuid4())
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request.state.request_id
            return response
        finally:
            model = getattr(application.state, "model", None)
            logger.info("http_request", extra={"fields": {
                "request_id": request.state.request_id, "method": request.method,
                "path": request.url.path, "status_code": status,
                "duration_ms": round((perf_counter() - started) * 1000, 3),
                "model_version": model.version if model else None,
                "preprocessing_version": model.preprocessing_version if model else None,
            }})

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError):
        return JSONResponse(status_code=422, content={
            "request_id": request.state.request_id,
            "detail": [
                {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
                for item in error.errors()
            ],
        })

    def require_model():
        model = getattr(application.state, "model", None)
        if model is None:
            raise HTTPException(status_code=503, detail="Model unavailable; check startup logs and artifact configuration.")
        return model

    @application.get("/health/live")
    def liveness():
        return {"status": "alive"}

    @application.get("/health/ready")
    def readiness():
        model = require_model()
        return {
            "status": "ready", "model_version": model.version,
            "preprocessing_version": model.preprocessing_version,
        }

    @application.get("/model")
    def model_information():
        model = require_model()
        return {
            "model_version": model.version,
            "preprocessing_version": model.preprocessing_version,
            "class_threshold": model.threshold,
            "features": list(PredictionRequest.model_fields),
        }

    @application.post("/predict", response_model=PredictionResponse)
    def predict(payload: PredictionRequest, request: Request):
        model = require_model()
        started = perf_counter()
        try:
            probability, predicted_class = model.predict(payload.model_dump())
        except Exception as error:
            logger.error("prediction_failed", extra={"fields": {
                "request_id": request.state.request_id, "model_version": model.version,
                "error_type": type(error).__name__,
            }})
            raise HTTPException(status_code=500, detail="Prediction failed; see correlated service logs.") from error
        return PredictionResponse(
            request_id=request.state.request_id, failure_probability=probability,
            predicted_class=predicted_class, class_threshold=model.threshold,
            model_version=model.version, preprocessing_version=model.preprocessing_version,
            inference_latency_ms=round((perf_counter() - started) * 1000, 3),
        )

    return application


app = create_app()
