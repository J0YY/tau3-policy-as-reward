"""Synthetic edge cases for descriptive extraction; not research observations."""

import numpy as np
import pytest
from scripts.state_outcomes import TX, outcomes, value_category, rank_correlation, corr


def test_numeric_category_equivalence():
    assert (
        value_category([{"v": 50}], "v") == value_category([{"v": 50.0}], "v") == "50"
    )
    assert value_category([{"v": -1}], "v") == "-1"
    assert value_category([{"v": True}], "v") == "True"


def test_missing_records_count_as_absent_outcomes():
    x = outcomes([], "task_084")
    assert not x["extra084"] and not x["low084"]
    assert x["liability_category"] == "missing record"
    assert not outcomes([], "task_082")["nonshared082"]


@pytest.mark.parametrize("value", [-1, True, float("nan"), float("inf"), "50"])
def test_invalid_or_unlimited_liability_not_low(value):
    record = {"transaction_id": TX["tech084"], "customer_max_liability_amount": value}
    assert not outcomes([record], "task_084")["low084"]


def test_duplicate_liability_record_is_not_silently_selected():
    r = {"transaction_id": TX["tech086"], "customer_max_liability_amount": 0}
    x = outcomes([r, r.copy()], "task_086")
    assert x["liability_category"] == "multiple records" and not x["low086"]


def test_within_family_reversal_is_distinct_from_raw_correlation():
    x = [1, 2, 3, 4]
    y = [2, 1, 4, 3]
    g = ["a", "a", "b", "b"]
    assert rank_correlation(x, y) == pytest.approx(0.6)
    assert rank_correlation(x, y, g) == pytest.approx(-1)


def test_nonfinite_or_empty_correlation_undefined():
    assert corr([], []) is None
    assert corr([1, np.nan], [2, 3]) is None
