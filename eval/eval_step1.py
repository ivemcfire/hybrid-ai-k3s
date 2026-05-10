#!/usr/bin/env python3
"""Evaluator for Step 1: parse_sensor_csv.

Extracts the function from the model's output, runs it against sample.csv,
checks correctness.
"""
import re
import sys
import importlib.util
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
OUTPUT_FILE = HERE / "step1_output.txt"
CSV_FILE = HERE / "sample.csv"

EXPECTED_GOOD_ROWS = 9  # 10 data rows minus 1 with value="broken"


def extract_code(text: str) -> str:
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if not m:
        return text  # assume raw code
    return m.group(1)


def run():
    if not OUTPUT_FILE.exists():
        print(f"FAIL: {OUTPUT_FILE} missing")
        sys.exit(1)

    code = extract_code(OUTPUT_FILE.read_text())
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        mod_path = f.name

    spec = importlib.util.spec_from_file_location("step1_mod", mod_path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        print(f"FAIL: import error: {e}")
        sys.exit(1)

    if not hasattr(mod, "parse_sensor_csv"):
        print("FAIL: parse_sensor_csv not defined")
        sys.exit(1)

    try:
        result = mod.parse_sensor_csv(str(CSV_FILE))
    except Exception as e:
        print(f"FAIL: function raised: {e}")
        sys.exit(1)

    if not isinstance(result, list):
        print(f"FAIL: expected list, got {type(result).__name__}")
        sys.exit(1)

    if len(result) != EXPECTED_GOOD_ROWS:
        print(f"FAIL: expected {EXPECTED_GOOD_ROWS} rows, got {len(result)}")
        sys.exit(1)

    sample = result[0]
    if not isinstance(sample, dict):
        print(f"FAIL: rows must be dicts, got {type(sample).__name__}")
        sys.exit(1)

    required = {"timestamp", "node_id", "sensor", "value"}
    if not required.issubset(sample.keys()):
        print(f"FAIL: missing keys; got {set(sample.keys())}")
        sys.exit(1)

    if not isinstance(sample["value"], float):
        print(f"FAIL: value must be float, got {type(sample['value']).__name__}")
        sys.exit(1)

    print(f"PASS: parsed {len(result)} rows, dropped 1 bad row, types correct")


if __name__ == "__main__":
    run()
