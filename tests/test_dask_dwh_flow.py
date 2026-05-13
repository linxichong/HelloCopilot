from decimal import Decimal

from app.dask_dwh_flow import (
    _json_ready_summary,
    _merge_summaries,
    _normalize_for_analytics,
    _partition_summary,
)


def test_normalize_for_analytics_uses_status_amount_and_completed_flag():
    assert _normalize_for_analytics({"status": "paid", "amount": "12.30"}) == {
        "status": "paid",
        "amount": Decimal("12.30"),
    }
    assert _normalize_for_analytics({"completed": True}) == {
        "status": "done",
        "amount": Decimal("0"),
    }


def test_partition_summary_counts_records_status_and_amounts():
    summary = _partition_summary(
        [
            {"status": "done", "amount": Decimal("10.50")},
            {"status": "done", "amount": Decimal("2.00")},
            {"status": "open", "amount": Decimal("1.25")},
        ]
    )

    assert summary == {
        "record_count": 3,
        "status_counts": {"done": 2, "open": 1},
        "amount_total": Decimal("13.75"),
    }


def test_merge_summaries_and_json_ready_summary():
    summary = _merge_summaries(
        {"record_count": 2, "status_counts": {"done": 1, "open": 1}, "amount_total": Decimal("3.50")},
        {"record_count": 1, "status_counts": {"done": 1}, "amount_total": Decimal("4.00")},
    )

    assert _json_ready_summary(summary) == {
        "record_count": 3,
        "status_counts": {"done": 2, "open": 1},
        "amount_total": "7.50",
    }
