"""
Guard-SLM Enterprise AI Security Command Center.

Real-time Streamlit dashboard visualizing proxy telemetry:
- Live scan metrics (Total scans, Blocks, Average latency, Current RPS)
- Threat vs Safe distribution donut chart
- Live activity feed showing Base64/Leetspeak payload normalization in action
"""

import sqlite3
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_PATH = Path("data/telemetry.db")

st.set_page_config(
    page_title="Guard-SLM Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #E2E8F0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_telemetry_data() -> pd.DataFrame:
    """Reads telemetry events from the SQLite database."""
    if not DB_PATH.exists():
        return pd.DataFrame(
            columns=[
                "id",
                "timestamp",
                "original_prompt",
                "normalized_prompt",
                "decision",
                "threat_type",
                "confidence",
                "latency_ms",
            ]
        )
    try:
        conn = sqlite3.connect(str(DB_PATH))
        df = pd.read_sql_query(
            "SELECT * FROM scans ORDER BY id DESC",
            conn,
        )
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error loading telemetry database: {e}")
        return pd.DataFrame()


# Top Header
st.markdown('<div class="main-header">🛡️ Guard-SLM: Enterprise AI Security Command Center</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Real-time edge proxy telemetry, attack unmasking, and sub-20ms SLA tracking</div>', unsafe_allow_html=True)

# Controls & Refresh bar
col_refresh, col_timestamp = st.columns([1, 4])
with col_refresh:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()
with col_timestamp:
    st.caption(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")

df = load_telemetry_data()

# ----------------- Top Row: Metric Cards -----------------
total_scans = len(df)
total_blocked = (df["decision"] == "BLOCK").sum() if not df.empty else 0
block_rate = (total_blocked / total_scans * 100) if total_scans > 0 else 0.0
avg_latency = df["latency_ms"].mean() if not df.empty else 0.0

# Calculate RPS over the last 60 seconds
if not df.empty and "timestamp" in df.columns:
    df["dt"] = pd.to_datetime(df["timestamp"])
    now_utc = pd.Timestamp.now(tz="UTC")
    # If dt has no timezone, assume UTC
    if df["dt"].dt.tz is None:
        recent_cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(seconds=60)
        recent_scans = (df["dt"] >= recent_cutoff).sum()
    else:
        recent_cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(seconds=60)
        recent_scans = (df["dt"] >= recent_cutoff).sum()
    current_rps = round(recent_scans / 60.0, 2)
else:
    current_rps = 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Scans", f"{total_scans:,}")
col2.metric("Threats Blocked", f"{total_blocked:,}", f"{block_rate:.1f}% block rate")
col3.metric("Avg Latency", f"{avg_latency:.2f} ms")
col4.metric("Live RPS (60s)", f"{current_rps} req/s")

st.divider()

# ----------------- Middle Row: Visual Analytics -----------------
col_chart1, col_chart2 = st.columns([1, 1])

with col_chart1:
    st.subheader("Decision Distribution")
    if not df.empty:
        decision_counts = df["decision"].value_counts().reset_index()
        decision_counts.columns = ["Decision", "Count"]

        color_map = {"FORWARD": "#10B981", "BLOCK": "#EF4444"}
        fig_donut = px.pie(
            decision_counts,
            values="Count",
            names="Decision",
            hole=0.6,
            color="Decision",
            color_discrete_map=color_map,
        )
        fig_donut.update_traces(textinfo="percent+label", hoverinfo="value")
        fig_donut.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300)
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.info("No scan records available yet.")

with col_chart2:
    st.subheader("Latency Distribution (ms)")
    if not df.empty:
        fig_hist = px.histogram(
            df,
            x="latency_ms",
            nbins=30,
            color="decision",
            color_discrete_map={"FORWARD": "#10B981", "BLOCK": "#EF4444"},
            labels={"latency_ms": "Latency (ms)", "count": "Requests"},
        )
        fig_hist.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            height=300,
            xaxis_title="Latency (ms)",
            yaxis_title="Count",
        )
        st.plotly_chart(fig_hist, use_container_width=True)
    else:
        st.info("No latency records available yet.")

st.divider()

# ----------------- Bottom Row: Live Feed & Normalization Unmasking -----------------
st.subheader("Live Security Events & Normalization Feed (Last 50 Scans)")
st.caption(
    "Observe raw input compared against the normalized payload to verify zero-width and Base64 defense unmasking."
)

if not df.empty:
    display_cols = [
        "id",
        "timestamp",
        "original_prompt",
        "normalized_prompt",
        "decision",
        "confidence",
        "latency_ms",
    ]
    st.dataframe(
        df[display_cols].head(50),
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "timestamp": st.column_config.DatetimeColumn("Timestamp", width="medium"),
            "original_prompt": st.column_config.TextColumn("Raw Payload", width="large"),
            "normalized_prompt": st.column_config.TextColumn("Normalized (Unmasked)", width="large"),
            "decision": st.column_config.TextColumn("Action", width="small"),
            "confidence": st.column_config.NumberColumn("Confidence", format="%.4f"),
            "latency_ms": st.column_config.NumberColumn("Latency (ms)", format="%.2f"),
        },
    )
else:
    st.info("Waiting for incoming requests through the Guard-SLM proxy...")
