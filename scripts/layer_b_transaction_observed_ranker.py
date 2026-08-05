"""Build and validate the provisional transaction-observed ranking model."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from layer_b_transaction_observed_ranker import run

if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
