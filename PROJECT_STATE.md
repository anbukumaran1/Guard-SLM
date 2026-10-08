# Guard-SLM Master Blueprint & Project State

Guard-SLM is an ultra-low latency (<20ms) Small Language Model (SLM) security firewall and proxy architecture engineered to protect Large Language Models (LLMs) from prompt injections, jailbreaks, and adversarial attacks.

---

## Architecture Phases

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 1** | **FastAPI Proxy & Normalization Defense Layer** | **COMPLETED** |
| **Phase 2** | **AI Guardrail Dataset Synthesis Engine** | **COMPLETED** |
| **Phase 3** | **DeBERTa Model Fine-Tuning & Quantized ONNX Export (INT8/FP16)** | PENDING |
| **Phase 4** | **Hybrid Defense & Fast-Path Heuristic Token Filter Engine** | PENDING |
| **Phase 5** | **Real-Time Security Dashboard & Telemetry Stream** | PENDING |
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
  - **Threat Matrix (Label 1: 1,000 samples)**:
    - 400 Direct Prompt Injections (system prompt extractors, boundary overrides, command injections).
    - 200 Roleplay & DAN Jailbreaks (DAN personas, evil bot simulations, developer mode unconstrained overrides).
    - 200 Obfuscated Payloads (100 Base64-encoded injections, 100 Leetspeak-substituted attacks).
    - 200 PII & Secret Extraction Attempts (database credentials, API keys, JWTs, SSH keys, env vars).
  - **Hard Negative Engine (Label 0: 1,000 samples)**:
    - 400 Legitimate Coding Queries (git ignore, class overrides, CORS bypass in dev, token hashing).
    - 300 AI Alignment & Security Discussions (academic papers, OWASP Top 10, jailbreak research).
    - 300 Benign User Requests (summarization, professional communication, informative inquiries).
- **Stratified Split & Export**:
  - Shuffled with fixed `random_state=42`.
  - Scikit-learn stratified 80/20 train/val split.
  - `data/train.jsonl`: Exactly 1,600 samples (800 Label 0, 800 Label 1; 50.0% balance).
  - `data/val.jsonl`: Exactly 400 samples (200 Label 0, 200 Label 1; 50.0% balance).
  - Strict schema: `{"text": str, "label": int}`.
- **Verification**:
  - Comprehensive pytest suite in `tests/test_dataset.py`.
  - 100% test pass rate across data integrity, schema consistency, stratification, and Base64 detection.
