"""Reproducible 14-day synthetic sample and intentionally seeded billing issues."""
import argparse
import math
import random
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import text

from .db import ROOT, engine, install_views, read_sql, rows

CUSTOMERS = [
    (1, "Acme", 0.20, 102.0, 78.0),
    (2, "Globex", 0.20, 120.0, 72.0),
    (3, "Stark", 0.20, 158.0, 40.0),
    (4, "Wayne", 0.20, 91.0, 58.0),
    (5, "Umbrella", 0.20, 115.0, 68.0),
]
START = datetime(2026, 8, 1)
HOURS = 14 * 24


def build():
    rng = random.Random(20260925)
    usage, commitments = [], []
    for cid, name, _fee, base, commitment in CUSTOMERS:
        for h in range(HOURS):
            hour = START + timedelta(hours=h)
            day = h // 24
            cycle = 1 + 0.045 * math.sin(2 * math.pi * h / 24)
            noise = rng.uniform(0.97, 1.03)
            profile = (0.58 if cid == 2 and day >= 7 else
                       1.21 if cid == 5 and day >= 10 else 1.0)
            compute = round(base * cycle * noise * profile, 2)
            # Split eligible usage; S3 is ineligible for this simplified plan.
            for service, cost, eligible in (
                ("EC2", round(compute * 0.78, 2), 1),
                ("RDS", round(compute * 0.22, 2), 1),
                ("S3", round(base * 0.12 * noise, 2), 0),
            ):
                usage.append({"customer_id": cid, "usage_hour": hour.isoformat(timespec="seconds"),
                              "service": service, "on_demand_cost": cost, "eligible": eligible})
            commitments.append({"customer_id": cid, "usage_hour": hour.isoformat(timespec="seconds"),
                                "committed_spend": commitment, "discount_rate": 0.30})
    return usage, commitments


def reset_database(db):
    with db.begin() as conn:
        for view in ("portfolio_metrics", "hourly_metrics"):
            conn.execute(text(f"DROP VIEW IF EXISTS {view}"))
        for table in ("marketplace_billing", "commitments_hourly", "usage_hourly", "customers"):
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        for statement in read_sql("00_schema.sql").split(";"):
            if statement.strip():
                conn.execute(text(statement))


def seed(write_parquet=True):
    db = engine()
    reset_database(db)
    usage, commitments = build()
    with db.begin() as conn:
        conn.execute(text("INSERT INTO customers VALUES (:customer_id,:customer_name,:fee_rate)"),
                     [dict(zip(("customer_id", "customer_name", "fee_rate"), c[:3])) for c in CUSTOMERS])
        conn.execute(text("INSERT INTO usage_hourly VALUES "
                          "(:customer_id,:usage_hour,:service,:on_demand_cost,:eligible)"), usage)
        conn.execute(text("INSERT INTO commitments_hourly VALUES "
                          "(:customer_id,:usage_hour,:committed_spend,:discount_rate)"), commitments)
        install_views(conn)
        portfolio = rows(conn, "02_portfolio_metrics.sql")
        for p in portfolio:
            # Globex: underbilled; Acme: overbilled; Umbrella: missing invoice.
            if p["customer_name"] == "Umbrella":
                continue
            adjustment = {"Acme": 120.0, "Globex": -175.0}.get(p["customer_name"], 0.0)
            conn.execute(text("INSERT INTO marketplace_billing VALUES "
                              "(:customer_id,:billing_month,:invoice_id,:billed_fee,:payment_status)"),
                         {"customer_id": p["customer_id"], "billing_month": "2026-08",
                          "invoice_id": f"DEMO-2026-08-{p['customer_id']:03d}",
                          "billed_fee": round(float(p["expected_fee"]) + adjustment, 2),
                          "payment_status": "Paid" if p["customer_name"] in ("Acme", "Stark") else "Pending"})
    if write_parquet:
        destination = ROOT / "data"
        destination.mkdir(exist_ok=True)
        pd.DataFrame(usage).to_parquet(destination / "synthetic_usage.parquet", index=False)
        pd.DataFrame(commitments).to_csv(destination / "commitments.csv", index=False)
    print(f"Seeded {len(usage):,} usage rows, {len(commitments):,} commitment hours, 4 invoices.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-parquet", action="store_true", help="Skip example data export")
    args = parser.parse_args()
    seed(write_parquet=not args.no_parquet)
