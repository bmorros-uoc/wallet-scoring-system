# backend/scoring_model.py

import pandas as pd
import numpy as np
import duckdb
from datetime import datetime, timezone
    
# --- MODEL WEIGHTS (Easily interpretable and modifiable rules) ---
# Weights must sum to 100%
WEIGHTS = {
    'Longevity_Score': 30,
    'Activity_Score': 40,
    'Diversity_Score': 20,
    'Risk_Score': 10,
}
    
def fetch_data_from_db(address: str) -> pd.DataFrame:
    """
    Retrieves the transaction DataFrame from DuckDB.
    """
    db_path = "data/wallet_data.duckdb"
    table_name = f"tx_{address}"
    
    try:
        conn = duckdb.connect(database=db_path, read_only=True)
        # Fetch the data and convert necessary columns
        df = conn.execute(f"SELECT * FROM {table_name}").fetchdf()
        conn.close()
        
        # Convert time from UNIX timestamp (string) to datetime
        df['timeStamp'] = pd.to_numeric(df['timeStamp'], errors='coerce')
        df['datetime'] = pd.to_datetime(df['timeStamp'], unit='s', utc=True)
        return df
    except Exception as e:
        # This will be triggered if the table doesn't exist (i.e., ingestion failed)
        print(f"Error retrieving data from DuckDB for {address}: {e}")
        return pd.DataFrame()

# ----------------------------------------------------
# A. INDICATOR CALCULATION: LONGEVITY 
# ----------------------------------------------------
def calculate_longevity_score(df: pd.DataFrame) -> float:
    """Calculates the Longevity Score (Longevity)."""
    if df.empty:
        return 0.0
    
    first_tx_date = df['datetime'].min().replace(tzinfo=timezone.utc)
    current_date = datetime.now(timezone.utc)
    
    # Difference in years (approximate)
    age_in_years = (current_date - first_tx_date).days / 365.25
    
    # Normalization example: 3 years = 100% score
    MAX_AGE_FOR_FULL_SCORE = 3.0  # years
    
    score = min(age_in_years / MAX_AGE_FOR_FULL_SCORE, 1.0) * 100
    return round(score, 2)
    
# ----------------------------------------------------
# B. INDICATOR CALCULATION: ACTIVITY (Frequency and Volume)
# ----------------------------------------------------
def calculate_activity_score(df: pd.DataFrame) -> float:
    """Calculates the Activity Score."""
    if df.empty:
        return 0.0

    # Metric 1: Regularity (Transactions per month)
    tx_per_month = df.set_index('datetime').resample('M').size()
    avg_monthly_tx = tx_per_month.mean() if not tx_per_month.empty else 0
    
    # Metric 2: Total number of transactions
    total_transactions = len(df)

    # Normalization (Simple Example)
    REG_THRESHOLD = 20
    reg_score = min(avg_monthly_tx / REG_THRESHOLD, 1.0) * 100
    
    VOL_THRESHOLD = 1000
    vol_score = min(total_transactions / VOL_THRESHOLD, 1.0) * 100
    
    # Combine both metrics (e.g., 50% / 50%)
    activity_score = (reg_score * 0.5) + (vol_score * 0.5)
    
    return round(activity_score, 2)

# ----------------------------------------------------
# C. INDICATOR CALCULATION: DIVERSITY (Protocol exploration)
# ----------------------------------------------------
def calculate_diversity_score(df: pd.DataFrame) -> float:
    """Calculates the Diversity Score."""
    if df.empty:
        return 0.0
        
    # Counting the diversity of 'to' addresses (interactions with contracts/wallets)
    unique_recipients = df['to'].nunique()
    
    # Normalization example: 200 unique addresses = 100% score
    DIVERSITY_THRESHOLD = 200
    score = min(unique_recipients / DIVERSITY_THRESHOLD, 1.0) * 100
    
    return round(score, 2)

# ----------------------------------------------------
# D. INDICATOR CALCULATION: RISK (Security)
# ----------------------------------------------------
def calculate_risk_score(df: pd.DataFrame) -> float:
    """
    Calculates the Risk Score (100 = Low Risk, 0 = High Risk).
    NOTE: Requires an external list of fraudulent addresses in a real system.
    """
    if df.empty:
        return 100.0 

    # SIMULATION: Known scam addresses list (for demonstration only)
    KNOWN_SCAM_ADDRESSES = [
        "0xdeadbeef...", 
        "0x12345678...", 
    ]
    
    # Count transactions sent to known risky addresses
    risky_tx_count = df[df['to'].isin(KNOWN_SCAM_ADDRESSES)].shape[0]
    
    # Penalization logic: 5 risky transactions cause max penalty
    MAX_PENALTY_TX = 5
    
    penalty = min(risky_tx_count / MAX_PENALTY_TX, 1.0) * 100
    # Risk score is inversely proportional to penalty
    risk_score = 100 - penalty

    return round(risk_score, 2)

# ----------------------------------------------------
# E. MAIN SCORING FUNCTION
# ----------------------------------------------------
def calculate_final_score(address: str) -> dict:
    """
    Calculates the final weighted score and assigns a qualitative profile.
    """
    df = fetch_data_from_db(address)
    
    if df.empty:
        return {
            'address': address,
            'status': 'Error: Could not load data. Check data ingestion step.',
            'final_score': 0,
            'indicators': {}
        }

    # 1. Calculate individual scores (Base 100)
    longevity_s = calculate_longevity_score(df)
    activity_s = calculate_activity_score(df)
    diversity_s = calculate_diversity_score(df)
    risk_s = calculate_risk_score(df) 

    indicators = {
        'Longevity_Score': longevity_s,
        'Activity_Score': activity_s,
        'Diversity_Score': diversity_s,
        'Risk_Score': risk_s,
    }

    # 2. Calculate the final weighted score (Rule-based Model)
    final_score = (
        (indicators['Longevity_Score'] * WEIGHTS['Longevity_Score']) +
        (indicators['Activity_Score'] * WEIGHTS['Activity_Score']) +
        (indicators['Diversity_Score'] * WEIGHTS['Diversity_Score']) +
        (indicators['Risk_Score'] * WEIGHTS['Risk_Score'])
    ) / 100
    
    # 3. Assign qualitative profile
    if final_score >= 85: profile = "Active Trader - High Reputation"
    elif final_score >= 60: profile = "Stable User - Medium Reputation"
    elif final_score >= 30: profile = "Inactive/New User - Low Reputation"
    else: profile = "Low Interest/Risky Wallet"

    return {
        'address': address,
        'status': 'OK',
        'final_score': round(final_score, 2),
        'profile': profile,
        'indicators': indicators,
        'weights': WEIGHTS
    }

if __name__ == '__main__':
    # --- Test Configuration ---
    TEST_ADDRESS = "0xdadB0d80178819F2319190D340ce9A924f783711" 
    
    print(f"\n--- Testing scoring model for {TEST_ADDRESS} ---\n")
    
    # Run the main scoring function
    result = calculate_final_score(TEST_ADDRESS)
    
    if result['status'] == 'OK':
        print("\n--- Wallet Scoring System Result ---")
        print(f"Address: {result['address']}")
        print(f"Final Score: {result['final_score']} / 100")
        print(f"Profile: {result['profile']}")
        print(f"Weights Used: {result['weights']}")
        print("\nIndicators (Base 100):")
        for k, v in result['indicators'].items():
             print(f" - {k}: {v}")
    else:
        # Prints error message if data could not be loaded
        print(f"Model Execution Error: {result['status']}")
