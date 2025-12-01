# backend/main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import os

# Import modules created in previous steps (using relative imports for Uvicorn)
from .data_ingestion import get_wallet_transactions, save_to_db
from .scoring_model import calculate_final_score

app = FastAPI(
    title="Wallet Scoring System API (MVP)",
    description="API to calculate Web3 wallet reputation based on on-chain data.",
    version="1.0.0"
)

# --- Data Models (Pydantic) for API Response ---
# These models ensure the API response structure is clean and standardized.

class Indicators(BaseModel):
    Longevity_Score: float = Field(..., description="Wallet longevity score (0-100).")
    Activity_Score: float = Field(..., description="Score based on transaction frequency and volume (0-100).")
    Diversity_Score: float = Field(..., description="Score based on the variety of protocols/tokens used (0-100).")
    Risk_Score: float = Field(..., description="Security score (100 = low risk, 0 = high risk).")
    
class ScoreResponse(BaseModel):
    address: str = Field(..., description="The wallet address queried.")
    final_score: float = Field(..., description="Global reputation score (0-100).")
    profile: str = Field(..., description="Qualitative profile assigned to the wallet.")
    indicators: Indicators = Field(..., description="Individual indicator scores.")
    weights: dict = Field(..., description="Weights used in the rule-based scoring model.")
    

# --- API ENDPOINTS ---

@app.get("/")
def read_root():
    """Returns basic API status information."""
    return {"project_name": "Wallet Scoring System", "status": "Running", "version": "MVP 1.0"}


@app.get("/wallet/{address}/score", response_model=ScoreResponse)
def get_wallet_score(address: str):
    """
    Calculates and returns the reputation score, indicators, and profile for a given wallet address.
    
    Process:
    1. Extracts raw transaction data from Etherscan (via data_ingestion.py).
    2. Stores the data temporarily in DuckDB.
    3. Calculates individual indicators and the final weighted score (via scoring_model.py).
    """
    
    # 1. Data Extraction (Phase 2)
    print(f"-> Starting data extraction for {address}...")
    try:
        transactions_df = get_wallet_transactions(address=address)
    except ValueError as e:
         # Captures the error if API key is not configured
         raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Error during data extraction: {e}")
        
    if transactions_df.empty:
        raise HTTPException(status_code=404, detail="No transactions found for the address or API error occurred.")

    # 2. Temporary Storage (Follows Step 4 logic)
    # This ensures the data is ready for the scoring module to access it from the DB
    save_to_db(transactions_df, address)
    
    # 3. Score Calculation (Phase 3)
    print("-> Calculating score...")
    score_result = calculate_final_score(address=address)
    
    if score_result['status'] != 'OK':
         raise HTTPException(status_code=500, detail=score_result['status'])

    # 4. Return Response
    return score_result
