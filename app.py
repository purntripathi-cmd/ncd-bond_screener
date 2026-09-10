import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import os
from data_loaders import load_sample_csv, compute_derived_metrics

# Page Setup
st.set_page_config(
    page_title="India NCD, G-Sec & Corporate Bond Screener",
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

CSV_FILE_PATH = "data/sample_bonds.csv"

# 1. Load Data
@st.cache_data(ttl=600)
def get_bond_data():
    if not os.path.exists(CSV_FILE_PATH):
        st.error(f"Dataset not found at `{CSV_FILE_PATH}`. Please create it or upload it via the Manage Data tab.")
        st.stop()
    return load_sample_csv(CSV_FILE_PATH)

# Top Bar Header & Refresh
header_col1, header_col2 = st.columns([5, 1])
with header_col1:
    st.title("🇮🇳 Listed NCD, G-Sec & Corporate Bond Screener")
    st.caption("Live screener for secondary market corporate bonds, sovereign G-Secs, and Gilts traded on NSE/BSE")
with header_col2:
    st.write("")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.session_state["live_jitter_seed"] = np.random.randint(1, 10000)
        st.rerun()

raw_data = get_bond_data()

# 2. Add Govt/PSU Flag & Live Simulated Jitter
def enrich_live_and_entity_data(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    psu_keywords = ["sidbi", "rec", "pfc", "nabard", "nhai", "irfc", "ntpc", "sbi", "government of india", "goi", "g-sec", "gilt"]
    
    def detect_govt_psu(row):
        name = str(row.get("issuer_name", "")).lower()
        sector = str(row.get("sector", "")).lower()
        tax = str(row.get("tax_status", "")).lower()
        rating = str(row.get("rating_current", "")).upper()
        if any(k in name for k in psu_keywords) or "54ec" in tax or "psu" in sector or "sovereign" in rating or "g-sec" in sector:
            return "Yes"
        return "No"
    
    data["is_govt_psu"] = data.apply(detect_govt_psu, axis=1)

    seed = st.session_state.get("live_jitter_seed", 42)
    np.random.seed(seed)
    jitter = np.random.uniform(-0.25, 0.25, size=len(data))
    data["last_traded_price"] = (data["last_traded_price"] + jitter).round(2)
    data["current_yield_ytm"] = (data["current_yield_ytm"] - (jitter * 0.04)).round(2)
    return data

raw_data = enrich_live_and_entity_data(raw_data)

# App Navigation Tabs
tab_screener, tab_discover = st.tabs(["📊 Bond Screener & Analytics", "🔎 Discover & Manage Bonds"])

with tab_screener:
    # Sidebar Filters
    st.sidebar.title("🔍 Screener Filters")
    tax_slab = st.sidebar.number_input("Your Tax Slab (%)", min_value=0.0, max_value=45.0, value=12.5, step=1.0)
    target_yield = st.sidebar.number_input("Target Post-Tax Yield (%)", min_value=0.0, max_value=25.0, value=6.0, step=0.25)

    if "payment_frequency" not in raw_data.columns:
        raw_data["payment_frequency"] = "Annual"
    if "tax_status" not in raw_data.columns:
        raw_data["tax_status"] = "Taxable"

    data = compute_derived_metrics(raw_data, user_tax_rate=tax_slab)

    # Multi-Factor Weighted Buy Score
    def calculate_buy_score(row) -> float:
        score = 0.0
        post_tax = row.get("post_tax_yield", 0.0)
        score += min(30.0, max(0.0, (post_tax / 10.0) * 30.0))

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
        if 1.0 <= tenor <= 3.0:
            score += 5.0
        elif 3.0 < tenor <= 6.0:
            score += 4.0
        elif 6.0 < tenor <= 10.0:
            score += 3.0
        else:
            score += 1.5

        return round(score, 1)

    data["buy_score"] = data.apply(calculate_buy_score, axis=1)

    st.sidebar.markdown("---")
    search_query = st.sidebar.text_input("Search Issuer or ISIN", "")
    sectors = st.sidebar.multiselect("Sector", options=sorted(data['sector'].dropna().unique()))
    exchanges = st.sidebar.multiselect("Exchange", options=sorted(data['exchange'].dropna().unique()))
    freq_options = st.sidebar.multiselect("Payment Frequency", options=sorted(data['payment_frequency'].dropna().unique()))
    rating_current = st.sidebar.multiselect("Rating", options=sorted(data['rating_current'].dropna().unique()))
    secured_options = st.sidebar.multiselect("Collateral", options=sorted(data['secured_unsecured'].dropna().unique()))
    psu_filter = st.sidebar.multiselect("Govt / PSU Entity", options=["Yes", "No"])
    liquidity_levels = st.sidebar.multiselect("Liquidity Level", options=["High", "Medium", "Low"])
    tax_status = st.sidebar.multiselect("Tax Status", options=sorted(data['tax_status'].dropna().unique()))

    st.sidebar.markdown("---")
    min_ytm = float(data['current_yield_ytm'].min())
    max_ytm = float(data['current_yield_ytm'].max())
    ytm_range = st.sidebar.slider("Current YTM (%)", min_ytm, max_ytm, (min_ytm, max_ytm), step=0.1)

    valid_tenors = data[data['remaining_tenor_years'] >= 1.0]['remaining_tenor_years']
    floor_tenor = 1.0
    ceil_tenor = float(valid_tenors.max()) if not valid_tenors.empty else 10.0
    tenor_range = st.sidebar.slider("Remaining Tenor (Years)", floor_tenor, ceil_tenor, (floor_tenor, ceil_tenor), step=0.5)

    # Filter Pipeline (Bonds with tenor >= 1.0 yr)
    filtered = data[data['remaining_tenor_years'] >= 1.0].copy()

    if search_query:
        q = search_query.lower()
        filtered = filtered[filtered['issuer_name'].str.lower().str.contains(q) | filtered['isin'].str.lower().str.contains(q)]
    if sectors:
        filtered = filtered[filtered['sector'].isin(sectors)]
    if exchanges:
        filtered = filtered[filtered['exchange'].isin(exchanges)]
    if freq_options:
        filtered = filtered[filtered['payment_frequency'].isin(freq_options)]
    if rating_current:
        filtered = filtered[filtered['rating_current'].isin(rating_current)]
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

    # KPI Metrics
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Total Opportunities (> 1 Yr)", len(filtered))
    with k2:
        avg_ytm = round(filtered['current_yield_ytm'].mean(), 2) if not filtered.empty else 0.0
        st.metric("Avg Current YTM", f"{avg_ytm}%")
    with k3:
        avg_post = round(filtered['post_tax_yield'].mean(), 2) if not filtered.empty else 0.0
        st.metric("Avg Post-Tax Yield", f"{avg_post}%", delta=f"{round(avg_post - target_yield, 2)}% vs target")
    with k4:
        tot_v = round(filtered['daily_value_inr_cr'].sum(), 2) if not filtered.empty else 0.0
        st.metric("Daily Volume", f"₹ {tot_v} Cr")

    st.markdown("---")

    # Visualizations
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
                hover_data=["isin", "post_tax_yield", "buy_score", "payment_frequency"],
                labels={"remaining_tenor_years": "Tenor (Years)", "current_yield_ytm": "YTM (%)"}
            )
            fig.update_layout(template="plotly_dark", height=380, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No bonds match the selected filters.")

    with col_right:
        st.subheader("Risk & Product Buckets")
        if not filtered.empty:
            pie_fig = px.pie(filtered, names="risk_bucket", hole=0.45, color_discrete_sequence=px.colors.qualitative.Pastel)
            pie_fig.update_layout(template="plotly_dark", height=380, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(pie_fig, use_container_width=True)
        else:
            st.info("No data available.")

    # Filtered Bond Master Table
    st.subheader("📋 Filtered Bond Master")

    display_columns = [
        "isin", "issuer_name", "buy_score", "is_govt_psu", "rating_current",
        "secured_unsecured", "payment_frequency", "maturity_date",
        "current_yield_ytm", "post_tax_yield", "remaining_tenor_years",
        "last_traded_price", "liquidity_flag", "tax_status"
    ]

    sorted_filtered = filtered.sort_values(by="post_tax_yield", ascending=False).copy()
    sorted_filtered['maturity_date'] = sorted_filtered['maturity_date'].dt.strftime('%Y-%m-%d')

    format_dict = {
        "buy_score": "{:.1f}",
        "current_yield_ytm": "{:.2f}%",
        "post_tax_yield": "{:.2f}%",
        "remaining_tenor_years": "{:.1f} yrs",
        "last_traded_price": "₹{:.2f}"
    }

    def highlight_target_yield(row):
        color = 'background-color: #064e3b;' if row['post_tax_yield'] >= target_yield else ''
        return [color] * len(row)

    styled_df = (
        sorted_filtered[display_columns]
        .style
        .apply(highlight_target_yield, axis=1)
        .format(format_dict)
    )

    st.dataframe(styled_df, use_container_width=True, height=400)

    csv_bytes = sorted_filtered.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Screener Results as CSV",
        data=csv_bytes,
        file_name="ncd_gsec_screener_export.csv",
        mime="text/csv"
    )

# Tab 2: Discover & Manage Bonds
with tab_discover:
    st.subheader("🔎 Discover & Manage Master Bond Data")
    st.write(
        "Directly review, update, or edit records in `data/sample_bonds.csv`. "
        "Any modifications saved here are immediately reflected across all screener calculations."
    )

    # Load master CSV directly
    master_csv_df = pd.read_csv(CSV_FILE_PATH)
    
    # In-place dynamic table editor
    edited_df = st.data_editor(
        master_csv_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True
    )

    col1, col2 = st.columns([2, 5])
    with col1:
        if st.button("💾 Save Changes to sample_bonds.csv", use_container_width=True, type="primary"):
            # Deduplicate by ISIN while saving
            final_df = edited_df.drop_duplicates(subset=["isin"], keep="last")
            os.makedirs(os.path.dirname(CSV_FILE_PATH), exist_ok=True)
            final_df.to_csv(CSV_FILE_PATH, index=False)
            
            st.cache_data.clear()
            st.success(f"Saved {len(final_df)} unique records to `{CSV_FILE_PATH}`!")
            st.rerun()

    st.markdown("---")
    st.subheader("📥 Merge / Append From External CSV")
    uploaded_file = st.file_uploader("Upload an additional CSV file to append into your dataset", type=["csv"])
    if uploaded_file is not None:
        if st.button("➕ Append / Merge Uploaded File"):
            new_data = pd.read_csv(uploaded_file)
            merged_df = pd.concat([master_csv_df, new_data], ignore_index=True).drop_duplicates(subset=["isin"], keep="last")
            merged_df.to_csv(CSV_FILE_PATH, index=False)
            st.cache_data.clear()
            st.success(f"Merged successfully! Dataset now contains {len(merged_df)} bonds.")
            st.rerun()
