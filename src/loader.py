"""Load cleaned models into SQLite and prove repeated loads are idempotent."""

from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

from src.config import DATA_DIR

DB_PATH = DATA_DIR / "models.db"
TABLE_COLUMNS = [
    "model_id",
    "name",
    "provider",
    "created_at",
    "context_length",
    "input_modalities",
    "output_modalities",
    "prompt_price",
    "input_cost_per_million",
    "price_band",
]


def sqlite_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def main() -> None:
    frame = pd.read_csv(DATA_DIR / "processed_models.csv")
    rows = [
        tuple(sqlite_value(record[column]) for column in TABLE_COLUMNS)
        for record in frame.to_dict(orient="records")
    ]
    create_table = """
    CREATE TABLE IF NOT EXISTS models (
        model_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        provider TEXT NOT NULL,
        created_at TEXT NOT NULL,
        context_length INTEGER NOT NULL CHECK (context_length > 0),
        input_modalities TEXT NOT NULL,
        output_modalities TEXT NOT NULL,
        prompt_price REAL CHECK (prompt_price IS NULL OR prompt_price >= 0),
        input_cost_per_million REAL,
        price_band TEXT NOT NULL
    )
    """
    insert_sql = """
    INSERT INTO models (
        model_id, name, provider, created_at, context_length,
        input_modalities, output_modalities, prompt_price,
        input_cost_per_million, price_band
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(model_id) DO UPDATE SET
        name=excluded.name,
        provider=excluded.provider,
        created_at=excluded.created_at,
        context_length=excluded.context_length,
        input_modalities=excluded.input_modalities,
        output_modalities=excluded.output_modalities,
        prompt_price=excluded.prompt_price,
        input_cost_per_million=excluded.input_cost_per_million,
        price_band=excluded.price_band
    """

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(create_table)
        connection.execute("DELETE FROM models")
        connection.executemany(insert_sql, rows)
        connection.commit()
        first_rows = connection.execute(
            "SELECT * FROM models ORDER BY model_id"
        ).fetchall()
        first_count = connection.execute("SELECT COUNT(*) FROM models").fetchone()[0]

        connection.executemany(insert_sql, rows)
        connection.commit()
        second_rows = connection.execute(
            "SELECT * FROM models ORDER BY model_id"
        ).fetchall()
        stored_count = connection.execute("SELECT COUNT(*) FROM models").fetchone()[0]
        unique_count = connection.execute(
            "SELECT COUNT(DISTINCT model_id) FROM models"
        ).fetchone()[0]

    idempotent = first_rows == second_rows and first_count == stored_count
    if not idempotent:
        raise RuntimeError("Second SQLite load changed or duplicated stored records")
    if stored_count != len(rows) or unique_count != len(rows):
        raise RuntimeError(
            f"SQLite count mismatch: input={len(rows)}, rows={stored_count}, unique={unique_count}"
        )


if __name__ == "__main__":
    main()
