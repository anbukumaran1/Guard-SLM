import json
import re
from pathlib import Path

import pandas as pd
import pytest

from src.data.build_dataset import build_and_export_dataset


@pytest.fixture(scope="module")
def dataset_paths():
    data_dir = Path("data")
    train_path = data_dir / "train.jsonl"
    val_path = data_dir / "val.jsonl"
    
    # If not yet generated, build them
    if not train_path.exists() or not val_path.exists():
        build_and_export_dataset(str(data_dir))
        
    return train_path, val_path


def test_dataset_files_exist(dataset_paths):
    train_path, val_path = dataset_paths
    assert train_path.exists(), f"Train file does not exist at {train_path}"
    assert val_path.exists(), f"Val file does not exist at {val_path}"


def test_dataset_row_counts(dataset_paths):
    train_path, val_path = dataset_paths
    
    train_df = pd.read_json(train_path, lines=True)
    val_df = pd.read_json(val_path, lines=True)

    assert len(train_df) == 1600, f"Expected exactly 1600 train samples, got {len(train_df)}"
    assert len(val_df) == 400, f"Expected exactly 400 val samples, got {len(val_df)}"


def test_dataset_strict_schema(dataset_paths):
    train_path, val_path = dataset_paths

    for path in (train_path, val_path):
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                record = json.loads(line)
                assert set(record.keys()) == {"text", "label"}, f"Invalid keys in line {idx} of {path}: {record.keys()}"
                assert isinstance(record["text"], str), f"Field 'text' must be str in line {idx} of {path}"
                assert isinstance(record["label"], int), f"Field 'label' must be int in line {idx} of {path}"
                assert record["label"] in (0, 1), f"Label must be 0 or 1 in line {idx} of {path}"
                assert len(record["text"].strip()) > 0, f"Text should not be empty in line {idx} of {path}"


def test_stratification_exact_fifty_percent(dataset_paths):
    train_path, val_path = dataset_paths
    
    train_df = pd.read_json(train_path, lines=True)
    val_df = pd.read_json(val_path, lines=True)

    # Train class counts
    train_label_0 = (train_df["label"] == 0).sum()
    train_label_1 = (train_df["label"] == 1).sum()
    assert train_label_0 == 800, f"Expected 800 benign in train, got {train_label_0}"
    assert train_label_1 == 800, f"Expected 800 threats in train, got {train_label_1}"
    assert train_df["label"].mean() == 0.5, f"Train balance is not exactly 50%: {train_df['label'].mean()}"

    # Val class counts
    val_label_0 = (val_df["label"] == 0).sum()
    val_label_1 = (val_df["label"] == 1).sum()
    assert val_label_0 == 200, f"Expected 200 benign in val, got {val_label_0}"
    assert val_label_1 == 200, f"Expected 200 threats in val, got {val_label_1}"
    assert val_df["label"].mean() == 0.5, f"Val balance is not exactly 50%: {val_df['label'].mean()}"


def test_dataset_contains_base64_payloads(dataset_paths):
    train_path, val_path = dataset_paths
    
    train_df = pd.read_json(train_path, lines=True)
    val_df = pd.read_json(val_path, lines=True)
    all_text = pd.concat([train_df["text"], val_df["text"]])

    # Base64 pattern candidate (min 8 chars of valid base64 chars + padding)
    b64_pattern = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")
    matching_samples = [t for t in all_text if b64_pattern.search(t)]

    assert len(matching_samples) > 0, "No Base64 encoded payload found in generated dataset!"
