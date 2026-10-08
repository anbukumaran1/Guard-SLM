from pathlib import Path

import numpy as np
import onnxruntime as ort
import pytest


@pytest.fixture(scope="module")
def onnx_dir():
    path = Path("src/model/onnx_guard")
    return path


def test_onnx_directory_exists(onnx_dir):
    assert onnx_dir.exists(), f"Directory {onnx_dir} does not exist"
    assert onnx_dir.is_dir(), f"{onnx_dir} is not a directory"


def test_onnx_model_file_exists(onnx_dir):
    onnx_files = list(onnx_dir.glob("*.onnx"))
    assert len(onnx_files) > 0, f"No .onnx files found in {onnx_dir}"
    model_path = onnx_dir / "model.onnx"
    assert model_path.exists() or len(onnx_files) > 0, "Expected model.onnx in onnx_guard directory"


def test_onnx_inference_session_load(onnx_dir):
    onnx_files = list(onnx_dir.glob("*.onnx"))
    assert len(onnx_files) > 0, f"No .onnx file found in {onnx_dir}"
    model_path = onnx_files[0]

    # Session loading without throwing errors
    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    assert session is not None


def test_onnx_dummy_tensor_inference(onnx_dir):
    onnx_files = list(onnx_dir.glob("*.onnx"))
    model_path = onnx_files[0]

    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    
    # Inspect input node requirements
    input_names = [inp.name for inp in session.get_inputs()]
    batch_size = 1
    seq_length = 128

    # Create dummy tensors of shape [1, 128]
    input_ids = np.zeros((batch_size, seq_length), dtype=np.int64)
    attention_mask = np.ones((batch_size, seq_length), dtype=np.int64)

    inputs = {"input_ids": input_ids}
    if "attention_mask" in input_names:
        inputs["attention_mask"] = attention_mask
    if "token_type_ids" in input_names:
        inputs["token_type_ids"] = np.zeros((batch_size, seq_length), dtype=np.int64)

    outputs = session.run(None, inputs)

    assert len(outputs) > 0, "Inference returned empty output list"
    logits = outputs[0]
    # Verify shape: [batch_size, num_classes] -> [1, 2]
    assert logits.shape == (1, 2), f"Expected logits shape (1, 2), got {logits.shape}"
