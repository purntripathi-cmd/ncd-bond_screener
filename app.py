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

# Combined Master Catalog: New Sovereign G-Secs/Gilts + All Previous Bonds
MASTER_BONDS_CATALOG = [
    {
        "isin": "IN0020230036", "issuer_name": "Government of India (7.17% GS 2030)", "sector": "G-Sec / Sovereign",
        "exchange": "Both", "listing_status": "Listed", "coupon_rate": 7.17, "coupon_type": "Fixed",
        "current_yield_ytm": 6.85, "last_traded_price": 101.40, "accrued_interest": 2.10, "issue_date": "2023-04-17",
        "maturity_date": "2030-04-16", "payment_frequency": "Semi-Annual", "repayment_mode": "Bullet",
        "call_put_option": "No", "premature_withdrawal_allowed": "No", "rating_current": "SOVEREIGN",
        "rating_agency": "RBI/Govt", "rating_outlook": "Stable", "rating_date": "2024-01-01",
        "secured_unsecured": "Sovereign Guarantee", "seniority": "Senior", "security_cover_ratio": 1.0,
        "daily_volume_units": 85000, "daily_value_inr_cr": 85.5, "num_trades": 340, "issue_size_inr_cr": 32000.0,
        "outstanding_inr_cr": 32000.0, "tax_status": "Taxable", "tds_applicable": "No", "min_investment_units": 10, "lot_size": 10
    },
    {
        "isin": "IN0020240035", "issuer_name": "Government of India (7.34% GS 2064 Gilt)", "sector": "G-Sec / Sovereign",
        "exchange": "Both", "listing_status": "Listed", "coupon_rate": 7.34, "coupon_type": "Fixed",
        "current_yield_ytm": 7.02, "last_traded_price": 102.10, "accrued_interest": 1.95, "issue_date": "2024-04-22",
        "maturity_date": "2064-04-22", "payment_frequency": "Semi-Annual", "repayment_mode": "Bullet",
        "call_put_option": "No", "premature_withdrawal_allowed": "No", "rating_current": "SOVEREIGN",
        "rating_agency": "RBI/Govt", "rating_outlook": "Stable", "rating_date": "2024-04-01",
        "secured_unsecured": "Sovereign Guarantee", "seniority": "Senior", "security_cover_ratio": 1.0,
        "daily_volume_units": 45000, "daily_value_inr_cr": 46.2, "num_trades": 180, "issue_size_inr_cr": 25000.0,
        "outstanding_inr_cr": 25000.0, "tax_status": "Taxable", "tds_applicable": "No", "min_investment_units": 10, "lot_size": 10
    },
    {
        "isin": "INE261F08EU4", "issuer_name": "NABARD (National Bank for Agri & Rural Dev)", "sector": "PSU / FI",
        "exchange": "NSE", "listing_status": "Listed", "coupon_rate": 7.44, "coupon_type": "Fixed",
        "current_yield_ytm": 7.55, "last_traded_price": 99.60, "accrued_interest": 1.10, "issue_date": "2024-07-17",
        "maturity_date": "2029-07-17", "payment_frequency": "Annual", "repayment_mode": "Bullet",
        "call_put_option": "No", "premature_withdrawal_allowed": "No", "rating_current": "AAA",
        "rating_agency": "CRISIL", "rating_outlook": "Stable", "rating_date": "2024-05-10",
        "secured_unsecured": "Secured", "seniority": "Senior", "security_cover_ratio": 1.15,
        "daily_volume_units": 15000, "daily_value_inr_cr": 15.0, "num_trades": 90, "issue_size_inr_cr": 5000.0,
        "outstanding_inr_cr": 5000.0, "tax_status": "Taxable", "tds_applicable": "Yes", "min_investment_units": 1, "lot_size": 1
    },
    {
        "isin": "INE053F08312", "issuer_name": "Indian Railway Finance Corp (IRFC)", "sector": "PSU / Railways",
        "exchange": "Both", "listing_status": "Listed", "coupon_rate": 7.64, "coupon_type": "Fixed",
        "current_yield_ytm": 7.32, "last_traded_price": 101.80, "accrued_interest": 4.10, "issue_date": "2021-03-22",
        "maturity_date": "2031-03-22", "payment_frequency": "Annual", "repayment_mode": "Bullet",
        "call_put_option": "No", "premature_withdrawal_allowed": "No", "rating_current": "AAA",
        "rating_agency": "CRISIL", "rating_outlook": "Stable", "rating_date": "2024-02-14",
        "secured_unsecured": "Secured", "seniority": "Senior", "security_cover_ratio": 1.25,
        "daily_volume_units": 12000, "daily_value_inr_cr": 12.2, "num_trades": 110, "issue_size_inr_cr": 4500.0,
        "outstanding_inr_cr": 4500.0, "tax_status": "Tax-free", "tds_applicable": "No", "min_investment_units": 1, "lot_size": 1
    },
    {
        "isin": "INE020B08FY2", "issuer_name": "REC Limited 6.70% 54EC Bonds", "sector": "PSU / Infra NBFC",
        "exchange": "Both", "listing_status": "Listed", "coupon_rate": 6.70, "coupon_type": "Fixed",
        "current_yield_ytm": 7.48, "last_traded_price": 97.65, "accrued_interest": 3.80, "issue_date": "2021-12-31",
        "maturity_date": "2029-12-31", "payment_frequency": "Annual", "repayment_mode": "Bullet",
        "call_put_option": "No", "premature_withdrawal_allowed": "No", "rating_current": "AAA",
        "rating_agency": "CARE", "rating_outlook": "Stable", "rating_date": "2024-03-01",
        "secured_unsecured": "Secured", "seniority": "Senior", "security_cover_ratio": 1.15,
        "daily_volume_units": 7500, "daily_value_inr_cr": 7.35, "num_trades": 55, "issue_size_inr_cr": 3000.0,
        "outstanding_inr_cr": 3000.0, "tax_status": "54EC", "tds_applicable": "No", "min_investment_units": 1, "lot_size": 1
    },
    {
        "isin": "INE296A07UB9", "issuer_name": "Bajaj Finance Limited 7.70% NCD", "sector": "NBFC",
        "exchange": "Both", "listing_status": "Listed", "coupon_rate": 7.70, "coupon_type": "Fixed",
        "current_yield_ytm": 7.92, "last_traded_price": 99.25, "accrued_interest": 2.65, "issue_date": "2024-09-20",
        "maturity_date": "2029-09-20", "payment_frequency": "Annual", "repayment_mode": "Bullet",
        "call_put_option": "No", "premature_withdrawal_allowed": "No", "rating_current": "AAA",
        "rating_agency": "CRISIL", "rating_outlook": "Stable", "rating_date": "2024-09-01",
        "secured_unsecured": "Secured", "seniority": "Senior", "security_cover_ratio": 1.20,
        "daily_volume_units": 17500, "daily_value_inr_cr": 17.4, "num_trades": 135, "issue_size_inr_cr": 2000.0,
        "outstanding_inr_cr": 2000.0, "tax_status": "Taxable", "tds_applicable": "Yes", "min_investment_units": 1, "lot_size": 1
    },
    {
        "isin": "INE674K08083", "issuer_name": "Aditya Birla Capital 8.07% NCD", "sector": "NBFC / Conglomerate",
        "exchange": "NSE", "listing_status": "Listed", "coupon_rate": 8.07, "coupon_type": "Fixed",
        "current_yield_ytm": 8.10, "last_traded_price": 99.80, "accrued_interest": 1.40, "issue_date": "2024-04-30",
        "maturity_date": "2036-04-30", "payment_frequency": "Annual", "repayment_mode": "Bullet",
        "call_put_option": "No", "premature_withdrawal_allowed": "No", "rating_current": "AAA",
        "rating_agency": "ICRA", "rating_outlook": "Stable", "rating_date": "2024-04-15",
        "secured_unsecured": "Secured", "seniority": "Senior", "security_cover_ratio": 1.15,
        "daily_volume_units": 3200, "daily_value_inr_cr": 3.2, "num_trades": 28, "issue_size_inr_cr": 1000.0,
        "outstanding_inr_cr": 1000.0, "tax_status": "Taxable", "tds_applicable": "Yes", "min_investment_units": 1, "lot_size": 1
    },
    {
        "isin": "INE342T07726", "issuer_name": "Navi Finserv Limited 10.75%", "sector": "Fintech / NBFC",
        "exchange": "BSE", "listing_status": "Listed", "coupon_rate": 10.75, "coupon_type": "Fixed",
        "current_yield_ytm": 10.85, "last_traded_price": 100.60, "accrued_interest": 4.15, "issue_date": "2024-08-31",
        "maturity_date": "2029-08-31", "payment_frequency": "Monthly", "repayment_mode": "Bullet",
        "call_put_option": "No", "premature_withdrawal_allowed": "No", "rating_current": "A",
        "rating_agency": "CRISIL", "rating_outlook": "Stable", "rating_date": "2024-08-10",
        "secured_unsecured": "Secured", "seniority": "Senior", "security_cover_ratio": 1.10,
        "daily_volume_units": 2700, "daily_value_inr_cr": 2.7, "num_trades": 35, "issue_size_inr_cr": 300.0,
        "outstanding_inr_cr": 300.0, "tax_status": "Taxable", "tds_applicable": "Yes", "min_investment_units": 10, "lot_size": 10
    },
    {
        "isin": "INE001A07SD4", "issuer_name": "HDFC Bank Ltd Tier-II", "sector": "Banking",
        "exchange": "Both", "listing_status": "Listed", "coupon_rate": 7.95, "coupon_type": "Fixed",
        "current_yield_ytm": 7.82, "last_traded_price": 1008.50, "accrued_interest": 12.30, "issue_date": "2021-09-15",
        "maturity_date": "2031-09-15", "payment_frequency": "Annual", "repayment_mode": "Bullet",
        "call_put_option": "No", "premature_withdrawal_allowed": "No", "rating_current": "AAA",
        "rating_agency": "CRISIL", "rating_outlook": "Stable", "rating_date": "2024-01-10",
        "secured_unsecured": "Unsecured", "seniority": "Senior", "security_cover_ratio": 0.0,
        "daily_volume_units": 4500, "daily_value_inr_cr": 4.54, "num_trades": 42, "issue_size_inr_cr": 5000.0,
        "outstanding_inr_cr": 5000.0, "tax_status": "Taxable", "tds_applicable": "Yes", "min_investment_units": 10, "lot_size": 10
    },
    {
        "isin": "INE296A07RW1", "issuer_name": "Bajaj Finance Ltd Long Term", "sector": "NBFC",
        "exchange": "Both", "listing_status": "Listed", "coupon_rate": 8.25, "coupon_type": "Fixed",
        "current_yield_ytm": 8.10, "last_traded_price": 1005.00, "accrued_interest": 8.50, "issue_date": "2022-03-20",
        "maturity_date": "2031-12-02", "payment_frequency": "Annual", "repayment_mode": "Bullet",
        "call_put_option": "No", "premature_withdrawal_allowed": "No", "rating_current": "AAA",
        "rating_agency": "CRISIL", "rating_outlook": "Stable", "rating_date": "2024-02-15",
        "secured_unsecured": "Secured", "seniority": "Senior", "security_cover_ratio": 1.25,
        "daily_volume_units": 12000, "daily_value_inr_cr": 12.06, "num_trades": 115, "issue_size_inr_cr": 2500.0,
        "outstanding_inr_cr": 2500.0, "tax_status": "Taxable", "tds_applicable": "Yes", "min_investment_units": 1, "lot_size": 1
    },
    {
        "isin": "INE556F08KD1", "issuer_name": "Small Industries Dev Bank (SIDBI)", "sector": "FI / Bank",
        "exchange": "NSE", "listing_status": "Listed", "coupon_rate": 7.70, "coupon_type": "Fixed",
        "current_yield_ytm": 7.65, "last_traded_price": 1001.20, "accrued_interest": 5.10, "issue_date": "2023-01-10",
        "maturity_date": "2029-01-10", "payment_frequency": "Annual", "repayment_mode": "Bullet",
        "call_put_option": "No", "premature_withdrawal_allowed": "No", "rating_current": "AAA",
        "rating_agency": "CARE", "rating_outlook": "Stable", "rating_date": "2024-01-05",
        "secured_unsecured": "Unsecured", "seniority": "Senior", "security_cover_ratio": 0.0,
        "daily_volume_units": 8500, "daily_value_inr_cr": 8.51, "num_trades": 60, "issue_size_inr_cr": 4000.0,
        "outstanding_inr_cr": 4000.0, "tax_status": "Taxable", "tds_applicable": "No", "min_investment_units": 5, "lot_size": 5
    },
    {
        "isin": "INE244L07187", "issuer_name": "Piramal Capital & Housing Fin", "sector": "Housing Finance",
        "exchange": "NSE", "listing_status": "Listed", "coupon_rate": 9.75, "coupon_type": "Fixed",
        "current_yield_ytm": 10.25, "last_traded_price": 985.00, "accrued_interest": 24.50, "issue_date": "2022-07-14",
        "maturity_date": "2028-07-14", "payment_frequency": "Annual", "repayment_mode": "Bullet",
        "call_put_option": "Yes", "premature_withdrawal_allowed": "No", "rating_current": "AA",
        "rating_agency": "ICRA", "rating_outlook": "Stable", "rating_date": "2024-01-22",
        "secured_unsecured": "Secured", "seniority": "Senior", "security_cover_ratio": 1.10,
        "daily_volume_units": 1800, "daily_value_inr_cr": 1.77, "num_trades": 28, "issue_size_inr_cr": 1000.0,
        "outstanding_inr_cr": 850.0, "tax_status": "Taxable", "tds_applicable": "Yes", "min_investment_units": 1, "lot_size": 1
    },
    {
        "isin": "INE020B08DF6", "issuer_name": "REC Limited Infrastructure", "sector": "Infra / NBFC",
        "exchange": "Both", "listing_status": "Listed", "coupon_rate": 7.54, "coupon_type": "Fixed",
        "current_yield_ytm": 7.48, "last_traded_price": 1004.00, "accrued_interest": 18.90, "issue_date": "2020-04-15",
        "maturity_date": "2030-04-15", "payment_frequency": "Annual", "repayment_mode": "Bullet",
        "call_put_option": "No", "premature_withdrawal_allowed": "No", "rating_current": "AAA",
        "rating_agency": "India Ratings", "rating_outlook": "Stable", "rating_date": "2024-03-01",
        "secured_unsecured": "Secured", "seniority": "Senior", "security_cover_ratio": 1.15,
        "daily_volume_units": 9500, "daily_value_inr_cr": 9.54, "num_trades": 84, "issue_size_inr_cr": 3000.0,
        "outstanding_inr_cr": 3000.0, "tax_status": "54EC", "tds_applicable": "No", "min_investment_units": 1, "lot_size": 1
    },
    {
        "isin": "INE756I07EA9", "issuer_name": "InCred Financial Services", "sector": "NBFC",
        "exchange": "BSE", "listing_status": "Listed", "coupon_rate": 10.30, "coupon_type": "Fixed",
        "current_yield_ytm": 10.65, "last_traded_price": 992.50, "accrued_interest": 14.20, "issue_date": "2023-05-12",
        "maturity_date": "2028-11-12", "payment_frequency": "Monthly", "repayment_mode": "Amortizing",
        "call_put_option": "No", "premature_withdrawal_allowed": "No", "rating_current": "A+",
        "rating_agency": "CRISIL", "rating_outlook": "Positive", "rating_date": "2024-03-18",
        "secured_unsecured": "Secured", "seniority": "Senior", "security_cover_ratio": 1.15,
        "daily_volume_units": 620, "daily_value_inr_cr": 0.62, "num_trades": 14, "issue_size_inr_cr": 200.0,
        "outstanding_inr_cr": 180.0, "tax_status": "Taxable", "tds_applicable": "Yes", "min_investment_units": 1, "lot_size": 1
    },
    {
        "isin": "INE121A08OE8", "issuer_name": "Cholamandalam Inv & Fin", "sector": "NBFC",
        "exchange": "NSE", "listing_status": "Listed", "coupon_rate": 8.40, "coupon_type": "Fixed",
        "current_yield_ytm": 8.28, "last_traded_price": 1006.10, "accrued_interest": 7.80, "issue_date": "2022-10-18",
        "maturity_date": "2028-10-18", "payment_frequency": "Annual", "repayment_mode": "Bullet",
        "call_put_option": "No", "premature_withdrawal_allowed": "No", "rating_current": "AA+",
        "rating_agency": "ICRA", "rating_outlook": "Stable", "rating_date": "2024-01-15",
        "secured_unsecured": "Secured", "seniority": "Senior", "security_cover_ratio": 1.20,
        "daily_volume_units": 5400, "daily_value_inr_cr": 5.43, "num_trades": 39, "issue_size_inr_cr": 1200.0,
        "outstanding_inr_cr": 1200.0, "tax_status": "Taxable", "tds_applicable": "Yes", "min_investment_units": 1, "lot_size": 1
    },
    {
        "isin": "INE002A08609", "issuer_name": "Reliance Industries Ltd NCD", "sector": "Manufacturing",
        "exchange": "Both", "listing_status": "Listed", "coupon_rate": 7.62, "coupon_type": "Fixed",
        "current_yield_ytm": 7.50, "last_traded_price": 1010.00, "accrued_interest": 11.10, "issue_date": "2023-03-23",
        "maturity_date": "2033-03-23", "payment_frequency": "Annual", "repayment_mode": "Bullet",
        "call_put_option": "No", "premature_withdrawal_allowed": "No", "rating_current": "AAA",
        "rating_agency": "CRISIL", "rating_outlook": "Stable", "rating_date": "2024-01-11",
        "secured_unsecured": "Secured", "seniority": "Senior", "security_cover_ratio": 1.50,
        "daily_volume_units": 15000, "daily_value_inr_cr": 15.15, "num_trades": 140, "issue_size_inr_cr": 7500.0,
        "outstanding_inr_cr": 7500.0, "tax_status": "Taxable", "tds_applicable": "Yes", "min_investment_units": 10, "lot_size": 10
    },
    {
        "isin": "INE040A08377", "issuer_name": "HDFC Credila Financial Services", "sector": "Education NBFC",
        "exchange": "NSE", "listing_status": "Listed", "coupon_rate": 8.90, "coupon_type": "Fixed",
        "current_yield_ytm": 9.15, "last_traded_price": 990.00, "accrued_interest": 6.40, "issue_date": "2023-08-01",
        "maturity_date": "2028-08-01", "payment_frequency": "Annual", "repayment_mode": "Bullet",
        "call_put_option": "No", "premature_withdrawal_allowed": "No", "rating_current": "AA+",
        "rating_agency": "CRISIL", "rating_outlook": "Stable", "rating_date": "2024-02-28",
        "secured_unsecured": "Secured", "seniority": "Senior", "security_cover_ratio": 1.10,
        "daily_volume_units": 800, "daily_value_inr_cr": 0.79, "num_trades": 16, "issue_size_inr_cr": 500.0,
        "outstanding_inr_cr": 500.0, "tax_status": "Taxable", "tds_applicable": "Yes", "min_investment_units": 1, "lot_size": 1
    },
    {
        "isin": "INE528S07128", "issuer_name": "Edelweiss Financial Services", "sector": "NBFC",
        "exchange": "BSE", "listing_status": "Listed", "coupon_rate": 10.40, "coupon_type": "Floating",
        "current_yield_ytm": 11.20, "last_traded_price": 970.00, "accrued_interest": 32.00, "issue_date": "2023-01-07",
        "maturity_date": "2029-01-07", "payment_frequency": "Annual", "repayment_mode": "Bullet",
        "call_put_option": "Yes", "premature_withdrawal_allowed": "No", "rating_current": "A+",
        "rating_agency": "CRISIL", "rating_outlook": "Stable", "rating_date": "2024-01-12",
        "secured_unsecured": "Secured", "seniority": "Subordinated", "security_cover_ratio": 1.10,
        "daily_volume_units": 400, "daily_value_inr_cr": 0.39, "num_trades": 11, "issue_size_inr_cr": 400.0,
        "outstanding_inr_cr": 320.0, "tax_status": "Taxable", "tds_applicable": "Yes", "min_investment_units": 1, "lot_size": 1
    }
]

# 1. Load Data
@st.cache_data(ttl=600)
def get_bond_data():
    if not os.path.exists(CSV_FILE_PATH):
        os.makedirs("data", exist_ok=True)
        pd.DataFrame(MASTER_BONDS_CATALOG).to_csv(CSV_FILE_PATH, index=False)
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
    tax_slab = st.sidebar.number_input("Your Tax Slab (%)", min_value=0.0, max_value=45.0, value=30.0, step=1.0)
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
        if "Secured" in sec or "Sovereign" in sec:
            score += 15.0
        else:
            score += 5.0
            
        if row.get("is_govt_psu") == "Yes":
            score += 15.0
        else:
            score += 5.0
            
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

    # Filter out bonds with tenor < 1.0 year as requested
    valid_tenors = data[data['remaining_tenor_years'] >= 1.0]['remaining_tenor_years']
    floor_tenor = 1.0
    ceil_tenor = float(valid_tenors.max()) if not valid_tenors.empty else 10.0
    tenor_range = st.sidebar.slider("Remaining Tenor (Years)", floor_tenor, ceil_tenor, (floor_tenor, ceil_tenor), step=0.5)

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
    st.subheader("🔎 Discover & Sync Master Bond Data")
    st.write(
        "Select bonds below to add them to your dataset. Clicking **Append / Merge to sample_bonds.csv** "
        "will merge selected bonds with your existing records using **ISIN** as unique identifier without duplicates or overwriting existing data."
    )

    catalog_df = pd.DataFrame(MASTER_BONDS_CATALOG)
    catalog_df["Select"] = True

    edited_df = st.data_editor(
        catalog_df[[
            "Select", "isin", "issuer_name", "sector", "rating_current",
            "coupon_rate", "current_yield_ytm", "payment_frequency",
            "issue_date", "maturity_date", "last_traded_price", "tax_status"
        ]],
        use_container_width=True,
        hide_index=True
    )

    col_btn, _ = st.columns([3, 4])
    with col_btn:
        if st.button("➕ Append / Merge to sample_bonds.csv", use_container_width=True, type="primary"):
            selected_isins = edited_df[edited_df["Select"] == True]["isin"].tolist()
            new_selection_df = catalog_df[catalog_df["isin"].isin(selected_isins)].drop(columns=["Select"])
            
            os.makedirs(os.path.dirname(CSV_FILE_PATH), exist_ok=True)
            
            # Read existing records if file exists to perform append / de-duplicated merge
            if os.path.exists(CSV_FILE_PATH):
                existing_df = pd.read_csv(CSV_FILE_PATH)
                # Combine existing + new selections and drop duplicate ISINs (keeps latest updated fields)
                combined_df = pd.concat([existing_df, new_selection_df], ignore_index=True).drop_duplicates(subset=["isin"], keep="last")
            else:
                combined_df = new_selection_df
            
            combined_df.to_csv(CSV_FILE_PATH, index=False)
            
            st.cache_data.clear()
            st.success(f"Merged successfully! Master dataset now contains {len(combined_df)} unique bonds in `{CSV_FILE_PATH}`.")
            st.rerun()
