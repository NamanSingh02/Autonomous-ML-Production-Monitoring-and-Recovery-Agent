"""Validating sensor requests and structured prediction responses."""

from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    temperature: float = Field(ge=0, le=120, description="Temperature in degrees Celsius")
    vibration: float = Field(ge=0, le=20, description="Vibration in mm/s")
    pressure: float = Field(ge=0, le=20, description="Pressure in bar")
    operating_hours: float = Field(ge=0, le=50_000)
    load: float = Field(ge=0, le=100, description="Operating load percentage")


class PredictionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    request_id: str
    failure_probability: float = Field(ge=0, le=1)
    predicted_class: int = Field(ge=0, le=1)
    class_threshold: float = Field(ge=0, le=1)
    model_version: str
    preprocessing_version: str
    inference_latency_ms: float = Field(ge=0)
