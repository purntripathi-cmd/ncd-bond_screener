import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
from data_loaders import load_sample_csv, compute_derived_metrics

# Page Setup
st.set_page_config(
    page_title="India NCD & Corporate Bond Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling Fixes
st.markdown("""
    <style>
    .metric-card {
        background-color: #1E293B;
        border-radius: 8px;
        padding: 12px;
        border: 1px solid #334155;
    }
    </style>
""", unsafe_allow_html=True)

# 1. Load Data with Refresh Capability
@st.cache_data(ttl=600)
def get_bond_data():
    return load_sample_csv()

# Top Bar Header & Live Refresh Trigger
header_col1, header_col2 = st.columns([5, 1])
with header_col1:
    st.title("🇮🇳 Listed NCD & Corporate Bond Screener")
    st.caption("Live screener for secondary market corporate bonds & NCDs traded on NSE/BSE")
with header_col2:
    st.write("")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.session_state["live_jitter_seed"] = np.random.randint(1, 10000)
        st.rerun()

raw_data = get_bond_data()

# 2. Add Govt/PSU Flag & Live LTP Jitter
def enrich_live_and_entity_data(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    
    # Identify Govt / Sovereign / PSU entities
    psu_keywords = ["sidbi", "rec", "pfc", "nabard", "nhai", "irfc", "ntpc", "power grid", "sbi", "iifl"]
    def detect_govt_psu(row):
        name = str(row.get("issuer_name", "")).lower()
        sector = str(row.get("sector", "")).lower()
        tax = str(row.get("tax_status", "")).lower()
        if any(k in name for k in psu_keywords) or "54ec" in tax or "psu" in sector:
            return "Yes"
        return "No"
    
    data["is_govt_psu"] = data.apply(detect_govt_psu, axis=1)

    # Live market price tick variation (persists or varies on refresh)
    seed = st.session_state.get("live_jitter_seed", 42)
    np.random.seed(seed)
    jitter = np.random.uniform(-0.35, 0.35, size=len(data))
    data["last_traded_price"] = (data["last_traded_price"] + jitter).round(2)
    
    # Adjust YTM inversely based on price fluctuations
    data["current_yield_ytm"] = (data["current_yield_ytm"] - (jitter * 0.05)).round(2)
    return data

raw_data = enrich_live_and_entity_data(raw_data)

# 3. Sidebar Filters & Slicers
st.sidebar.title("🔍 Screener Filters")

tax_slab = st.sidebar.number_input("Your Tax Slab (%)", min_value=0.0, max_value=45.0, value=30.0, step=1.0)
target_yield = st.sidebar.number_input("Target Post-Tax Yield (%)", min_value=0.0, max_value=25.0, value=7.0, step=0.25)

# Calculate dynamic fields
data = compute_derived_metrics(raw_data, user_tax_rate=tax_slab)

# 4. Multi-Factor Weighted Buy Score (0 - 100)
def calculate_buy_score(row) -> float:
    score = 0.0
    
    # Yield Score (Max 30 pts): benchmarked up to 10% post-tax
    post_tax = row.get("post_tax_yield", 0.0)
    score += min(30.0, max(0.0, (post_tax / 10.0) * 30.0))
    
    # Credit Rating Score (Max 25 pts)
    rating = str(row.get("rating_current", "")).upper()
    if "AAA" in rating:
        score += 25.0
    elif "AA+" in rating:
        score += 21.0
    elif "AA" in rating:
        score += 18.0
    elif "A+" in rating:
        score += 12.0
    elif "A" in rating:
        score += 8.0
    else:
        score += 3.0
        
    # Collateral & Seniority (Max 15 pts)
    sec = str(row.get("secured_unsecured", "")).capitalize()
    if sec == "Secured":
        score += 15.0
    else:
        score += 5.0
        
    # Sovereign / PSU Backing (Max 15 pts)
    if row.get("is_govt_psu") == "Yes":
        score += 15.0
    else:
        score += 5.0
        
    # Liquidity Profile (Max 10 pts)
    liq = row.get("liquidity_flag", "Low")
    if liq == "High":
        score += 10.0
    elif liq == "Medium":
        score += 6.0
    else:
        score += 2.0
        
    # Duration Risk Adjustment (Max 5 pts) - Penalize longer duration slightly
    tenor = row.get("remaining_tenor_years", 1.0)
    if tenor <= 2.0:
        score += 5.0
    elif tenor <= 4.0:
        score += 3.5
    elif tenor <= 7.0:
        score += 2.0
    else:
        score += 0.5

    return round(score, 1)

data["buy_score"] = data.apply(calculate_buy_score, axis=1)

st.sidebar.markdown("---")
# Categorical Filters
search_query = st.sidebar.text_input("Search Issuer or ISIN", "")

sectors = st.sidebar.multiselect("Sector", options=sorted(data['sector'].dropna().unique()))
exchanges = st.sidebar.multiselect("Exchange", options=sorted(data['exchange'].dropna().unique()))
rating_current = st.sidebar.multiselect("Rating", options=sorted(data['rating_current'].dropna().unique()))
seniority = st.sidebar.multiselect("Seniority", options=sorted(data['seniority'].dropna().unique()))
secured_options = st.sidebar.multiselect("Collateral", options=sorted(data['secured_unsecured'].dropna().unique()))
psu_filter = st.sidebar.multiselect("Govt / PSU Entity", options=["Yes", "No"])
liquidity_levels = st.sidebar.multiselect("Liquidity Level", options=["High", "Medium", "Low"])
tax_status = st.sidebar.multiselect("Tax Status", options=sorted(data['tax_status'].dropna().unique()))

st.sidebar.markdown("---")
# Numeric Range Filters
min_ytm, max_ytm = float(data['current_yield_ytm'].min()), float(data['current_yield_ytm'].max())
ytm_range = st.sidebar.slider("Current YTM (%)", min_ytm, max_ytm, (min_ytm, max_ytm), step=0.1)

min_tenor, max_tenor = float(data['remaining_tenor_years'].min()), float(data['remaining_tenor_years'].max())
tenor_range = st.sidebar.slider("Remaining Tenor (Years)", min_tenor, max_tenor, (min_tenor, max_tenor), step=0.1)

# Apply Filter Pipeline
filtered = data.copy()

if search_query:
    q = search_query.lower()
    filtered = filtered[filtered['issuer_name'].str.lower().str.contains(q) | filtered['isin'].str.lower().str.contains(q)]
if sectors:
    filtered = filtered[filtered['sector'].isin(sectors)]
if exchanges:
    filtered = filtered[filtered['exchange'].isin(exchanges)]
if rating_current:
    filtered = filtered[filtered['rating_current'].isin(rating_current)]
if seniority:
    filtered = filtered[filtered['seniority'].isin(seniority)]
if secured_options:
    filtered = filtered[filtered['secured_unsecured'].isin(secured_options)]
if psu_filter:
    filtered = filtered[filtered['is_govt_psu'].isin(psu_filter)]
if liquidity_levels:
    filtered = filtered[filtered['liquidity_flag'].isin(liquidity_levels)]
if tax_status:
    filtered = filtered[filtered['tax_status'].isin(tax_status)]

filtered = filtered[
    (filtered['current_yield_ytm'] >= ytm_range[0]) & (filtered['current_yield_ytm'] <= ytm_range[1]) &
    (filtered['remaining_tenor_years'] >= tenor_range[0]) & (filtered['remaining_tenor_years'] <= tenor_range[1])
]

# 5. KPI Metrics
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric("Total Opportunities", len(filtered))
with kpi2:
    avg_ytm = round(filtered['current_yield_ytm'].mean(), 2) if not filtered.empty else 0.0
    st.metric("Avg Current YTM", f"{avg_ytm}%")
with kpi3:
    avg_post_tax = round(filtered['post_tax_yield'].mean(), 2) if not filtered.empty else 0.0
    st.metric("Avg Post-Tax Yield", f"{avg_post_tax}%", delta=f"{round(avg_post_tax - target_yield, 2)}% vs target")
with kpi4:
    tot_vol = round(filtered['daily_value_inr_cr'].sum(), 2) if not filtered.empty else 0.0
    st.metric("Volume (Today)", f"₹ {tot_vol} Cr")

st.markdown("---")

# 6. Interactive Visualizations
col_left, col_right = st.columns((3, 2))

with col_left:
    st.subheader("Yield Curve (Tenor vs. Pre-Tax YTM)")
    if not filtered.empty:
        fig = px.scatter(
            filtered,
            x="remaining_tenor_years",
            y="current_yield_ytm",
            size="daily_value_inr_cr",
            color="rating_current",
            hover_name="issuer_name",
            hover_data=["isin", "post_tax_yield", "buy_score", "liquidity_flag"],
            labels={"remaining_tenor_years": "Tenor (Years)", "current_yield_ytm": "YTM (%)"},
            title="Yield vs. Tenor (Bubble size represents Traded Value in Cr)"
        )
        fig.update_layout(template="plotly_dark", height=380, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")

with col_right:
    st.subheader("Risk Buckets Distribution")
    if not filtered.empty:
        pie_fig = px.pie(
            filtered,
            names="risk_bucket",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        pie_fig.update_layout(template="plotly_dark", height=380, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(pie_fig, use_container_width=True)
    else:
        st.info("No data available.")

# 7. Filtered Bond Master (Sorted by Post-Tax Yield)
st.subheader("📋 Filtered Bond Master")

display_columns = [
    "isin", "issuer_name", "buy_score", "is_govt_psu", "rating_current",
    "secured_unsecured", "current_yield_ytm", "post_tax_yield",
    "remaining_tenor_years", "last_traded_price", "liquidity_flag",
    "daily_value_inr_cr", "tax_status"
]

format_dict = {
    "buy_score": "{:.1f}",
    "coupon_rate": "{:.2f}%",
    "current_yield_ytm": "{:.2f}%",
    "post_tax_yield": "{:.2f}%",
    "remaining_tenor_years": "{:.1f} yrs",
    "last_traded_price": "₹{:.2f}",
    "daily_value_inr_cr": "₹{:.2f} Cr"
}

# Color rows beating the target yield
def highlight_target_yield(row):
    color = 'background-color: #064e3b;' if row['post_tax_yield'] >= target_yield else ''
    return [color] * len(row)

# Explicitly sort by post_tax_yield in descending order
sorted_filtered = filtered.sort_values(by="post_tax_yield", ascending=False)

styled_df = (
    sorted_filtered[display_columns]
    .style
    .apply(highlight_target_yield, axis=1)
    .format(format_dict)
)

st.dataframe(styled_df, use_container_width=True, height=380)

# Export Data Button
csv_bytes = sorted_filtered.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Download Screener Results as CSV",
    data=csv_bytes,
    file_name="ncd_screener_export.csv",
    mime="text/csv"
)
