"""Download the google/civil_comments dataset and export it as Parquet.

Exports all three splits (train / validation / test) to the repo-root
``data/`` directory (gitignored), plus a lightweight text-only subset of
the test split used by the producer service for fast local testing.

Usage (from producer_service/, with the venv active)::

    python fetch_data.py

The script is idempotent: splits whose Parquet files already exist are
skipped, so it can be re-run safely to resume a partial download.
"""

from pathlib import Path
from typing import Final

from datasets import Dataset, load_dataset

DATASET_NAME: Final[str] = "google/civil_comments"
SPLITS: Final[tuple[str, ...]] = ("train", "validation", "test")

# Repo-root data directory, shared with the future ml_consumer fine-tuning
# work (train/validation splits). Resolved relative to this file so the
# script works regardless of the current working directory.
DATA_DIR: Final[Path] = Path(__file__).resolve().parents[1] / "data"

SUBSET_PATH: Final[Path] = DATA_DIR / "comments_subset.parquet"


def split_path(split: str) -> Path:
    """Return the Parquet output path for a full dataset split."""
    return DATA_DIR / f"civil_comments_{split}.parquet"


def fetch_split(split: str) -> None:
    """Download a single split and export it to Parquet, skipping if present."""
    target = split_path(split)
    if target.exists():
        print(f"[skip] {target.name} already exists")
        return

    print(f"[download] {DATASET_NAME} split={split} ...")
    dataset: Dataset = load_dataset(DATASET_NAME, split=split)
    dataset.to_parquet(str(target))
    print(f"[saved] {target.name}: {dataset.num_rows:,} rows")


def build_test_subset() -> None:
    """Write a text-only subset of the test split for fast local testing."""
    if SUBSET_PATH.exists():
        print(f"[skip] {SUBSET_PATH.name} already exists")
        return

    print("[subset] building text-only test subset ...")
    dataset: Dataset = load_dataset(DATASET_NAME, split="test")
    subset = dataset.select_columns(["text"])
    subset.to_parquet(str(SUBSET_PATH))
    print(f"[saved] {SUBSET_PATH.name}: {subset.num_rows:,} rows")


def main() -> None:
    """Fetch all splits and build the local-testing subset."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for split in SPLITS:
        fetch_split(split)
    build_test_subset()
    print(f"\nDone. Files in {DATA_DIR}:")
    for file in sorted(DATA_DIR.glob("*.parquet")):
        size_mb = file.stat().st_size / (1024 * 1024)
        print(f"  {file.name}  ({size_mb:,.1f} MB)")


if __name__ == "__main__":
    main()
