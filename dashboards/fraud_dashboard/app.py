import os
import streamlit as st
import pandas as pd
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

st.header("Risk Tier Breakdown")
risk_tier_df = run_query("""
    SELECT risk_tier, COUNT(*) as total_transactions,
           SUM(is_fraudulent) as fraud_count,
           ROUND(SUM(is_fraudulent) / COUNT(*) * 100, 2) as fraud_rate_pct
    FROM fraud_detection.gold.transactions_risk_scored
    GROUP BY risk_tier
    ORDER BY fraud_rate_pct DESC
""")
st.dataframe(risk_tier_df)