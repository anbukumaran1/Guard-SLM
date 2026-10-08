import asyncio
import time
from typing import Tuple

from fastapi import FastAPI, status

from src.proxy.normalization import PayloadNormalizer
from src.proxy.schemas import SecurityRequest, SecurityResponse


class DebertaONNXMocker:
    """
    Mock/dummy ONNX runtime classifier for DeBERTa guard model.
    Simulates async inference latency (~5ms) and produces deterministic classification.
    """

    def __init__(self, simulated_delay_sec: float = 0.005):
        self.simulated_delay_sec = simulated_delay_sec

    async def predict(self, normalized_text: str) -> Tuple[str, str | None, float]:
        """
        Simulates model classification.
        Returns: (decision, threat_type, confidence)
        """
        if self.simulated_delay_sec > 0:
            await asyncio.sleep(self.simulated_delay_sec)

        # Flag malicious input if normalized text contains 'ignore' (e.g. "ignore previous instructions")
        if "ignore" in normalized_text.lower():
            return "BLOCK", "prompt_injection", 0.98

        return "FORWARD", None, 0.99


app = FastAPI(
    title="Guard-SLM Security Proxy",
    description="Sub-20ms ultra-low latency prompt injection and jailbreak firewall.",
    version="0.1.0",
)

normalizer = PayloadNormalizer()
model = DebertaONNXMocker(simulated_delay_sec=0.005)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "healthy"}


@app.post(
    "/v1/guard/scan",
    response_model=SecurityResponse,
    status_code=status.HTTP_200_OK,
    summary="Scan prompt for injection/jailbreak attacks",
)
async def guard_scan(request: SecurityRequest) -> SecurityResponse:
    start_time = time.perf_counter()

    # Step 1: Normalization Defense Layer
    normalized_text = normalizer.normalize(request.prompt)

    # Step 2: Model Inference
    decision, threat_type, confidence = await model.predict(normalized_text)

    # Step 3: Latency measurement in ms
    latency_ms = (time.perf_counter() - start_time) * 1000.0

    return SecurityResponse(
        decision=decision,
        threat_type=threat_type,
        confidence=confidence,
        latency_ms=round(latency_ms, 3),
    )
