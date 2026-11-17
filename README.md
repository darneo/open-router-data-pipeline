# OpenRouter Models: Kafka and Pandera Pipeline

An end-to-end data collection and preparation project for the SIS2 course. It fetches the public OpenRouter Models API, preserves the raw response, streams flattened model records through a real Apache Kafka broker, validates and transforms them, stores them in SQLite, and generates exploratory figures.

## Data source

- Endpoint: `https://openrouter.ai/api/v1/models?output_modalities=all`
- Request parameter: `output_modalities=all`
- Authentication: not required for this public endpoint
- Original response: `data/raw_models.json`
- Flattened UTF-8 JSON Lines: `data/models.jsonl`
- Fields include model ID, name, provider, Unix creation time, context length, input/output modalities, and prompt price.

The API catalog changes over time; rerunning the project collects a fresh snapshot.

## Requirements

- Python 3.11 or later
- Docker Desktop with Docker Compose and a running Linux container engine
- Internet access to the OpenRouter Models API
- Windows PowerShell commands below can be adapted to another shell

## Installation

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The API is public and requires no API key. Do not add private credentials to the repository.

## Kafka setup

The project uses the official Apache Kafka Docker image in KRaft mode. Start the broker manually when testing stages individually:

```powershell
docker compose up -d
docker compose ps
```

Create or reset the project's single-partition topic before a standalone Producer run:

```powershell
python -m src.kafka_setup
```

`src.kafka_setup` deletes the existing `openrouter-models` topic and recreates it. This removes old messages so the Consumer starts at offset zero and count comparisons describe one run.

## Execute the complete pipeline

From the project directory:

```powershell
python main.py
```

`main.py` starts Kafka through Docker Compose, waits for broker metadata, fetches a new API snapshot, resets the topic, then runs the Producer, Consumer, Pandera validator, cleaner, SQLite loader, and EDA in order. It stops with an error if API, Kafka, validation, cleaning, or database counts do not reconcile. The Consumer derives its target from non-empty lines in `data/models.jsonl`; no expected count is hard-coded.

## Run individual stages

Start Docker and create a clean topic first. Then run:

```powershell
python -m src.api_client
python -m src.kafka_setup
python -m src.producer
python -m src.consumer
python -m src.validator
python -m src.cleaner
python -m src.loader
python -m src.analysis
```

The standalone Consumer reads the number of records in `data/models.jsonl`. Its unique group ID and `auto.offset.reset=earliest` make each run consume from the topic beginning. A finite deadline prevents an endless wait if the expected records are unavailable.

## Outputs

- `data/raw_models.json`: preserved API response
- `data/models.jsonl`: flattened source records
- `data/consumed_models.jsonl`: JSON messages read from Kafka
- `data/valid_models.jsonl` and `data/invalid_models.jsonl`: validation results and error reasons
- `data/validation_test_results.json`: deliberately invalid examples detected by Pandera; excluded from final data
- `data/processed_models.csv`, `data/filtered_models.csv`, `data/grouped_by_provider.csv`, `data/pivot_provider_modality.csv`: transformations
- `data/models.db`: SQLite database with `models.model_id` as primary key
- `figures/`: three EDA plots

## Database verification

The loader rebuilds the table from the latest cleaned dataset, then inserts the same rows a second time using `ON CONFLICT(model_id) DO UPDATE`. It compares the database snapshots and checks that processed, stored, and unique-key counts agree. SQL verification queries are in `docs/verification_queries.sql`.

## Reproducibility and troubleshooting

- Confirm Docker is running with `docker compose ps` if the pipeline cannot connect to Kafka.
- If the public API is temporarily unavailable, the request raises its HTTP/network error and stops before replacing downstream outputs.
- If the Consumer times out, compare the published count and `models.jsonl` line count, then reset the topic and rerun `python main.py`.
- Stop the broker with `docker compose down` when finished. This stops the container; do not use `-v` unless you intend to remove Docker volumes.

## Project structure

```text
README.md
requirements.txt
main.py
compose.yaml
src/
  api_client.py
  kafka_setup.py
  producer.py
  consumer.py
  validator.py
  cleaner.py
  loader.py
  analysis.py
docs/
  data_dictionary.md
  verification_queries.sql
data/
figures/
```
