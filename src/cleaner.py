"""Clean validated records and create grouped and reshaped tables."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.config import DATA_DIR


def main() -> None:
    records = [
        json.loads(line)
        for line in (DATA_DIR / "valid_models.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    frame = pd.DataFrame(records)
    if frame.empty:
        raise RuntimeError("No valid records are available for cleaning")

    missing_before = frame.isna().sum().astype(int).to_dict()
    print("Missing values before cleaning:")
    print(pd.Series(missing_before).to_string())
    before_deduplication = len(frame)
    frame = frame.drop_duplicates(subset="model_id", keep="first").copy()
    duplicates_removed = before_deduplication - len(frame)

    frame["created_at"] = pd.to_datetime(frame["created"], unit="s", utc=True)
    for column in ("provider", "input_modalities", "output_modalities"):
        frame[column] = frame[column].astype("string").str.strip().str.lower()
    frame["context_length"] = pd.to_numeric(frame["context_length"], errors="raise").astype("int64")
    frame["prompt_price"] = pd.to_numeric(frame["prompt_price"], errors="coerce")
    frame["input_cost_per_million"] = frame["prompt_price"] * 1_000_000

    known_prices = frame["prompt_price"].dropna()
    median_price = float(known_prices.median()) if not known_prices.empty else 0.0
    frame["price_band"] = np.select(
        [
            frame["prompt_price"].isna(),
            frame["prompt_price"].eq(0),
            frame["prompt_price"].lt(median_price),
        ],
        ["unknown", "free", "below_median"],
        default="at_or_above_median",
    )

    median_context = frame["context_length"].median()
    filtered = frame.loc[
        (frame["context_length"] >= median_context)
        & frame["input_modalities"].str.contains("text", na=False)
    ].copy()
    grouped = frame.groupby("provider", as_index=False).agg(
        model_count=("model_id", "count"),
        mean_context_length=("context_length", "mean"),
        median_input_cost=("input_cost_per_million", "median"),
    )
    pivot = frame.pivot_table(
        index="provider",
        columns="output_modalities",
        values="model_id",
        aggfunc="count",
        fill_value=0,
    )

    frame.to_csv(DATA_DIR / "processed_models.csv", index=False)
    filtered.to_csv(DATA_DIR / "filtered_models.csv", index=False)
    grouped.to_csv(DATA_DIR / "grouped_by_provider.csv", index=False)
    pivot.to_csv(DATA_DIR / "pivot_provider_modality.csv")
    print(f"Validated input rows: {before_deduplication}")
    print(f"Duplicates removed: {duplicates_removed}")
    print(f"Rows after cleaning: {len(frame)}")
    print(f"Rows after filtering: {len(filtered)}")
    print(f"Missing prompt prices retained as unknown: {int(frame['prompt_price'].isna().sum())}")
    print(f"Filter conditions: context_length >= {median_context:g} and input includes text")
    print(f"Provider groups: {len(grouped)}; pivot rows: {len(pivot)}")

if __name__ == "__main__":
    main()
