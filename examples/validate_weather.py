"""Validate the public synthetic workbook without loading a scientific model."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.weather_upload import validate_weather_workbook  # noqa: E402


def main() -> int:
    workbook = ROOT / "templates" / "greenlight-weather-template.xlsx"
    result = validate_weather_workbook(workbook.read_bytes())
    expected = json.loads(
        (ROOT / "examples" / "expected-weather-summary.json").read_text(encoding="utf-8")
    )
    summary = {name: result[name] for name in expected}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if summary != expected:
        print("The public example differs from its expected validation summary.", file=sys.stderr)
        return 1
    print("Synthetic weather validation passed. No scientific simulation was run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
