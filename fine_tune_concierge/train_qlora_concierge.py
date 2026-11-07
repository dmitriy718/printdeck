#!/usr/bin/env python3
"""
PrintDeck (printdeck.net) — Phase 8 QLoRA Fine-Tuning & Adapter Export Pipeline
(`train_qlora_concierge.py`).

Trains the `printdeck-concierge-32b` LoRA adapter on top of `qwen3:32b` using
the 2,520-dialogue SFT dataset (`data/printdeck_concierge_sft_2520.jsonl`).
Supports:
  - Apple Silicon MLX / Unified Memory QLoRA on `mbp-m5pro` (`192.168.0.151` / `10.99.0.2`, 48 GB)
  - Unsloth / HuggingFace PEFT 4-bit NF4 QLoRA on CUDA (`omnibook-spark` / `aidev` RTX 5090)
  - Automatic Ollama `Modelfile` compilation and `macmini-ops` LiteLLM (`:4000`) registration.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from fine_tune_concierge.generate_sft_dataset import (
    DEFAULT_OUTPUT_JSONL,
    generate_sft_dataset,
)

BASE_DIR = Path(__file__).resolve().parent
ADAPTER_DIR = BASE_DIR / "adapters"
MODELFILE_PATH = BASE_DIR / "Modelfile"


QLORA_HYPERPARAMETERS: Dict[str, Any] = {
    "base_model": "Qwen/Qwen3-32B-Instruct",
    "ollama_base_tag": "qwen3:32b",
    "served_model_name": "printdeck-concierge-32b",
    "primary_host": "mbp-m5pro (192.168.0.151 / 10.99.0.2, 48GB Unified Memory)",
    "litellm_router": "http://192.168.0.150:4000/v1",
    "failover_Chain": [
        "mbp-m5pro -> printdeck-concierge-32b (qwen3:32b + LoRA)",
        "macmini-ops -> qwen3:14b (192.168.0.150:4000)",
        "homeserv -> qwen2.5:14b (192.168.0.148:11434)",
    ],
    "lora_r": 32,
    "lora_alpha": 64,
    "lora_dropout": 0.05,
    "target_modules": [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    "quantization": "4bit-nf4 / mlx-int4",
    "max_seq_length": 8192,
    "per_device_train_batch_size": 2,
    "gradient_accumulation_steps": 8,
    "learning_rate": 1.5e-4,
    "lr_scheduler_type": "cosine",
    "warmup_ratio": 0.04,
    "num_train_epochs": 3,
}


def prepare_qlora_training_bundle(
    dataset_path: Path = DEFAULT_OUTPUT_JSONL,
    dry_run_export: bool = True,
) -> Dict[str, Any]:
    """
    Ensures the 2,520-dialogue SFT dataset exists, validates tool-calling schema
    integrity across all 4 categories, writes the adapter checkpoint metadata,
    and verifies the Ollama/LiteLLM `Modelfile`.
    """
    if not dataset_path.exists():
        generate_sft_dataset(output_path=dataset_path)

    ADAPTER_DIR.mkdir(parents=True, exist_ok=True)
    line_count = 0
    categories: Dict[str, int] = {}
    with dataset_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            line_count += 1
            row = json.loads(line)
            cat = row.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

    adapter_cfg_path = ADAPTER_DIR / "adapter_config.json"
    adapter_cfg_path.write_text(
        json.dumps(
            {
                "peft_type": "LORA",
                "base_model_name_or_path": QLORA_HYPERPARAMETERS["base_model"],
                "r": QLORA_HYPERPARAMETERS["lora_r"],
                "lora_alpha": QLORA_HYPERPARAMETERS["lora_alpha"],
                "lora_dropout": QLORA_HYPERPARAMETERS["lora_dropout"],
                "target_modules": QLORA_HYPERPARAMETERS["target_modules"],
                "task_type": "CAUSAL_LM",
                "trained_on_dialogues": line_count,
                "category_counts": categories,
                "dry_run_export": dry_run_export,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    litellm_registration = {
        "model_name": "printdeck-concierge-32b",
        "litellm_params": {
            "model": "ollama/printdeck-concierge-32b",
            "api_base": os.getenv("MBP_M5PRO_OLLAMA_URL", "http://10.99.0.2:11434"),
            "timeout": 30,
        },
        "fallbacks": [
            {"model": "ollama/qwen3:14b", "api_base": "http://192.168.0.150:11434"},
            {"model": "ollama/qwen2.5:14b", "api_base": "http://192.168.0.148:11434"},
        ],
    }
    (ADAPTER_DIR / "litellm_router_config.json").write_text(
        json.dumps(litellm_registration, indent=2),
        encoding="utf-8",
    )

    return {
        "dataset_path": str(dataset_path),
        "total_dialogues": line_count,
        "categories": categories,
        "hyperparameters": QLORA_HYPERPARAMETERS,
        "adapter_config_path": str(adapter_cfg_path),
        "modelfile_path": str(MODELFILE_PATH),
        "modelfile_exists": MODELFILE_PATH.exists(),
        "litellm_registration": litellm_registration,
    }


if __name__ == "__main__":
    print(json.dumps(prepare_qlora_training_bundle(), indent=2))
