# Guard-SLM Master Blueprint & Project State

Guard-SLM is an ultra-low latency (<20ms) Small Language Model (SLM) security firewall and proxy architecture engineered to protect Large Language Models (LLMs) from prompt injections, jailbreaks, and adversarial attacks.

---

## Architecture Phases

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 1** | **FastAPI Proxy & Normalization Defense Layer** | **COMPLETED** |
| **Phase 2** | **DeBERTa Model Fine-Tuning & Prompt Injection Dataset Pipeline** | PENDING |
| **Phase 3** | **ONNX Runtime Export & Quantization (INT8/FP16 Optimization)** | PENDING |
| **Phase 4** | **Hybrid Defense & Fast-Path Heuristic Token Filter Engine** | PENDING |
| **Phase 5** | **Real-Time Security Dashboard & Telemetry Stream** | PENDING |
| **Phase 6** | **End-to-End Stress Testing, Red-Teaming & Benchmark Harness** | PENDING |

---

## Phase 1 Execution Summary

- **Schemas Defined**: Strict Pydantic models for `SecurityRequest` (`prompt`, `user_id`) and `SecurityResponse` (`decision`, `threat_type`, `confidence`, `latency_ms`).
- **Normalization Defense Layer (`PayloadNormalizer`)**:
  - Zero-width & invisible Unicode character stripping (`\u200b`, `\u200c`, `\u200d`, `\ufeff`, etc.).
  - Embedded Base64 payload detection, robust boundary handling, and auto-decoding.
  - Leetspeak translation mapping obfuscated characters to standard Latin letters.
- **Async FastAPI Proxy**:
  - Implemented `/v1/guard/scan` endpoint with high-precision `time.perf_counter()` latency tracking.
  - Integrated `DebertaONNXMocker` with realistic async inference delay (~5ms).
  - Validated strict sub-20ms round-trip latency budget.
- **Verification**:
  - Comprehensive unit and integration test suite in `tests/test_proxy.py`.
  - 100% test pass rate across evasion handling, schema validation, and latency targets.
