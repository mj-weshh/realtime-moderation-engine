"""Hugging Face toxicity model loader with local weight caching.

Downloads and loads a sequence-classification model (default: unitary/toxic-bert)
into ``ml_consumer/model_cache/`` so weights are not re-fetched on every run.
Kafka consumption and Neo4j integration are added in later phases.

Usage (from ml_consumer/, with the venv active)::

    python model_loader.py
"""

import os
from pathlib import Path
from typing import Final

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

DEFAULT_MODEL_ID: Final[str] = os.getenv("TOXICITY_MODEL_ID", "unitary/toxic-bert")
MODEL_CACHE_DIR: Final[Path] = Path(__file__).resolve().parent / "model_cache"


class ToxicityModelLoader:
    """Loads a toxicity classifier and tokenizer from a local Hugging Face cache."""

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        cache_dir: Path = MODEL_CACHE_DIR,
    ) -> None:
        self.model_id = model_id
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.tokenizer: AutoTokenizer | None = None
        self.model: AutoModelForSequenceClassification | None = None

    def load(self) -> tuple[AutoTokenizer, AutoModelForSequenceClassification]:
        """Download (if needed) and load the tokenizer and model from cache."""
        if self.tokenizer is not None and self.model is not None:
            return self.tokenizer, self.model

        cache_path = str(self.cache_dir)
        print(f"Loading model '{self.model_id}' from cache dir: {self.cache_dir}")

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_id,
            cache_dir=cache_path,
        )
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_id,
            cache_dir=cache_path,
        )
        self.model.eval()
        return self.tokenizer, self.model

    def predict_logits(self, text: str) -> torch.Tensor:
        """Tokenize ``text`` and return raw classification logits."""
        tokenizer, model = self.load()
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = model(**inputs)
        return outputs.logits


if __name__ == "__main__":
    test_text = "This is a test comment"
    loader = ToxicityModelLoader()
    tokenizer, model = loader.load()

    inputs = tokenizer(test_text, return_tensors="pt", truncation=True, max_length=512)
    print(f"Input text: {test_text!r}")
    print(f"Tokenized input_ids shape: {inputs['input_ids'].shape}")
    print(f"Tokenized input_ids: {inputs['input_ids'].tolist()}")

    with torch.no_grad():
        outputs = model(**inputs)

    print(f"Raw logits shape: {outputs.logits.shape}")
    print(f"Raw logits: {outputs.logits.tolist()}")
