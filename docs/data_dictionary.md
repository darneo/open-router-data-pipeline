# Data dictionary

The source dataset is collected from the public OpenRouter Models API. `created` is supplied as a Unix timestamp in seconds. `prompt_price` is the provider's input price per token, as returned by the API; the cleaner derives USD per one million input tokens by multiplying it by 1,000,000. Missing prices remain missing and are classified as `unknown` instead of being treated as zero.

## Flattened API and Kafka record (`data/models.jsonl`)

| Field | Type | Meaning | Validation / handling |
|---|---|---|---|
| `model_id` | string | API model identifier; also the Kafka key and SQLite primary key | Required, non-empty, unique in the dataset |
| `name` | string | Human-readable model name | Required, non-empty |
| `provider` | string | Prefix before `/` in `model_id` | Required, non-empty; trimmed and lowercased during cleaning |
| `created` | integer | Unix timestamp in seconds | Required and greater than zero; converted to UTC `created_at` |
| `context_length` | integer | Maximum context length in tokens | Required and greater than zero |
| `input_modalities` | string | Comma-separated input modality names | Required, non-empty; trimmed and lowercased |
| `output_modalities` | string | Comma-separated output modality names | Required, non-empty; trimmed and lowercased |
| `prompt_price` | number or null | API prompt/input price per token | Null allowed; otherwise non-negative |

## Processed SQLite table (`models`)

| Field | SQLite type | Meaning |
|---|---|---|
| `model_id` | TEXT PRIMARY KEY | Stable model identifier; prevents duplicate rows |
| `name` | TEXT NOT NULL | Model name |
| `provider` | TEXT NOT NULL | Normalized provider |
| `created_at` | TEXT NOT NULL | UTC ISO-style timestamp derived from `created` |
| `context_length` | INTEGER NOT NULL | Valid context size in tokens |
| `input_modalities` | TEXT NOT NULL | Normalized inputs |
| `output_modalities` | TEXT NOT NULL | Normalized outputs |
| `prompt_price` | REAL | Price per token, nullable |
| `input_cost_per_million` | REAL | Prompt price multiplied by one million |
| `price_band` | TEXT NOT NULL | `unknown`, `free`, `below_median`, or `at_or_above_median` |
