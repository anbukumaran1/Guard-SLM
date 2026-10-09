# Guard-SLM Master Blueprint & Project State

Guard-SLM is an ultra-low latency (<20ms) Small Language Model (SLM) security firewall and proxy architecture engineered to protect Large Language Models (LLMs) from prompt injections, jailbreaks, and adversarial attacks.

---

## Architecture Phases

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 1** | **FastAPI Proxy & Normalization Defense Layer** | **COMPLETED** |
| **Phase 2** | **AI Guardrail Dataset Synthesis Engine** | **COMPLETED** |
| **Phase 3** | **DeBERTa Model Fine-Tuning & Quantized ONNX Export (INT8/FP16)** | **COMPLETED** |
| **Phase 4** | **Bare-Metal ONNX Proxy Integration & Concurrency Benchmark** | **COMPLETED** |
| **Phase 5** | **Real-Time Security Dashboard & Telemetry Stream** | **COMPLETED** |
| **Phase 6** | **End-to-End Stress Testing, Red-Teaming & Benchmark Harness** | PENDING |

---

## Phase Execution Details

### Phase 1: FastAPI Proxy & Normalization Defense Layer
- **Schemas**: Strict Pydantic models for `SecurityRequest` (`prompt`, `user_id`) and `SecurityResponse` (`decision`, `threat_type`, `confidence`, `latency_ms`).
- **Normalization Layer (`PayloadNormalizer`)**:
  - Invisible/zero-width Unicode character stripping (`\u200b`, `\u200c`, `\u200d`, `\ufeff`, etc.).
  - Embedded Base64 detection, boundary extraction, and auto-decoding.
  - Leetspeak translation mapping obfuscated characters to standard Latin letters.
- **Async Proxy**:
  - Implemented `/v1/guard/scan` endpoint with `time.perf_counter()` latency tracking.
  - Sub-20ms verified round-trip latency budget.

### Phase 2: AI Guardrail Dataset Synthesis Engine
- **Procedural Generator (`src/data/build_dataset.py`)**:
  - **Threat Matrix (Label 1: 1,000 samples)**: Direct Injections, Roleplay/DAN Jailbreaks, Obfuscated Payloads, PII/Secret Extraction.
  - **Hard Negative Engine (Label 0: 1,000 samples)**: Legitimate Coding Queries, AI Alignment Discussions, Benign Requests.
- **Stratified Split & Export**:
  - Shuffled (`random_state=42`) and exported to `data/train.jsonl` (1,600 samples) and `data/val.jsonl` (400 samples).
  - Exact 50.0% class balance in both splits.

### Phase 3: DeBERTa-v3 Fine-Tuning & Bare-Metal ONNX Compilation
- **Training Pipeline (`src/model/train_and_export.py`)**:
  - Fine-tuned `microsoft/deberta-v3-base` with binary classification head.
  - Compact context window (`max_length=128`) for sub-20ms inference budget.
  - Compiled using `optimum.onnxruntime.ORTModelForSequenceClassification`.
  - Artifacts exported to `src/model/onnx_guard/` (`model.onnx`, tokenizer, config).

### Phase 4: Bare-Metal ONNX Proxy Integration & Concurrency Benchmark
- **Native ONNX Proxy Integration (`src/proxy/main.py`)**:
  - Removed dummy mocker class and implemented native `GuardONNXEngine`.
  - Global startup initialization via FastAPI `@asynccontextmanager` lifespan.
  - Configured hardware-optimized CPU session (`intra_op_num_threads=4`, `ORT_ENABLE_ALL`) with dynamic token input length.
  - Non-blocking execution via `asyncio.to_thread` for high concurrency without event-loop starvation.
- **High-Concurrency Load Testing (`src/proxy/benchmark.py`)**:
  - Fired 1,000 concurrent asynchronous requests to live `/v1/guard/scan` endpoint.
  - Validated throughput (82.19 Requests/sec) and pipeline latency distributions under heavy load.

### Phase 5: Real-Time Security Dashboard & Telemetry Stream
- **Database Engine (`src/proxy/db.py`)**:
  - Asynchronous SQLite logger using `aiosqlite` targeting `data/telemetry.db`.
  - `init_db()` auto-initializes the `scans` table on server startup.
  - `log_scan()` captures raw prompt, normalized prompt, decision, threat type, confidence, and latency.
- **Proxy Telemetry Integration**:
  - Integrated into FastAPI `/v1/guard/scan` via `BackgroundTasks` for zero-latency impact on responses.
  - Verified live writing: recorded initial scan events and confirmed Base64/Unicode unmasking fields.
- **Live Command Center (`src/dashboard/app.py`)**:
  - Streamlit dashboard displaying real-time scan volume, block rate, average latency, and rolling RPS.
  - Plotly donut chart visualizes Safe vs. Threat distributions.
  - Latency distribution histogram.
  - Live data feed displays raw payloads alongside unmasked payloads to demonstrate Base64 and Unicode normalization in real time.
  - Verified headless launch and health check on port 8501.
