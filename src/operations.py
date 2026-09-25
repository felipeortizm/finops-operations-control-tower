"""Read models and human-actionable operational queue."""

from sqlalchemy import text

from .db import engine, rows


def load():
    db = engine()
    with db.connect() as conn:
        portfolio = rows(conn, "02_portfolio_metrics.sql")
        billing = rows(conn, "03_reconciliation.sql", billing_month="2026-08")
        risk = rows(conn, "04_commitment_risk.sql", cutoff="2026-08-08T00:00:00")
        quality = rows(conn, "05_data_quality.sql")
        daily = [dict(x) for x in conn.execute(text(
            "SELECT customer_id, SUBSTR(usage_hour,1,10) AS day, SUM(baseline) AS baseline, "
            "SUM(actual_cost) AS actual_cost, SUM(net_savings) AS net_savings "
            "FROM hourly_metrics GROUP BY customer_id, SUBSTR(usage_hour,1,10) ORDER BY day"
        )).mappings()]
    return portfolio, billing, risk, quality, daily


def make_queue(portfolio, billing, risk, quality):
    queue = []
    by_id = {p["customer_id"]: p for p in portfolio}
    for b in billing:
        if b["reconciliation_status"] != "Matched":
            queue.append({"priority": 1 if b["reconciliation_status"] == "Missing invoice" else 2,
                          "customer": b["customer_name"], "issue": b["reconciliation_status"],
                          "exposure": abs(float(b["variance"])),
                          "action": "Trace missing billing export before closing period" if b["invoice_id"] is None
                          else "Compare fee calculation with invoice line and correct source"})
    for r in risk:
        utilization = float(r["recent_utilization"])
        change = float(r["usage_change"])
        if utilization < 0.90 and float(r["unused"]) > 0:
            queue.append({"priority": 1, "customer": r["customer_name"],
                          "issue": f"Commitment utilization {utilization:.1%}; eligible usage {change:+.1%}",
                          "exposure": float(r["unused"]),
                          "action": "Review consumption trend and commitment exposure"})
        p = by_id[r["customer_id"]]
        if float(p["coverage"]) < 0.60 and utilization > 0.95:
            queue.append({"priority": 3, "customer": r["customer_name"],
                          "issue": f"Coverage opportunity {float(p['coverage']):.1%}",
                          "exposure": float(p["eligible_od"] - p["covered_od"]),
                          "action": "Assess stable eligible usage before considering more commitments"})
    for q in quality:
        if q["affected_rows"]:
            queue.append({"priority": 1, "customer": "Portfolio", "issue": q["issue"],
                          "exposure": 0.0, "action": "Repair source data before using metrics"})
    return sorted(queue, key=lambda x: (x["priority"], -x["exposure"], x["customer"]))
