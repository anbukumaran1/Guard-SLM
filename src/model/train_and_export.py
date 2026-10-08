"""
Guard-SLM DeBERTa-v3 Fine-Tuning & Bare-Metal ONNX Compilation Pipeline.

This module fine-tunes a DeBERTa-v3 sequence classification encoder on synthesized
prompt injection datasets and exports the compiled ONNX graph to src/model/onnx_guard/
for sub-20ms ultra-low latency production inference.
"""

import os
from pathlib import Path
from typing import Dict

import evaluate
import numpy as np
import torch

# Compatibility patch for Python 3.14+ dill / pickle _batch_setitems signature
try:
    import dill
    import datasets.utils._dill

    _orig_batch_setitems = datasets.utils._dill.Pickler._batch_setitems

    def _py314_batch_setitems(self, items, obj=None):
        if getattr(self, "_legacy_no_dict_keys_sorting", False):
            if obj is not None:
                return dill.Pickler._batch_setitems(self, items, obj)
            return dill.Pickler._batch_setitems(self, items)
        try:
            items = sorted(items)
        except Exception:
            from datasets.fingerprint import Hasher
            items = sorted(items, key=lambda x: Hasher.hash(x[0]))
        if obj is not None:
            return dill.Pickler._batch_setitems(self, items, obj)
        return dill.Pickler._batch_setitems(self, items)

    datasets.utils._dill.Pickler._batch_setitems = _py314_batch_setitems
except Exception:
    pass

from datasets import load_dataset
from optimum.onnxruntime import ORTModelForSequenceClassification
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)


def compute_metrics_fn(eval_pred):
    """Calculates accuracy and f1 score."""
    metric_acc = evaluate.load("accuracy")
    metric_f1 = evaluate.load("f1")

    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)

    acc = metric_acc.compute(predictions=predictions, references=labels)
    f1 = metric_f1.compute(predictions=predictions, references=labels)
    return {**acc, **f1}


def train_and_export_onnx(
    model_name: str = "microsoft/deberta-v3-base",
    data_dir: str = "data",
    output_dir: str = "./results",
    onnx_output_dir: str = "src/model/onnx_guard",
    max_length: int = 128,
    num_train_epochs: int = 1,
    batch_size: int = 8,
    sample_limit: int | None = None,
):
    """
    Fine-tunes DeBERTa-v3 on train.jsonl / val.jsonl and compiles to ONNX.

    Args:
        model_name: Hugging Face model repository identifier.
        data_dir: Path to dataset containing train.jsonl and val.jsonl.
        output_dir: Temporary directory for model checkpoints.
        onnx_output_dir: Destination folder for compiled ONNX model & tokenizer.
        max_length: Maximum token length (tight 128 token window for <20ms latency SLA).
        num_train_epochs: Number of training epochs (1 for fast iteration).
        batch_size: Per-device batch size.
        sample_limit: Optional integer slice to speed up training on CPU/resource-constrained environments.
    """
    print(f"[*] Initializing model and tokenizer: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    id2label = {0: "SAFE", 1: "THREAT"}
    label2id = {"SAFE": 0, "THREAT": 1}

    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=2,
        id2label=id2label,
        label2id=label2id,
    )

    data_path = Path(data_dir)
    train_file = str((data_path / "train.jsonl").resolve())
    val_file = str((data_path / "val.jsonl").resolve())

    print(f"[*] Loading datasets from {train_file} and {val_file}")
    dataset = load_dataset(
        "json",
        data_files={"train": train_file, "validation": val_file},
    )

    if sample_limit is not None and sample_limit > 0:
        print(f"[*] Applying sample limit: {sample_limit} train / {max(10, sample_limit // 4)} val")
        dataset["train"] = dataset["train"].select(range(min(sample_limit, len(dataset["train"]))))
        dataset["validation"] = dataset["validation"].select(
            range(min(max(10, sample_limit // 4), len(dataset["validation"])))
        )

    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            padding="max_length",
            truncation=True,
            max_length=max_length,
        )

    print(f"[*] Tokenizing datasets (max_length={max_length})...")
    tokenized_datasets = dataset.map(tokenize_function, batched=True)

    use_fp16 = torch.cuda.is_available()
    print(f"[*] CUDA available: {use_fp16}. fp16 training enabled: {use_fp16}")

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_train_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        fp16=use_fp16,
        logging_steps=10,
        save_strategy="no",
        eval_strategy="no",
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["validation"],
        processing_class=tokenizer,
    )

    print("[*] Starting Trainer.train() loop...")
    trainer.train()
    print("[+] Training completed successfully.")

    # Save fine-tuned PyTorch checkpoint temporarily for export
    checkpoint_dir = Path(output_dir) / "fine_tuned_guard"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(checkpoint_dir))
    tokenizer.save_pretrained(str(checkpoint_dir))

    # Compile model to ONNX format via Optimum
    print(f"[*] Compiling fine-tuned model to ONNX bare-metal binary -> {onnx_output_dir}...")
    onnx_dest = Path(onnx_output_dir)
    onnx_dest.mkdir(parents=True, exist_ok=True)

    ort_model = ORTModelForSequenceClassification.from_pretrained(
        str(checkpoint_dir),
        export=True,
    )
    ort_model.save_pretrained(str(onnx_dest))
    tokenizer.save_pretrained(str(onnx_dest))
    print(f"[+] ONNX compilation complete. Artifacts saved to: {onnx_dest.resolve()}")


if __name__ == "__main__":
    # If no GPU is detected, use sample limit of 50 for rapid end-to-end CPU execution
    sample_limit = None if torch.cuda.is_available() else 50
    train_and_export_onnx(sample_limit=sample_limit)
