"""Producer service entry point.

Day 4 scope: verify local data ingestion by loading the text-only test
subset produced by ``fetch_data.py`` and printing a preview. The Kafka
publishing logic will be added in the next phase.
"""

from pathlib import Path
from typing import Final

import pandas as pd

SUBSET_PATH: Final[Path] = (
    Path(__file__).resolve().parents[1] / "data" / "comments_subset.parquet"
)


def load_comments(path: Path = SUBSET_PATH) -> pd.DataFrame:
    """Load the local comments subset into a DataFrame.

    Raises:
        FileNotFoundError: If the subset has not been generated yet
            (run ``fetch_data.py`` first).
    """
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run 'python fetch_data.py' to download the data."
        )
    return pd.read_parquet(path)


def main() -> None:
    """Verify ingestion: load the subset and print a preview."""
    df = load_comments()
    print(f"Loaded {len(df):,} rows, columns: {list(df.columns)}\n")
    print(df.head(5).to_string())


if __name__ == "__main__":
    main()
