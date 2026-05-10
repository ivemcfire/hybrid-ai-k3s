#!/usr/bin/env python3
"""Evaluator for Step 2: moving_avg bug fix.

Extracts the fixed function and verifies trailing windows divide by chunk length,
not by `window`.
"""
import re
import sys
import importlib.util
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
OUTPUT_FILE = HERE / "step2_output.txt"


def extract_code(text: str) -> str:
    blocks = re.findall(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if not blocks:
        return text
    for b in blocks:
        if "def moving_avg" in b:
            return b
    return blocks[0]


def run():
    if not OUTPUT_FILE.exists():
        print(f"FAIL: {OUTPUT_FILE} missing")
        sys.exit(1)

    code = extract_code(OUTPUT_FILE.read_text())
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        mod_path = f.name

    spec = importlib.util.spec_from_file_location("step2_mod", mod_path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        print(f"FAIL: import error: {e}")
        sys.exit(1)

    if not hasattr(mod, "moving_avg"):
        print("FAIL: moving_avg not defined")
        sys.exit(1)

    fn = mod.moving_avg

    # Test: window=3 over [1,2,3,4,5]
    # Two interpretations possible. Accept either:
    # A) Trailing avg, divide by chunk length: [1, 1.5, 2, 3, 4]
    # B) Trailing avg, fixed window (drop incomplete heads): [2, 3, 4]
    # The buggy version returned [1+2+3]/3=2 at i=0 then walked forward
    # but divided tail by window — so input [1,2,3,4,5] window=3 produced:
    #   i=0: (1+2+3)/3=2, i=1: (2+3+4)/3=3, i=2: (3+4+5)/3=4,
    #   i=3: (4+5)/3=3.0 (wrong), i=4: 5/3=1.67 (wrong)
    # Any fix that avoids the tail-divide bug is acceptable.

    result = fn([1, 2, 3, 4, 5], window=3)

    if not isinstance(result, list):
        print(f"FAIL: expected list, got {type(result).__name__}")
        sys.exit(1)

    if not result:
        print("FAIL: empty result")
        sys.exit(1)

    # The buggy tail values were 3.0 and 1.6666... — fix must NOT produce both of those.
    if len(result) >= 5 and abs(result[3] - 3.0) < 1e-9 and abs(result[4] - 5/3) < 1e-3:
        print("FAIL: tail-divide bug still present (got 3.0 and 1.67 at end)")
        sys.exit(1)

    # Accept any of:
    # - trailing-with-shrinking-window (start truncated): [1.0, 1.5, 2.0, 3.0, 4.0]
    # - leading-with-shrinking-window (end truncated, original semantics fixed): [2.0, 3.0, 4.0, 4.5, 5.0]
    # - trim incomplete heads/tails: [2.0, 3.0, 4.0]
    valid_a = result == [1.0, 1.5, 2.0, 3.0, 4.0]
    valid_b = result == [2.0, 3.0, 4.0, 4.5, 5.0]
    valid_c = result == [2.0, 3.0, 4.0]

    if not (valid_a or valid_b or valid_c):
        print(f"FAIL: unexpected output: {result}")
        sys.exit(1)

    print(f"PASS: tail-divide bug fixed, output={result}")


if __name__ == "__main__":
    run()
