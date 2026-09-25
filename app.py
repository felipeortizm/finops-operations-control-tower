"""Streamlit frontend for the synthetic FinOps operations demo."""
import os
import pandas as pd
import streamlit as st

from src.operations import load, make_queue
from src.seed import seed
from src.db import ROOT

st.set_page_config(page_title="FinOps Operations Control Tower", page_icon="◈", layout="wide")
st.markdown("""
<style>
  .block-container {padding-top: 1.5rem; max-width: 1380px}
  h1,h2,h3 {letter-spacing: -.035em}
  .subtle {color: #91a0b6; margin-top: -.6rem}
  .eyebrow {color: #49c8a6; font-weight: 700; font-size: .8rem; letter-spacing: .14em}
  [data-testid="stMetric"] {background: #172434; border: 1px solid #29405a;
      padding: 1rem 1.2rem; border-radius: 12px}
  [data-testid="stMetricLabel"] {color: #b7c7d8}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=30)
def data():
    return load()

if not os.environ.get("DATABASE_URL") and not (ROOT / "finops_demo.db").exists():
    seed()


st.markdown('<div class="eyebrow">PORTFOLIO OPERATIONS / DEMONSTRATION</div>', unsafe_allow_html=True)
st.title("FinOps Operations Control Tower")
st.markdown('<div class="subtle">August 1–14, 2026 · synthetic AWS-like usage · USD · illustrative commercial rules</div>',
            unsafe_allow_html=True)

try:
    portfolio, billing, risk, quality, daily = data()
except Exception as exc:
    st.info("Demo database is not initialized. Generate the synthetic sample below, or run `python -m src.seed`.")
    if st.button("Generate demo data", type="primary"):
        seed()
        data.clear()
        st.rerun()
    st.stop()

names = [p["customer_name"] for p in portfolio]
selected = st.sidebar.selectbox("Customer", ["All customers", *names])
st.sidebar.caption("Data is entirely synthetic. SQLite runs locally; PostgreSQL is supported via DATABASE_URL.")
st.sidebar.divider()
st.sidebar.caption("Coverage uses eligible On-Demand equivalent. Utilization uses applied / purchased commitment.")

visible = [p for p in portfolio if selected == "All customers" or p["customer_name"] == selected]
visible_names = {p["customer_name"] for p in visible}
visible_bills = [b for b in billing if b["customer_name"] in visible_names]
visible_risks = [r for r in risk if r["customer_name"] in visible_names]
queue = make_queue(visible, visible_bills, visible_risks, quality if selected == "All customers" else [])


def total(field):
    return sum(float(p[field]) for p in visible)


def usd(value):
    return f"${value:,.0f}"


money = st.columns(3)
money[0].metric("AWS cost / demo", usd(total("actual_cost")))
money[1].metric("Net savings", usd(total("net_savings")))
money[2].metric("Expected fee", usd(total("expected_fee")))

ratios = st.columns(2)
ratios[0].metric("Coverage", f"{total('covered_od')/total('eligible_od'):.1%}" if total("eligible_od") else "—")
ratios[1].metric("Utilization", f"{total('applied_commitment')/total('committed_spend'):.1%}" if total("committed_spend") else "—")

tab_queue, tab_portfolio, tab_billing, tab_method = st.tabs(
    ["Operations queue", "Portfolio & commitments", "Billing reconciliation", "Method & controls"]
)

with tab_queue:
    a, b, c = st.columns(3)
    a.metric("Actions to review", len(queue))
    b.metric("Billing exceptions", sum(x["reconciliation_status"] != "Matched" for x in visible_bills))
    c.metric("Recent unused commitment", usd(sum(float(r["unused"]) for r in visible_risks)))
    st.subheader("Next actions")
    if queue:
        qdf = pd.DataFrame(queue).rename(columns={"priority": "Priority", "customer": "Customer",
                                                   "issue": "Signal", "exposure": "USD context", "action": "Suggested review"})
        st.dataframe(qdf.style.format({"USD context": "${:,.0f}"}), width="stretch",
                     hide_index=True, column_config={"Priority": st.column_config.NumberColumn(help="1 = urgent; 3 = opportunity")})
    else:
        st.success("No items meet the demo's review thresholds.")
    st.caption("USD context combines different measures (billing variance, unused commitment, uncovered usage). Do not sum these values as one financial exposure.")

with tab_portfolio:
    st.subheader("Customer performance")
    pdf = pd.DataFrame(visible)
    shown = pdf[["customer_name", "baseline", "actual_cost", "net_savings", "coverage", "utilization", "unused_commitment"]]
    shown = shown.rename(columns={"customer_name": "Customer", "baseline": "On-Demand baseline",
                                  "actual_cost": "AWS cost", "net_savings": "Net savings",
                                  "coverage": "Coverage", "utilization": "Utilization",
                                  "unused_commitment": "Unused commitment"})
    st.dataframe(shown.style.format({"On-Demand baseline": "${:,.0f}", "AWS cost": "${:,.0f}",
                                     "Net savings": "${:,.0f}", "Coverage": "{:.1%}",
                                     "Utilization": "{:.1%}", "Unused commitment": "${:,.0f}"}),
                 width="stretch", hide_index=True)
    st.caption("Daily On-Demand baseline compared with modeled AWS cost for the selected scope.")
    df_daily = pd.DataFrame(daily)
    df_daily = df_daily[df_daily["customer_id"].isin({p["customer_id"] for p in visible})]
    df_daily = df_daily.groupby("day", as_index=True)[["baseline", "actual_cost"]].sum()
    st.line_chart(df_daily[["baseline", "actual_cost"]], color=["#8da4ba", "#49c8a6"])
    st.subheader("Recent commitment risk")
    rdf = pd.DataFrame(visible_risks)
    if not rdf.empty:
        rdf = rdf[["customer_name", "recent_utilization", "usage_change", "unused"]]
        rdf.columns = ["Customer", "Last 7d utilization", "Eligible usage change", "Last 7d unused USD"]
        st.dataframe(rdf.style.format({"Last 7d utilization": "{:.1%}", "Eligible usage change": "{:+.1%}",
                                       "Last 7d unused USD": "${:,.0f}"}), width="stretch", hide_index=True)

with tab_billing:
    st.subheader("Operational result → expected fee → invoice")
    st.caption("Positive variance means expected fee exceeds billed fee; missing invoices remain separate from numerical mismatches.")
    bdf = pd.DataFrame(visible_bills)
    bdf = bdf[["customer_name", "expected_fee", "invoice_id", "billed_fee", "variance",
               "reconciliation_status", "payment_status"]]
    bdf.columns = ["Customer", "Expected fee", "Invoice ID", "Billed fee", "Variance",
                   "Reconciliation", "Payment"]
    st.dataframe(bdf.style.format({"Expected fee": "${:,.2f}", "Billed fee": lambda v: "—" if pd.isna(v) else f"${v:,.2f}",
                                  "Variance": "${:,.2f}"}), width="stretch", hide_index=True)
    st.info("A paid but mismatched invoice still needs investigation; payment status and fee accuracy are separate controls.")

with tab_method:
    st.subheader("Metric definitions")
    st.markdown("""
    - **Coverage** = covered On-Demand equivalent ÷ eligible On-Demand usage.
    - **Utilization** = applied discounted commitment ÷ purchased discounted commitment.
    - **AWS cost** = total On-Demand baseline − covered On-Demand equivalent + full purchased commitment.
    - **Net savings** = On-Demand baseline − AWS cost; unused commitment can reduce savings.
    - **Expected fee** = 20% × max(net savings, 0), an illustrative assumption for this sample.
    - **Risk** = utilization below 90% in the last seven days; uncovered usage opportunity below 60% coverage and above 95% utilization.
    """)
    st.subheader("Source checks")
    st.dataframe(pd.DataFrame(quality).rename(columns={"issue": "Check", "affected_rows": "Affected rows"}),
                 width="stretch", hide_index=True)
    st.caption("This model is a simplified synthetic Savings Plans illustration, not a full AWS CUR, RI allocation engine, invoice integration or claim about Frust's internal pricing.")
