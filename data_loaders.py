import pandas as pd
import numpy as np
from datetime import datetime

def compute_derived_metrics(df: pd.DataFrame, user_tax_rate: float = 30.0) -> pd.DataFrame:
    """Calculates tenor, liquidity flag, risk bucketing, and post-tax yields."""
    data = df.copy()
    
    # Parse dates
    data['issue_date'] = pd.to_datetime(data['issue_date'])
    data['maturity_date'] = pd.to_datetime(data['maturity_date'])
    today = pd.to_datetime(datetime.today().date())

    # 1. Remaining Tenor (Years)
    data['remaining_tenor_years'] = ((data['maturity_date'] - today).dt.days / 365.25).round(2)
    data['remaining_tenor_years'] = data['remaining_tenor_years'].apply(lambda x: max(0.0, x))

    # Ensure payment frequency exists
    if 'payment_frequency' not in data.columns:
        data['payment_frequency'] = 'Annual'

    # 2. Derived Liquidity Flag
    def calc_liquidity(row):
        val = row.get('daily_value_inr_cr', 0.0)
        trades = row.get('num_trades', 0)
        if val >= 5.0 or trades >= 50:
            return "High"
        elif val >= 1.0 or trades >= 15:
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

    # 4. Risk Bucket Grouping
    def assign_risk_bucket(row):
        r = str(row.get('rating_current', '')).upper()
        sec = str(row.get('secured_unsecured', '')).capitalize()
        sector = str(row.get('sector', '')).lower()
        if "sovereign" in r or "g-sec" in sector or "gilt" in sector:
            return "Sovereign / G-Sec (Zero Default Risk)"
        is_safe = any(k in r for k in ['AAA', 'AA+', 'AA'])
        if is_safe and sec == "Secured":
            return "Prime Secured (Lower Risk)"
        elif is_safe and sec != "Secured":
            return "Prime Unsecured"
        elif "A" in r and sec == "Secured":
            return "Moderate Yield Secured"
        return "High Yield / Credit Risk"

    data['risk_bucket'] = data.apply(assign_risk_bucket, axis=1)
    return data

def load_sample_csv(path: str = "data/sample_bonds.csv") -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except Exception as e:
        raise RuntimeError(f"Error loading master CSV at {path}: {e}")
