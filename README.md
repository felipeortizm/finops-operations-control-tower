# FinOps Operations Control Tower

**A small, runnable operations system for cloud commitment risk and billing reconciliation.** It turns synthetic AWS-like hourly usage into a prioritized review queue. Built as a portfolio demonstration of SQL, financial controls, analytics and internal tooling.
**Live demo:** [Explore the FinOps dashboard](https://finops-operations-control-tower-pvgheewzqdrus5eappj2msr.streamlit.app)

> **Quick review:** run the app, open **Operations queue**, then inspect Globex (declining demand), Umbrella (missing invoice), and Stark (low coverage with fully utilized commitment). All customer and billing data is invented. This project is independent of Frust and does not reproduce its product or customer contracts.

## The operations question

If a portfolio saves money through cloud commitments, which accounts need attention today? A useful answer must connect usage and commitment metrics to billing exceptions, explain the size of each issue, and retain a path back to source data. A dashboard of total spend alone does not answer that question.

### Demonstrated findings from the seeded sample

| Customer | Signal | Operational decision |
|---|---|---|
| Globex | Eligible usage fell **42.1%** in the last seven days; utilization reached **67.7%**, with **$3,905** unused commitment in that window. | Investigate the drop before extending or increasing commitments. |
| Umbrella | Simulated period fee of **$1,958.40** has **no invoice**. | Trace the missing billing export before closing the period. |
| Stark | Coverage is **36.2%** while commitment utilization is **100%**. | Evaluate stable uncovered usage; do not assume a new commitment is automatically warranted. |
| Acme / Globex | Invoices differ from expected fees by **+$120 / −$175** in the invoiced amount. | Reconcile line items and inspect payment status separately. |

These examples are seeded to demonstrate detection. USD context in the queue represents different concepts (unbilled fee, mismatch, unused commitment, uncovered usage) and must **not** be summed into a single financial exposure.

## Run in under five minutes

Python 3.12 is recommended.

```bash
git clone <your-repository-url>
cd finops-operations-control-tower
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m src.seed
streamlit run app.py
```

Open the local URL shown by Streamlit. You can also start the app before seeding and select **Generate demo data**. `python -m src.seed` resets the demo tables and writes `data/synthetic_usage.parquet` plus `data/commitments.csv` deterministically; there are no AWS credentials, external APIs or paid services.

**PostgreSQL option:** launch a local database with `docker compose up -d db`, then set `DATABASE_URL=postgresql+psycopg://finops:finops@localhost:5432/finops` before running the seed and app. SQLite is the default for a frictionless review; the same SQL metric layer runs against PostgreSQL. Docker is optional.

Run the business rule checks with `pip install -r requirements-dev.txt && python -m pytest -q`. GitHub Actions runs the same checks on each push and pull request.

## Architecture

```mermaid
flowchart TD
    A["Synthetic hourly usage"] --> B["Relational tables"]
    C["Synthetic commitments"] --> B
    B --> D["SQL metrics views"]
    D --> E["Risk and review queue"]
    D --> F["Fee expectation"]
    G["Simulated invoices"] --> H["Reconciliation"]
    F --> H
    E --> I["Streamlit console"]
    H --> I
```

| Layer | Where to look | What it proves |
|---|---|---|
| Synthetic source | `src/seed.py`, `data/` | Repeatable scenarios; hourly usage; Parquet sample export. |
| Relational model | `sql/00_schema.sql` | Customer, service usage, hourly commitment and invoice keys. |
| Metric engine | `sql/01_hourly_metrics.sql`, `sql/02_portfolio_metrics.sql` | Per-hour allocation and weighted portfolio KPIs in inspectable SQL. |
| Controls | `sql/03_reconciliation.sql` through `05_data_quality.sql` | Missing invoice, signed variance, consumption shift and source checks. |
| Decision layer | `src/operations.py`, `app.py` | Prioritized action with a specific review step. |

## Calculation contract

This is a **simplified Savings Plans illustration**, not an AWS bill reconstruction:

1. The dataset has one discounted dollar commitment per customer and hour, with a fixed illustrative 30% rate reduction. EC2 and RDS usage is eligible; S3 is ineligible *in this sample*.
2. **Covered On-Demand equivalent** = `min(eligible On-Demand usage, purchased commitment / (1 − discount rate))`.
3. **Coverage** = `sum(covered On-Demand equivalent) / sum(eligible On-Demand usage)`; **utilization** = `sum(applied discounted commitment) / sum(purchased commitment)`. Aggregate ratios are weighted, never averages of customer percentages.
4. **Modeled AWS cost** = `On-Demand baseline − covered On-Demand equivalent + purchased commitment`, including unused commitment. **Net savings** = `baseline − modeled cost`; these can be negative.
5. **Expected fee** = `20% × max(customer net savings, 0)` solely as a configurable illustrative rule in `src/seed.py`. It is **not a claim about Frust's actual fees**. Missing invoices and invoice variances are different states. The invoice tag `2026-08` represents a **simulated close for August 1–14**, not a full monthly billing cycle.

The review thresholds are intentionally simple: recent utilization below 90% flags risk; coverage below 60% alongside utilization above 95% flags an opportunity to assess. They are review triggers, not purchase recommendations.

AWS describes Savings Plans coverage using On-Demand equivalent eligible usage, and its utilization report compares committed spend and applied benefits. Its [CUR 2.0 documentation](https://docs.aws.amazon.com/cur/latest/userguide/table-dictionary-cur2.html) explains the richer real export structure. This dataset uses a small conceptual subset rather than claiming schema parity. References: [AWS coverage](https://docs.aws.amazon.com/savingsplans/latest/userguide/ce-sp-cr-metrics.html), [AWS utilization](https://docs.aws.amazon.com/savingsplans/latest/userguide/ce-sp-pr-metrics.html). Frust's [public technical annex](https://www.frust.co/terms/technical-annex) describes hourly Parquet CUR exports; the Parquet file here is synthetic and local.

## Data controls and limitations

- Source checks detect missing commitment hours, invalid usage amounts and invalid discounts. Composite database keys reject duplicate hourly entries and invoices.
- A real CUR contains distinct Savings Plans/RI line types, credits, refunds, taxes, negotiated rates, account sharing and amortization. This MVP models none of those. It does not ingest AWS CUR, call AWS APIs, reconcile against actual AWS Marketplace, or implement an allocation algorithm for overlapping commitments.
- Monetary values in the demo are stored as decimal SQL columns but generated from rounded floating-point sample data. The tests use cent-level tolerance. A production financial pipeline would use decimal arithmetic end to end and audited invoice source mapping.
- Re-running the seed **resets demo tables**. Point `DATABASE_URL` to a disposable database, especially when using PostgreSQL.

## Next sensible iteration

Introduce an actual CUR 2.0 mapping with an explicit reconciliation bridge to billing exports, then add account-level permissions and an exception lifecycle (owner, due date, evidence, resolved state). Those changes should precede forecasting or an LLM assistant: the operational numbers and audit trail need to be trustworthy first.
