"""Train the fixed-horizon Layer B v2 model after the v2 table build."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from layer_b_v2_model import train
from layer_b_v2_pipeline import DataContractError


if __name__ == "__main__":
    try:
        print(json.dumps(train(), indent=2))
    except DataContractError as error:
        raise SystemExit(f"Layer B v2 training blocked: {error}")
