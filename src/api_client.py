"""Fetch and preserve OpenRouter's public model catalog."""

from __future__ import annotations

import json
from typing import Any

import requests

from src.config import API_URL, DATA_DIR, MINIMUM_RECORDS


def flatten_model(model: dict[str, Any]) -> dict[str, Any]:
    model_id = model.get("id")
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("API record is missing a non-empty model id")
    architecture = model.get("architecture") or {}
    pricing = model.get("pricing") or {}
    price = pricing.get("prompt")
    return {
        "model_id": model_id.strip(),
        "name": model.get("name"),
        "provider": model_id.split("/", 1)[0] if "/" in model_id else "unknown",
        "created": model.get("created"),
        "context_length": model.get("context_length"),
        "input_modalities": ", ".join(architecture.get("input_modalities") or []),
        "output_modalities": ", ".join(architecture.get("output_modalities") or []),
        "prompt_price": float(price) if price is not None else None,
    }


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        response = requests.get(API_URL, timeout=(10, 60))
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(f"OpenRouter API request failed: {error}") from error
    try:
        payload = response.json()
    except requests.JSONDecodeError as error:
        raise RuntimeError("OpenRouter returned a response that is not valid JSON") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError("Unexpected API response: expected an object with a data list")

    models = payload["data"]
    if len(models) < MINIMUM_RECORDS:
        raise RuntimeError(
            f"API returned {len(models)} records; at least {MINIMUM_RECORDS} are required"
        )
    raw_path = DATA_DIR / "raw_models.json"
    raw_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    records = [flatten_model(model) for model in models]
    ids = [record["model_id"] for record in records]
    if len(set(ids)) != len(ids):
        raise RuntimeError("API response contains duplicate model IDs")

    jsonl_path = DATA_DIR / "models.jsonl"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
