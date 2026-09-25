import os
from pathlib import Path

import pytest
from sqlalchemy import text

from src.db import engine, rows
from src.operations import load, make_queue
from src.seed import seed


@pytest.fixture(scope="module", autouse=True)
def isolated_database(tmp_path_factory):
    target = tmp_path_factory.mktemp("db") / "test.db"
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{target}"
    seed(write_parquet=False)
    yield
    if previous is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous


def test_cost_identity_and_weighted_rates():
    portfolio, _, _, _, _ = load()
    for p in portfolio:
        assert float(p["baseline"]) == pytest.approx(float(p["actual_cost"]) + float(p["net_savings"]))
        assert 0 <= float(p["coverage"]) <= 1
        assert 0 <= float(p["utilization"]) <= 1
        assert float(p["expected_fee"]) == pytest.approx(round(max(float(p["net_savings"]), 0) * .2, 2), abs=.02)


def test_hourly_allocation_never_exceeds_eligible_usage_or_purchase():
    with engine().connect() as conn:
        bad = conn.execute(text("SELECT COUNT(*) FROM hourly_metrics WHERE covered_od > eligible_od + .0001 "
                                "OR applied_commitment > committed_spend + .0001 "
                                "OR ABS(baseline - actual_cost - net_savings) > .0001")).scalar_one()
    assert bad == 0


def test_seeded_reconciliation_cases_and_priorities():
    portfolio, billing, risk, quality, _ = load()
    statuses = {b["customer_name"]: b["reconciliation_status"] for b in billing}
    assert statuses == {"Acme": "Mismatch", "Globex": "Mismatch", "Stark": "Matched",
                        "Umbrella": "Missing invoice", "Wayne": "Matched"}
    queue = make_queue(portfolio, billing, risk, quality)
    assert any(x["customer"] == "Globex" and "utilization" in x["issue"] for x in queue)
    assert queue == sorted(queue, key=lambda x: (x["priority"], -x["exposure"], x["customer"]))


def test_seed_data_has_no_structural_quality_issues():
    _, _, _, quality, _ = load()
    assert all(q["affected_rows"] == 0 for q in quality)


def test_usage_drop_reduces_recent_globex_utilization():
    _, _, risk, _, _ = load()
    globex = next(r for r in risk if r["customer_name"] == "Globex")
    assert float(globex["usage_change"]) < -0.35
    assert float(globex["recent_utilization"]) < .90
