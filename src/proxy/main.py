import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Tuple

from fastapi import BackgroundTasks, FastAPI, status
import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

from src.proxy.db import init_db, log_scan
from src.proxy.normalization import PayloadNormalizer
from src.proxy.schemas import SecurityRequest, SecurityResponse


class GuardONNXEngine:
    """
    Bare-metal ONNX Runtime Classifier for DeBERTa-v3 Guard model.
    Runs hardware-optimized CPU inference with dynamic token lengths.
    """

    def __init__(self, model_dir: str = "src/model/onnx_guard"):
        self.model_dir = Path(model_dir)
        self.tokenizer = None
        self.session = None
        self.input_names = []

    def load(self):
        """Loads tokenizer and ONNX Runtime InferenceSession once globally."""
        if self.session is not None and self.tokenizer is not None:
            return

        print(f"[*] Loading tokenizer from {self.model_dir}...")
        self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir))

        model_file = self.model_dir / "model.onnx"
        if not model_file.exists():
            raise FileNotFoundError(f"ONNX model file not found at {model_file}")

        print(f"[*] Initializing bare-metal ONNX session from {model_file}...")
        sess_opts = ort.SessionOptions()
        sess_opts.intra_op_num_threads = 4
        sess_opts.inter_op_num_threads = 1
        sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self.session = ort.InferenceSession(
            str(model_file),
            sess_options=sess_opts,
            providers=["CPUExecutionProvider"],
        )
        self.input_names = [inp.name for inp in self.session.get_inputs()]

        # Warmup pass
        warmup_inputs = self.tokenizer(
            "Warmup prompt for Guard-SLM runtime",
            return_tensors="np",
            truncation=True,
            max_length=128,
        )
        ort_feed = {k: v for k, v in warmup_inputs.items() if k in self.input_names}
        self.session.run(None, ort_feed)
        print("[+] GuardONNXEngine initialized and warmed up.")

    def ensure_loaded(self):
        if self.session is None or self.tokenizer is None:
            self.load()

    async def predict(self, text: str) -> Tuple[str, Optional[str], float]:
        """
        Runs async inference on the provided text.
        Returns: (decision, threat_type, confidence)
        """
        self.ensure_loaded()
        return await asyncio.to_thread(self._sync_predict, text)

    def _sync_predict(self, text: str) -> Tuple[str, Optional[str], float]:
        inputs = self.tokenizer(
            text,
            return_tensors="np",
            truncation=True,
            max_length=128,
        )
        ort_feed = {k: v for k, v in inputs.items() if k in self.input_names}

        outputs = self.session.run(None, ort_feed)
        logits = outputs[0]  # Shape: [1, 2]

        # Numerically stable softmax
        exp_logits = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        probs = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)

        pred_label = int(np.argmax(probs, axis=-1)[0])
        confidence = float(probs[0][pred_label])

        if pred_label == 1:
            return "BLOCK", "prompt_injection", round(confidence, 4)
        return "FORWARD", None, round(confidence, 4)


normalizer = PayloadNormalizer()
engine = GuardONNXEngine(model_dir="src/model/onnx_guard")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize telemetry database and ONNX engine
    await init_db()
    engine.load()
    yield
    # Shutdown


app = FastAPI(
    title="Guard-SLM Security Proxy",
    description="Sub-20ms ultra-low latency prompt injection and jailbreak firewall.",
    version="0.3.0",
    lifespan=lifespan,
)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "healthy"}


@app.post(
    "/v1/guard/scan",
    response_model=SecurityResponse,
    status_code=status.HTTP_200_OK,
    summary="Scan prompt for injection/jailbreak attacks",
)
async def guard_scan(
    request: SecurityRequest,
    background_tasks: BackgroundTasks,
) -> SecurityResponse:
    start_time = time.perf_counter()

    # Step 1: Normalization Defense Layer
    normalized_text = normalizer.normalize(request.prompt)

    # Step 2: Bare-metal ONNX Model Inference
    decision, threat_type, confidence = await engine.predict(normalized_text)

    # Step 3: Latency measurement in ms
    latency_ms = (time.perf_counter() - start_time) * 1000.0
    rounded_latency = round(latency_ms, 3)

    # Step 4: Non-blocking asynchronous telemetry dispatch via background tasks
    background_tasks.add_task(
        log_scan,
        original_prompt=request.prompt,
        normalized_prompt=normalized_text,
        decision=decision,
        threat_type=threat_type,
        confidence=confidence,
        latency_ms=rounded_latency,
    )

    return SecurityResponse(
        decision=decision,
        threat_type=threat_type,
        confidence=confidence,
        latency_ms=rounded_latency,
    )
