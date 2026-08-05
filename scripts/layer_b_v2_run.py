"""Run the coverage-aware Layer B v2 table build from the project root."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from layer_b_v2_pipeline import DataContractError, run


if __name__ == "__main__":
    try:
        print(json.dumps(run(), indent=2))
    except DataContractError as error:
        raise SystemExit(f"Layer B v2 data contract not satisfied: {error}")
