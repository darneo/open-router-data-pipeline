from __future__ import annotations
import json
import pandas as pd
import pandera.pandas as pa
from src.config import DATA_DIR


def nonempty(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().str.len().gt(0)


SCHEMA = pa.DataFrameSchema(
    {
        "model_id": pa.Column(
            str, 
            checks=pa.Check(nonempty), 
            nullable=False, 
            unique=True
        ),
        "name": pa.Column(
            str, 
            checks=pa.Check(nonempty), 
            nullable=False
        ),
        "provider": pa.Column(
            str, 
            checks=pa.Check(nonempty), 
            nullable=False
        ),

        "created": pa.Column(int, 
            checks=pa.Check.greater_than(0),
            nullable=False, 
            coerce=True
        ),
        "context_length": pa.Column(
            int, 
            checks=pa.Check.greater_than(0), 
            nullable=False, coerce=True
        ),
        "input_modalities": pa.Column(
            str, 
            checks=pa.Check(nonempty), 
            nullable=False
        ),
        "output_modalities": pa.Column(
            str, 
            checks=pa.Check(nonempty), 
            nullable=False
        ),
        "prompt_price": pa.Column(
            float,
            checks=pa.Check.greater_than_or_equal_to(0),
            nullable=True,
            coerce=True,
        ),
    },
    strict=False,
)


def validate_one(record: dict) -> list[str]:
    try:
        SCHEMA.validate(pd.DataFrame([record]), lazy=True)
        return []
    except (pa.errors.SchemaError, pa.errors.SchemaErrors) as error:
        cases = getattr(error, "failure_cases", None)
        if isinstance(cases, pd.DataFrame) and not cases.empty:
            failures = []
            for _, case in cases.iterrows():
                column = case.get("column") or "record"
                value = case.get("failure_case")
                failures.append(f"{column}: {value}")
            return sorted(set(failures))
        return [str(error)]


def check_synthetic_failures(template: dict) -> list[dict]:
    cases = [
        ("empty model id", "model_id", {"model_id": ""}),
        ("non-positive context", "context_length", {"context_length": 0}),
        ("negative prompt price", "prompt_price", {"prompt_price": -1.0}),
    ]
    results = []
    for name, expected_field, changes in cases:
        record = {**template, **changes}
        errors = validate_one(record)
        detected = any(error.startswith(f"{expected_field}:") for error in errors)
        results.append({
            "test_case": name,
            "expected_rule": expected_field,
            "detected": detected,
            "errors": errors,
            "test_record": record,
            "excluded_from_final_dataset": True,
        })
    if not all(result["detected"] for result in results):
        failed = [result["test_case"] for result in results if not result["detected"]]
        raise RuntimeError(f"Pandera failed to detect synthetic invalid cases: {failed}")
    (DATA_DIR / "validation_test_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return results


def main() -> None:
    input_path = DATA_DIR / "consumed_models.jsonl"
    records = [
        json.loads(line)
        for line in input_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    valid, invalid, seen_ids = [], [], set()
    for row_number, record in enumerate(records, start=1):
        errors = validate_one(record)
        model_id = record.get("model_id")
        if model_id in seen_ids:
            errors.append("model_id: duplicate")
        if model_id:
            seen_ids.add(model_id)
        if errors:
            invalid.append({"row_number": row_number, "record": record, "errors": errors})
        else:
            valid.append(record)

    (DATA_DIR / "valid_models.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in valid),
        encoding="utf-8",
    )
    (DATA_DIR / "invalid_models.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in invalid),
        encoding="utf-8",
    )
    valid_template = next((record for record in records if not validate_one(record)), None)
    if valid_template is None:
        raise RuntimeError("No valid template record is available for synthetic rule checks")
    synthetic = check_synthetic_failures(valid_template)
    print(f"Valid records: {len(valid)}")

if __name__ == "__main__":
    main()
