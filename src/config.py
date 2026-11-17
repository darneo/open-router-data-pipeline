"""Shared project paths and Kafka settings."""

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
FIGURES_DIR = PROJECT_DIR / "figures"
API_URL = "https://openrouter.ai/api/v1/models?output_modalities=all"
BOOTSTRAP_SERVERS = "localhost:9092"
TOPIC = "openrouter-models"
MINIMUM_RECORDS = 200
