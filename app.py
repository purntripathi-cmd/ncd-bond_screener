import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import os
from datetime import datetime
from data_loaders import load_sample_csv, compute_derived_metrics, BENCHMARK_10Y_GSEC_YIELD

# Page Setup
st.set_page_config(
    page_title="India NCD, G-Sec & Corporate Bond Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Institutional Dark/Clean Styling Fixes
st.markdown("""
    <style>
    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 1.2rem !important;
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
    }
    div[data-testid="stMetric"] {
        background-color: rgba(30, 41, 59, 0.4);
        border-radius: 6px;
        padding: 5px 12px !important;
        border: 1px solid rgba(51, 65, 85, 0.6);
    }
    div[data-testid="stMetricLabel"] > p {
        font-size: 0.72rem !important;
        margin-bottom: 0px !important;
    }
    div[data-testid="stMetricValue"] > div {
        font-size: 1.15rem !important;
        font-weight: 700 !important;
    }
    div[data-testid="stDataFrame"] {
        font-size: 0.80rem !important;
    }
    </style>
""", unsafe_allow_html=True)

CSV_FILE_PATH = "data/sample_bonds.csv"

# 1. Load Data
@st.cache_data(ttl=600)
def get_bond_data():
    if not os.path.exists(CSV_FILE_PATH):
        st.error(f"Dataset not found at `{CSV_FILE_PATH}`.")
        st.stop()
    return load_sample_csv(CSV_FILE_PATH)

# Top Bar Header & Refresh
header_col1, header_col2 = st.columns([4, 1.5])
with header_col1:
    st.title("🇮🇳 Listed NCD, G-Sec & Corporate Bond Screener")
    last_sync_time = st.session_state.get("bond_last_sync", datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    st.caption(f"Institutional fixed income analytics calibrated against 10Y Indian Sovereign Benchmark ({BENCHMARK_10Y_GSEC_YIELD:.2f}%) • 🕒 Last Refreshed: {last_sync_time}")
with header_col2:
    st.write("")
    if st.button("🔄 Refresh Quotes & Data", use_container_width=True, help="Flush caches and reload latest quotes and metadata"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.session_state["bond_last_sync"] = datetime.now().strftime("%d-%b-%Y %H:%M:%S")
        st.toast("Quotes and Bond Screener data refreshed!", icon="✅")
        st.rerun()

raw_data = get_bond_data()

# 2. Add Govt/PSU Flag (without artificial jitter)
def enrich_entity_metadata(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    psu_keywords = ["sidbi", "rec", "pfc", "nabard", "nhai", "irfc", "ntpc", "sbi", "government of india", "goi", "g-sec", "gilt", "power grid"]
    
    def detect_govt_psu(row):
        name = str(row.get("issuer_name", "")).lower()
        sector = str(row.get("sector", "")).lower()
        tax = str(row.get("tax_status", "")).lower()
        rating = str(row.get("rating_current", "")).upper()
        if any(k in name for k in psu_keywords) or "54ec" in tax or "psu" in sector or "sovereign" in rating or "g-sec" in sector:
            return "Yes"
        return "No"
    
    data["is_govt_psu"] = data.apply(detect_govt_psu, axis=1)
    return data

raw_data = enrich_entity_metadata(raw_data)

# App Navigation Tabs
tab_screener, tab_yield_curve, tab_stress_test, tab_manage = st.tabs([
    "📊 Bond Screener & Analytics", 
    "📈 Yield Curve & Spread Matrix",
    "⚡ RBI Rate Shock Stress-Tester",
    "🔎 Raw Data & Management"
])

# Sidebar Filters
st.sidebar.title("🔍 Screener Filters")
tax_slab = st.sidebar.number_input("Your Tax Slab (%)", min_value=0.0, max_value=45.0, value=30.0, step=1.0)
target_yield = st.sidebar.number_input("Target Post-Tax Yield (%)", min_value=0.0, max_value=25.0, value=6.0, step=0.25)

data = compute_derived_metrics(raw_data, user_tax_rate=tax_slab)

# Multi-Factor Weighted Buy Score (0 - 100)
def calculate_buy_score(row) -> float:
    score = 0.0
    post_tax = row.get("post_tax_yield", 0.0)
    score += min(30.0, max(0.0, (post_tax / 8.0) * 30.0))

    rating = str(row.get("rating_current", "")).upper()
    if "SOVEREIGN" in rating:
        score += 25.0
    elif "AAA" in rating:
        score += 23.0
    elif "AA+" in rating:
        score += 19.0
    elif "AA" in rating:
        score += 16.0
    elif "A+" in rating:
        score += 10.0
    elif "A" in rating:
        score += 7.0
    else:
        score += 2.0
        
    sec = str(row.get("secured_unsecured", "")).capitalize()
    score += 15.0 if ("Secured" in sec or "Sovereign" in sec) else 5.0
    score += 15.0 if row.get("is_govt_psu") == "Yes" else 5.0
        
    liq = row.get("liquidity_flag", "Low")
    if liq == "High":
        score += 10.0
    elif liq == "Medium":
        score += 6.0
    else:
        score += 2.0
        
    tenor = row.get("remaining_tenor_years", 1.0)
    if 1.0 <= tenor <= 5.0:
        score += 5.0
    elif 5.0 < tenor <= 10.0:
        score += 4.0
    else:
        score += 2.0

    return round(score, 1)

data["buy_score"] = data.apply(calculate_buy_score, axis=1)

st.sidebar.markdown("---")
search_query = st.sidebar.text_input("Search Ticker, ISIN, or Issuer", "", help="Search by NSE/BSE bond ticker symbol, ISIN, or company name")
sectors = st.sidebar.multiselect("Sector", options=sorted(data['sector'].dropna().unique()))
sec_filter = st.sidebar.multiselect("Security Type", options=sorted(data['secured_unsecured'].dropna().unique()) if 'secured_unsecured' in data.columns else [])
pay_freq = st.sidebar.multiselect("Payout Frequency", options=sorted(data['payment_frequency'].dropna().unique()) if 'payment_frequency' in data.columns else [])
exchanges = st.sidebar.multiselect("Exchange", options=sorted(data['exchange'].dropna().unique()))
rating_current = st.sidebar.multiselect("Rating", options=sorted(data['rating_current'].dropna().unique()))
psu_filter = st.sidebar.multiselect("Govt / PSU Entity", options=["Yes", "No"])
tax_status = st.sidebar.multiselect("Tax Status", options=sorted(data['tax_status'].dropna().unique()))

st.sidebar.markdown("---")
min_ytm = float(data['current_yield_ytm'].min())
max_ytm = float(data['current_yield_ytm'].max())
ytm_range = st.sidebar.slider("Current YTM (%)", min_ytm, max_ytm, (min_ytm, max_ytm), step=0.1)

max_tenor = float(data['remaining_tenor_years'].max())
tenor_range = st.sidebar.slider("Tenor (Years)", 0.0, max_tenor, (0.0, max_tenor), step=0.5)

# Filter Application
filtered = data.copy()
if search_query:
    q = search_query.lower()
    t_match = filtered["ticker"].astype(str).str.lower().str.contains(q) if "ticker" in filtered.columns else False
    i_match = filtered["issuer_name"].astype(str).str.lower().str.contains(q)
    isin_match = filtered["isin"].astype(str).str.lower().str.contains(q)
    filtered = filtered[t_match | i_match | isin_match]
if sectors:
    filtered = filtered[filtered['sector'].isin(sectors)]
if sec_filter:
    filtered = filtered[filtered['secured_unsecured'].isin(sec_filter)]
if pay_freq:
    filtered = filtered[filtered['payment_frequency'].isin(pay_freq)]
if exchanges:
    filtered = filtered[filtered['exchange'].isin(exchanges)]
if rating_current:
    filtered = filtered[filtered['rating_current'].isin(rating_current)]
if psu_filter:
    filtered = filtered[filtered['is_govt_psu'].isin(psu_filter)]
if tax_status:
    filtered = filtered[filtered['tax_status'].isin(tax_status)]

filtered = filtered[(filtered['current_yield_ytm'] >= ytm_range[0]) & (filtered['current_yield_ytm'] <= ytm_range[1])]
filtered = filtered[(filtered['remaining_tenor_years'] >= tenor_range[0]) & (filtered['remaining_tenor_years'] <= tenor_range[1])]

with tab_screener:
    # Summary Metrics
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Screened Bonds", f"{len(filtered)} / {len(data)}")
    m2.metric("Avg YTM", f"{round(filtered['current_yield_ytm'].mean(), 2)}%" if not filtered.empty else "0%")
    m3.metric("Avg Post-Tax Yield", f"{round(filtered['post_tax_yield'].mean(), 2)}%" if not filtered.empty else "0%")
    m4.metric("Avg G-Sec Spread", f"{int(filtered['credit_spread_bps'].mean()):+d} bps" if not filtered.empty else "0 bps")
    m5.metric("Avg Mod Duration", f"{round(filtered['modified_duration'].mean(), 2)} yrs" if not filtered.empty else "0")
    top_score_bond = filtered.sort_values(by='buy_score', ascending=False).iloc[0]['issuer_name'][:18] + ".." if not filtered.empty else "-"
    m6.metric("Top Buy Score", top_score_bond)

    st.markdown("---")

    display_cols = [
        "ticker", "issuer_name", "isin", "issue_date", "maturity_date",
        "payment_frequency", "secured_unsecured", "rating_current", "coupon_rate", 
        "current_yield_ytm", "credit_spread_bps", "post_tax_yield", "remaining_tenor_years", 
        "modified_duration", "convexity", "tax_status", "is_govt_psu", "liquidity_flag", "buy_score"
    ]
    display_cols = [c for c in display_cols if c in filtered.columns]

    st.dataframe(
        filtered[display_cols].sort_values(by="buy_score", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", help="NSE/BSE Trading Symbol for quick terminal search", width="small"),
            "issuer_name": st.column_config.TextColumn("Bond Title / Issue Name", width="large"),
            "isin": st.column_config.TextColumn("ISIN", width="small"),
            "issue_date": st.column_config.TextColumn("Issue Date", width="small"),
            "maturity_date": st.column_config.TextColumn("Maturity Date", width="small"),
            "payment_frequency": st.column_config.TextColumn("Payout Freq", help="Interest Payout Schedule (Annual, Semi-Annual, Monthly)", width="small"),
            "secured_unsecured": st.column_config.TextColumn("Security Type", help="Charge on assets (Secured, Unsecured, Sovereign Guarantee)", width="small"),
            "rating_current": st.column_config.TextColumn("Rating", width="small"),
            "coupon_rate": st.column_config.NumberColumn("Coupon (%)", format="%.2f%%"),
            "current_yield_ytm": st.column_config.NumberColumn("Pre-Tax YTM (%)", format="%.2f%%"),
            "credit_spread_bps": st.column_config.NumberColumn("Spread (bps)", help="Yield spread over 10Y Sovereign G-Sec (6.82%)"),
            "post_tax_yield": st.column_config.NumberColumn("Post-Tax Yield", format="%.2f%%", help="Yield realized after deducting user tax slab"),
            "remaining_tenor_years": st.column_config.NumberColumn("Tenor (Yrs)", format="%.1f"),
            "modified_duration": st.column_config.NumberColumn("Mod Dur (Yrs)", format="%.2f"),
            "convexity": st.column_config.NumberColumn("Convexity", format="%.2f"),
            "tax_status": st.column_config.TextColumn("Tax Status"),
            "is_govt_psu": st.column_config.TextColumn("Govt/PSU"),
            "liquidity_flag": st.column_config.TextColumn("Liquidity"),
            "buy_score": st.column_config.NumberColumn("Buy Score (100)", format="%.1f")
        }
    )

    st.download_button(
        "📥 Export Screened Bonds (CSV)",
        data=filtered[display_cols].to_csv(index=False).encode('utf-8'),
        file_name="bonds_screener_output.csv",
        mime="text/csv"
    )

with tab_yield_curve:
    st.subheader("📈 India Fixed-Income Yield Curve & Credit Spread Matrix")
    c_y1, c_y2 = st.columns([3, 2])

    with c_y1:
        fig_curve = px.scatter(
            filtered,
            x="remaining_tenor_years",
            y="current_yield_ytm",
            color="risk_bucket",
            size="buy_score",
            hover_name="issuer_name",
            labels={"remaining_tenor_years": "Tenor to Maturity (Years)", "current_yield_ytm": "Yield to Maturity (%)"},
            title="Yield vs Maturity Curve by Risk Bucket"
        )
        fig_curve.add_hline(y=BENCHMARK_10Y_GSEC_YIELD, line_dash="dash", line_color="orange", annotation_text="10Y G-Sec (6.82%)")
        fig_curve.update_layout(height=420, margin=dict(l=10, r=10, t=35, b=10))
        st.plotly_chart(fig_curve, use_container_width=True)

    with c_y2:
        spread_by_sector = filtered.groupby("sector")["credit_spread_bps"].mean().reset_index().sort_values(by="credit_spread_bps")
        fig_bar = px.bar(
            spread_by_sector,
            x="credit_spread_bps",
            y="sector",
            orientation="h",
            color="credit_spread_bps",
            color_continuous_scale="Viridis",
            title="Average Credit Spread over G-Sec by Sector (bps)"
        )
        fig_bar.update_layout(height=420, margin=dict(l=10, r=10, t=35, b=10))
        st.plotly_chart(fig_bar, use_container_width=True)

with tab_stress_test:
    st.subheader("⚡ RBI Policy Rate Shock Simulator (Duration & Convexity Engine)")
    st.caption("Evaluates bond capital appreciation or depreciation under monetary policy shifts using Taylor-expansion duration/convexity approximation:")
    st.latex(r"\Delta P \approx -D_{\text{mod}} \cdot \Delta y + \frac{1}{2} C \cdot (\Delta y)^2")

    shock_bps = st.slider("Simulated RBI Repo Rate Change (bps)", -200, 200, -50, 25, help="Negative = Rate Cuts (Bond Prices Rise); Positive = Rate Hikes (Bond Prices Drop)")
    shock_y = shock_bps / 10000.0

    stress_df = filtered.copy()
    stress_df["price_change_pct"] = (
        -stress_df["modified_duration"] * (shock_y * 100) + 0.5 * stress_df["convexity"] * ((shock_y * 100) ** 2)
    ).round(2)
    stress_df["new_ytm"] = (stress_df["current_yield_ytm"] + (shock_bps / 100.0)).round(2)

    st_col1, st_col2 = st.columns([3, 2])
    with st_col1:
        fig_stress = px.bar(
            stress_df.sort_values(by="price_change_pct", ascending=False).head(15),
            x="price_change_pct",
            y="issuer_name",
            orientation="h",
            color="price_change_pct",
            color_continuous_scale="RdYlGn",
            title=f"Capital Gain / Loss (%) under a {shock_bps:+d} bps Rate Shift"
        )
        fig_stress.update_layout(height=420, margin=dict(l=10, r=10, t=35, b=10))
        st.plotly_chart(fig_stress, use_container_width=True)

    with st_col2:
        stress_cols = ["ticker", "issuer_name", "remaining_tenor_years", "modified_duration", "price_change_pct", "new_ytm"]
        stress_cols = [c for c in stress_cols if c in stress_df.columns]
        st.dataframe(
            stress_df[stress_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "ticker": st.column_config.TextColumn("Ticker"),
                "issuer_name": st.column_config.TextColumn("Bond"),
                "remaining_tenor_years": st.column_config.NumberColumn("Tenor (Yrs)", format="%.1f"),
                "modified_duration": st.column_config.NumberColumn("Mod Dur", format="%.2f"),
                "price_change_pct": st.column_config.NumberColumn("Est Capital Chg (%)", format="%+.2f%%"),
                "new_ytm": st.column_config.NumberColumn("New YTM (%)", format="%.2f%%")
            }
        )

with tab_manage:
    st.subheader("📂 Active Bond Master Database")
    st.dataframe(raw_data, use_container_width=True)
