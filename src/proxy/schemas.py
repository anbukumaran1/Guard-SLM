from typing import Literal, Optional
from pydantic import BaseModel, Field


class SecurityRequest(BaseModel):
    prompt: str = Field(..., description="The user prompt or input text to evaluate.")
    user_id: Optional[str] = Field(default=None, description="Optional identifier for the requesting user or client.")


class SecurityResponse(BaseModel):
    decision: Literal["BLOCK", "FORWARD"] = Field(
        ..., description="Guard action decision: BLOCK malicious input or FORWARD safe input."
    )
    threat_type: Optional[str] = Field(
        default=None, description="Identified threat category if blocked (e.g., prompt_injection), else None."
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Model classification confidence score between 0.0 and 1.0."
    )
    latency_ms: float = Field(
        ..., ge=0.0, description="Total pipeline latency in milliseconds."
    )
