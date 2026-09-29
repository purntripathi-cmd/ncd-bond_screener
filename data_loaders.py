import pandas as pd
import numpy as np
from datetime import datetime

BENCHMARK_10Y_GSEC_YIELD = 6.82

def calculate_duration_convexity(coupon_rate: float, ytm_pct: float, tenor_years: float, freq: str = "Annual"):
    """
    Computes Macaulay Duration, Modified Duration, and Convexity for fixed-income securities.
    """
    if tenor_years <= 0 or ytm_pct <= 0:
        return 0.0, 0.0, 0.0

    m = 2 if "semi" in str(freq).lower() else (12 if "month" in str(freq).lower() else 1)
    y = (ytm_pct / 100.0) / m
    n = int(round(tenor_years * m))
    if n == 0:
        return 0.0, 0.0, 0.0

    c = (coupon_rate / m)
    face_value = 100.0

    periods = np.arange(1, n + 1)
    cash_flows = np.full(n, c)
    cash_flows[-1] += face_value

    discount_factors = 1.0 / np.power(1.0 + y, periods)
    pv_cash_flows = cash_flows * discount_factors
    bond_price = np.sum(pv_cash_flows)

    if bond_price <= 0:
        return round(tenor_years, 2), round(tenor_years, 2), 0.0

    # Macaulay Duration in years
    mac_dur_periods = np.sum(periods * pv_cash_flows) / bond_price
    mac_dur_years = mac_dur_periods / m

    # Modified Duration
    mod_dur = mac_dur_years / (1.0 + y)

    # Convexity in years^2
    convexity_periods = np.sum(periods * (periods + 1) * pv_cash_flows) / (bond_price * np.power(1.0 + y, 2))
    convexity = convexity_periods / (m * m)

    return round(float(mac_dur_years), 2), round(float(mod_dur), 2), round(float(convexity), 2)

def compute_derived_metrics(df: pd.DataFrame, user_tax_rate: float = 30.0) -> pd.DataFrame:
    """Calculates tenor, liquidity flag, risk bucketing, durations, convexity, and post-tax yields."""
    data = df.copy()
    
    # Parse dates
    data['issue_date'] = pd.to_datetime(data['issue_date'])
    data['maturity_date'] = pd.to_datetime(data['maturity_date'])
    today = pd.to_datetime(datetime.today().date())

    # 1. Remaining Tenor (Years)
    data['remaining_tenor_years'] = ((data['maturity_date'] - today).dt.days / 365.25).round(2)
    data['remaining_tenor_years'] = data['remaining_tenor_years'].apply(lambda x: max(0.1, x))

    if 'payment_frequency' not in data.columns:
        data['payment_frequency'] = 'Annual'

    # 2. Derived Liquidity Flag
    def calc_liquidity(row):
        val = row.get('daily_value_inr_cr', 0.0)
        trades = row.get('num_trades', 0)
        if val >= 20.0 or trades >= 100:
            return "High"
        elif val >= 5.0 or trades >= 30:
            return "Medium"
        return "Low"

    data['liquidity_flag'] = data.apply(calc_liquidity, axis=1)

    # 3. Post-Tax Yield (%)
    tax_factor = 1.0 - (user_tax_rate / 100.0)
    data['post_tax_yield'] = data.apply(
        lambda r: round(r['current_yield_ytm'], 2) 
        if str(r.get('tax_status', '')).strip().lower() in ['tax-free', '54ec'] 
        else round(r['current_yield_ytm'] * tax_factor, 2),
        axis=1
    )

    # 4. Credit Spread over 10Y Indian Sovereign Benchmark (bps)
    data['credit_spread_bps'] = data['current_yield_ytm'].apply(
        lambda ytm: int(round((ytm - BENCHMARK_10Y_GSEC_YIELD) * 100))
    )

    # 5. Risk Bucket Grouping
    def assign_risk_bucket(row):
        r = str(row.get('rating_current', '')).upper()
        sec = str(row.get('secured_unsecured', '')).capitalize()
        sector = str(row.get('sector', '')).lower()
        if "sovereign" in r or "g-sec" in sector or "gilt" in sector:
            return "Sovereign / G-Sec (Zero Default Risk)"
        is_safe = any(k in r for k in ['AAA', 'AA+'])
        if is_safe and ("Secured" in sec or "Senior" in str(row.get('seniority', ''))):
            return "Prime AAA/AA+ Secured"
        elif is_safe:
            return "Prime Unsecured / Tier-II"
        elif "A" in r:
            return "Moderate Yield A-Rated"
        return "High Yield / Credit Risk"

    data['risk_bucket'] = data.apply(assign_risk_bucket, axis=1)

    # 6. Macaulay Duration, Modified Duration & Convexity
    duration_metrics = [
        calculate_duration_convexity(
            row['coupon_rate'], row['current_yield_ytm'], row['remaining_tenor_years'], row['payment_frequency']
        )
        for _, row in data.iterrows()
    ]
    data['macaulay_duration'] = [d[0] for d in duration_metrics]
    data['modified_duration'] = [d[1] for d in duration_metrics]
    data['convexity'] = [d[2] for d in duration_metrics]

    # 7. Price Sensitivity to 100 bps Interest Rate Hike (+1%)
    # Delta P = -ModDur * Delta_y + 0.5 * Convexity * (Delta_y)^2
    data['price_impact_100bps_hike'] = (
        -data['modified_duration'] * 1.0 + 0.5 * data['convexity'] * 0.01
    ).round(2)

    return data

def load_sample_csv(path: str = "data/sample_bonds.csv") -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except Exception as e:
        raise RuntimeError(f"Error loading master CSV at {path}: {e}")
