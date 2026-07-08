"""Batched toxicity inference for the ML consumer.

Uses ``unitary/toxic-bert`` (multi-label classifier) loaded via
``ToxicityModelLoader``. Logits are converted to probabilities with
``sigmoid`` — not softmax, because each toxicity dimension is independent.

Note: toxic-bert exposes 6 labels (toxic, severe_toxic, obscene, threat,
insult, identity_hate). The civil_comments dataset defines 7 labels; there
is no ``sexual_explicit`` score from this model.
"""

from typing import Final

import torch

from model_loader import ToxicityModelLoader

# Map Hugging Face id2label names to PRD / scored_comments key names.
LABEL_KEY_MAP: Final[dict[str, str]] = {
    "toxic": "toxicity",
    "severe_toxic": "severe_toxicity",
    "obscene": "obscene",
    "threat": "threat",
    "insult": "insult",
    "identity_hate": "identity_attack",
}

_loader: ToxicityModelLoader | None = None


def _get_loader() -> ToxicityModelLoader:
    global _loader
    if _loader is None:
        _loader = ToxicityModelLoader()
    return _loader


def _normalize_label(raw_label: str) -> str:
    """Convert a model config label to a PRD-aligned score key."""
    key = raw_label.lower().replace(" ", "_").replace("-", "_")
    return LABEL_KEY_MAP.get(key, key)


def _logits_to_score_dict(
    logits: torch.Tensor,
    id2label: dict[int, str],
) -> dict[str, float]:
    """Convert a single row of logits to a label -> probability dict."""
    probs = torch.sigmoid(logits).tolist()
    scores: dict[str, float] = {}
    for idx, prob in enumerate(probs):
        raw = id2label.get(idx, f"label_{idx}")
        key = _normalize_label(raw)
        scores[key] = round(float(prob), 4)
    return scores


def score_text(
    text_batch: list[str],
    loader: ToxicityModelLoader | None = None,
) -> list[dict[str, float]]:
    """Score a batch of comment strings for toxicity dimensions.

    Args:
        text_batch: List of raw comment texts to classify.
        loader: Optional pre-initialized loader (for testing). Uses a
            module-level lazy singleton when omitted.

    Returns:
        One scores dictionary per input string, in the same order.
        Keys align with the PRD ``scored_comments`` schema where the model
        supports them (``toxicity``, ``severe_toxicity``, ``obscene``,
        ``threat``, ``insult``, ``identity_attack``).
    """
    if not text_batch:
        return []

    model_loader = loader or _get_loader()
    tokenizer, model = model_loader.load()
    id2label: dict[int, str] = model.config.id2label

    inputs = tokenizer(
        text_batch,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )

    with torch.no_grad():
        outputs = model(**inputs)

    return [
        _logits_to_score_dict(row, id2label)
        for row in outputs.logits
    ]


if __name__ == "__main__":
    samples = [
        "This is a test comment",
        "You are an idiot and I hope you die",
    ]
    results = score_text(samples)
    for text, scores in zip(samples, results):
        print(f"Text: {text!r}")
        print(f"Scores: {scores}\n")
