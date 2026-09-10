import streamlit as st
import plotly.express as px
import pandas as pd
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

# 1. Load Data
@st.cache_data(ttl=600)
def get_bond_data():
    return load_sample_csv()

raw_data = get_bond_data()

# 2. Sidebar Filters & Slicers
st.sidebar.title("🔍 Screener Filters")

# User Session State & Sliders
tax_slab = st.sidebar.number_input("Your Tax Slab (%)", min_value=0.0, max_value=45.0, value=30.0, step=1.0)
target_yield = st.sidebar.number_input("Target Post-Tax Yield (%)", min_value=0.0, max_value=25.0, value=7.0, step=0.25)

# Calculate dynamic fields
data = compute_derived_metrics(raw_data, user_tax_rate=tax_slab)

st.sidebar.markdown("---")
# Categorical Filters
search_query = st.sidebar.text_input("Search Issuer or ISIN", "")

sectors = st.sidebar.multiselect("Sector", options=sorted(data['sector'].dropna().unique()))
exchanges = st.sidebar.multiselect("Exchange", options=sorted(data['exchange'].dropna().unique()))
rating_current = st.sidebar.multiselect("Rating", options=sorted(data['rating_current'].dropna().unique()))
seniority = st.sidebar.multiselect("Seniority", options=sorted(data['seniority'].dropna().unique()))
secured_options = st.sidebar.multiselect("Collateral", options=sorted(data['secured_unsecured'].dropna().unique()))
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
if liquidity_levels:
    filtered = filtered[filtered['liquidity_flag'].isin(liquidity_levels)]
if tax_status:
    filtered = filtered[filtered['tax_status'].isin(tax_status)]

filtered = filtered[
    (filtered['current_yield_ytm'] >= ytm_range[0]) & (filtered['current_yield_ytm'] <= ytm_range[1]) &
    (filtered['remaining_tenor_years'] >= tenor_range[0]) & (filtered['remaining_tenor_years'] <= tenor_range[1])
]

# 3. Main Dashboard Header & KPI Metrics
st.title("🇮🇳 Listed NCD & Corporate Bond Screener")
st.caption("Live screener for secondary market corporate bonds & NCDs traded on NSE/BSE")

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

# 4. Interactive Visualizations
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
            hover_data=["isin", "post_tax_yield", "liquidity_flag"],
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

# 5. Screener Table & Details
st.subheader("📋 Filtered Bond Master")

display_columns = [
    "isin", "issuer_name", "rating_current", "secured_unsecured",
    "coupon_rate", "current_yield_ytm", "post_tax_yield",
    "remaining_tenor_years", "last_traded_price", "liquidity_flag",
    "daily_value_inr_cr", "tax_status"
]

format_dict = {
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

styled_df = (
    filtered[display_columns]
    .style
    .apply(highlight_target_yield, axis=1)
    .format(format_dict)
)

st.dataframe(styled_df, use_container_width=True, height=350)

# Export Data Button
csv_bytes = filtered.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Download Screener Results as CSV",
    data=csv_bytes,
    file_name="ncd_screener_export.csv",
    mime="text/csv"
)
