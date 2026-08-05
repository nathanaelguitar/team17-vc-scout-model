from __future__ import annotations

import pandas as pd

from layer_b_transaction_observed_ranker import FEATURE_FAMILIES, NUMERIC, build_table


def _round(company: str, date: str, post: float = 0.0) -> dict:
    return {
        "company_key": company,
        "company_name": company,
        "event_date": pd.Timestamp(date),
        "transaction_id": f"{company}-{date}",
        "round_value_usd": 10_000_000.0,
        "post_money_usd": post,
        "investors": {"investor"},
        "investor_count": 1,
    }


def test_observed_labels_require_post_snapshot_event_or_followup():
    rounds = pd.DataFrame([
        _round("positive", "2018-01-01"), _round("positive", "2019-01-01"), _round("positive", "2020-01-01", 1_000_000_000.0),
        _round("negative", "2018-01-01"), _round("negative", "2019-01-01"), _round("negative", "2023-01-01"),
        _round("unknown", "2018-01-01"), _round("unknown", "2019-01-01"),
    ])
    result = build_table(rounds).set_index("company_key")
    assert result.loc["positive", "label_state"] == "observed_positive"
    assert result.loc["negative", "label_state"] == "observed_no_future_outcome"
    assert result.loc["unknown", "label_state"] == "insufficient_followup"


def test_ranker_feature_contract_excludes_outcome_and_source_fields():
    forbidden = {"post_money_usd", "first_observed_unicorn_date", "last_observed_transaction_date", "label_state", "source_file"}
    assert not forbidden.intersection(NUMERIC)
    assert not forbidden.intersection({feature for features in FEATURE_FAMILIES.values() for feature in features})
