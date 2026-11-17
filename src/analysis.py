"""Run descriptive EDA and save three figures from the SQLite dataset."""

from __future__ import annotations

import sqlite3

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src.config import DATA_DIR, FIGURES_DIR


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATA_DIR / "models.db") as connection:
        frame = pd.read_sql_query("SELECT * FROM models ORDER BY model_id", connection)
    if frame.empty:
        raise RuntimeError("SQLite contains no models to analyze")

    frame["created_at"] = pd.to_datetime(frame["created_at"], utc=True, errors="coerce")
    print(f"Rows and columns: {frame.shape}")
    print("\nData types:")
    print(frame.dtypes.to_string())
    print("\nNumeric descriptive statistics:")
    print(frame[["context_length", "prompt_price", "input_cost_per_million"]].describe())
    print("\nTop output modalities:")
    print(frame["output_modalities"].value_counts().head(10).to_string())
    print("\nTop providers:")
    print(frame["provider"].value_counts().head(10).to_string())
    print(f"\nFree models: {int(frame['price_band'].eq('free').sum())}")
    print(f"Unknown-price models: {int(frame['price_band'].eq('unknown').sum())}")
    print(f"Median context length: {frame['context_length'].median():,.0f} tokens")
    print(f"Median input price: ${frame['input_cost_per_million'].median():,.4f} per 1M tokens")

    sns.set_theme(style="whitegrid", context="notebook")

    modality_counts = frame["output_modalities"].value_counts().head(12)
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(x=modality_counts.values, y=modality_counts.index, color="#4c78a8", ax=ax)
    ax.set(title="OpenRouter models by output modality", xlabel="Model count", ylabel="Output modality")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "models_by_modality.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.histplot(data=frame, x="context_length", bins=25, color="#4c78a8", ax=ax)
    ax.set_xscale("log")
    ax.set(title="Distribution of model context length", xlabel="Context length in tokens (log scale)", ylabel="Model count")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "context_length_distribution.png", dpi=180)
    plt.close(fig)

    priced = frame.dropna(subset=["input_cost_per_million"]).copy()
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(
        data=priced,
        x="context_length",
        y="input_cost_per_million",
        hue="output_modalities",
        alpha=0.72,
        s=45,
        ax=ax,
    )
    ax.set_xscale("log")
    ax.set_yscale("symlog", linthresh=0.01)
    ax.set(title="Context length and input price", xlabel="Context length in tokens (log scale)", ylabel="USD per 1M input tokens (symlog scale)")
    ax.legend(title="Output modality", bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "context_vs_cost.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    figures = [
        "figures/models_by_modality.png",
        "figures/context_length_distribution.png",
        "figures/context_vs_cost.png",
    ]
    for figure in figures:
        print(figure)


if __name__ == "__main__":
    main()
