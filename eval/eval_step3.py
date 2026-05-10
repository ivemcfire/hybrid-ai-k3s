#!/usr/bin/env python3
"""Evaluator for Step 3: combined module + tests.

Extracts both code blocks, writes them to disk, attempts to import the module
and run summarize() on sample.csv. Captures structural and semantic failures.
"""
import re
import sys
import importlib.util
from pathlib import Path

HERE = Path(__file__).parent
OUTPUT_FILE = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "step3_output.txt"
CSV_FILE = HERE / "sample.csv"


def extract_blocks(text: str) -> list[tuple[str, str]]:
    """Return list of (filename, code) tuples."""
    pattern = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)
    blocks = pattern.findall(text)
    out = []
    for b in blocks:
        first_line = b.lstrip().splitlines()[0] if b.strip() else ""
        m = re.match(r"#\s*([\w./-]+\.py)", first_line)
        name = m.group(1) if m else None
        out.append((name, b))
    return out


def main():
    text = OUTPUT_FILE.read_text()
    blocks = extract_blocks(text)

    fails = []
    if len(blocks) < 2:
        fails.append(f"expected 2 code blocks, got {len(blocks)}")

    module_block = next((b for n, b in blocks if n and "test" not in n.lower()), None)
    test_block = next((b for n, b in blocks if n and "test" in n.lower()), None)

    if module_block is None:
        fails.append("module block not identified")
    if test_block is None:
        fails.append("test block not identified")

    if module_block:
        mod_path = HERE / "_step3_summary.py"
        mod_path.write_text(module_block)

        spec = importlib.util.spec_from_file_location("step3_summary", mod_path)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            fails.append(f"module import error: {e}")
        else:
            if not hasattr(mod, "summarize"):
                fails.append("summarize() not defined")
            else:
                try:
                    result = mod.summarize(str(CSV_FILE), window=3)
                except Exception as e:
                    fails.append(f"summarize() raised: {e}")
                else:
                    if not isinstance(result, dict):
                        fails.append(f"summarize() returned {type(result).__name__}, expected dict")
                    else:
                        # Check keys are tuples
                        bad_keys = [k for k in result if not (isinstance(k, tuple) and len(k) == 2)]
                        if bad_keys:
                            fails.append(f"non-tuple keys: {bad_keys[:3]}")

                        # Check values are list of floats (no None, no mixed types)
                        for k, v in result.items():
                            if not isinstance(v, list):
                                fails.append(f"value for {k} is not list: {type(v).__name__}")
                                continue
                            non_floats = [x for x in v if not isinstance(x, (float, int))]
                            if non_floats:
                                fails.append(f"non-float entries in {k}: {non_floats[:3]}")
                                break

                        # Expected groups based on sample.csv
                        expected = {
                            ("one61", "soil_moisture"),
                            ("one61", "temperature"),
                            ("one62", "soil_moisture"),
                        }
                        actual_keys = set(result.keys())
                        if actual_keys != expected:
                            fails.append(f"key mismatch: got {actual_keys}, expected {expected}")

                        # Spec: list of MA values per group, one per reading.
                        # one61/soil_moisture has 4 readings -> list len should be 4
                        soil_61 = result.get(("one61", "soil_moisture"))
                        if soil_61 is not None and len(soil_61) < 2:
                            fails.append(
                                f"summarize() returned single-element list for one61/soil_moisture "
                                f"(len={len(soil_61)}); spec requires one MA per reading (4 expected)"
                            )

    if test_block:
        # Smoke check: imports + at least one assert
        if "import pytest" not in test_block:
            fails.append("test file missing 'import pytest'")
        if "def test_" not in test_block:
            fails.append("test file has no test_ functions")
        # Skip CSV-fixture check — tests may create files inline.

    if fails:
        print("FAIL:")
        for f in fails:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("PASS")


if __name__ == "__main__":
    main()
