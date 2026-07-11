import os
import streamlit as st
import pandas as pd
import plotly.express as px
from databricks import sql
from databricks.sdk.core import Config

st.set_page_config(page_title="Fraud Detection Dashboard", layout="wide")
st.title("E-Commerce Fraud Detection — Gold Layer Dashboard")

cfg = Config()
WAREHOUSE_ID = os.environ["WAREHOUSE_ID"]

def run_query(query: str) -> pd.DataFrame:
    with sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
        credentials_provider=lambda: cfg.authenticate
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall_arrow().to_pandas()

# ---- Summary metrics row ----
summary_df = run_query("""
    SELECT COUNT(*) as total_tx, SUM(is_fraudulent) as fraud_tx,
           ROUND(SUM(is_fraudulent) / COUNT(*) * 100, 2) as fraud_rate_pct,
           ROUND(SUM(transaction_amount_usd), 0) as total_volume_usd
    FROM fraud_detection.gold.transactions_risk_scored
""")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Transactions", f"{summary_df['total_tx'][0]:,}")
c2.metric("Flagged Fraudulent", f"{summary_df['fraud_tx'][0]:,}")
c3.metric("Overall Fraud Rate", f"{summary_df['fraud_rate_pct'][0]}%")
c4.metric("Total Volume (USD)", f"${summary_df['total_volume_usd'][0]:,.0f}")

st.divider()

# ---- Risk tier breakdown ----
st.header("Risk Tier Breakdown")
risk_tier_df = run_query("""
    SELECT risk_tier, COUNT(*) as total_transactions,
           SUM(is_fraudulent) as fraud_count,
           ROUND(SUM(is_fraudulent) / COUNT(*) * 100, 2) as fraud_rate_pct
    FROM fraud_detection.gold.transactions_risk_scored
    GROUP BY risk_tier
    ORDER BY fraud_rate_pct DESC
""")
col1, col2 = st.columns([1, 1])
col1.dataframe(risk_tier_df, use_container_width=True)
fig_tier = px.bar(risk_tier_df, x="risk_tier", y="fraud_rate_pct",
                   title="Fraud Rate by Risk Tier", text="fraud_rate_pct")
col2.plotly_chart(fig_tier, use_container_width=True)

st.divider()

# ---- Daily fraud trend ----
st.header("Daily Fraud Trend")
daily_df = run_query("""
    SELECT tx_date, total_transactions, fraud_count, fraud_rate_pct, total_volume_usd
    FROM fraud_detection.gold.daily_fraud_summary
    ORDER BY tx_date
""")
fig_daily = px.line(daily_df, x="tx_date", y="fraud_rate_pct",
                     title="Daily Fraud Rate (%) — Jan-Apr 2024")
st.plotly_chart(fig_daily, use_container_width=True)

st.divider()

# ---- Category and country breakdowns, side by side ----
st.header("Fraud Rate by Category and Country")
st.caption("Note: statistical testing found neither dimension shows a meaningful fraud signal in this dataset — shown here for completeness and transparency, not as validated risk indicators.")

col3, col4 = st.columns(2)

category_df = run_query("""
    SELECT product_category, total_transactions, fraud_count, fraud_rate_pct
    FROM fraud_detection.gold.category_fraud_rates
    ORDER BY fraud_rate_pct DESC
""")
col3.subheader("By Category")
col3.dataframe(category_df, use_container_width=True)

country_df = run_query("""
    SELECT country_name, total_transactions, fraud_rate_pct
    FROM fraud_detection.gold.country_risk_profile
    ORDER BY fraud_rate_pct DESC
    LIMIT 15
""")
col4.subheader("By Country (Top 15, min. 100 transactions)")
col4.dataframe(country_df, use_container_width=True)