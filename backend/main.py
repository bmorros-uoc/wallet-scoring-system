# backend/main.py

from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel, Field

from .data_ingestion import (
    get_wallet_transactions,
    get_wallet_erc20_transfers,
    save_to_db,
)
from .scoring_model import calculate_final_score

app = FastAPI(
    title="Wallet Scoring System API (MVP)",
    description="API to calculate Web3 wallet reputation based on on-chain data.",
    version="1.2.0"
)

class Indicators(BaseModel):
    Activity_Score: float = Field(..., description="Score based on transaction frequency and volume (0-100).")
    Longevity_Score: float = Field(..., description="Wallet longevity score (0-100).")
    Diversity_Score: float = Field(..., description="Score based on ecosystem footprint / interactions (0-100).")
    General_Risk_Score: float = Field(..., description="General security score (100 = low risk, 0 = high risk).")
    Asset_Risk_Score: float = Field(..., description="Specific asset/AML risk (mixers/privacy) (100 = low risk).")

class ScoreResponse(BaseModel):
    address: str = Field(..., description="The wallet address queried.")
    final_score: float = Field(..., description="Global reputation score (0-100).")
    profile: str = Field(..., description="Qualitative profile assigned to the wallet.")
    indicators: Indicators = Field(..., description="Individual indicator scores.")
    weights: dict = Field(..., description="Weights used in the scoring model.")

@app.get("/")
def read_root():
    return {"project_name": "Wallet Scoring System", "status": "Running", "version": "MVP 1.2"}

@app.get("/wallet/{address}/score", response_model=ScoreResponse)
def get_wallet_score(address: str = Path(..., regex=r"^0x[a-fA-F0-9]{40}$")):
    try:
        tx_df = get_wallet_transactions(address=address)
        if tx_df.empty:
            raise HTTPException(status_code=404, detail="No transactions found for the address or API error occurred.")

        erc20_df = get_wallet_erc20_transfers(address=address)

    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during data extraction: {e}")

    save_to_db(tx_df, address, table_kind="tx")
    save_to_db(erc20_df, address, table_kind="erc20")

    score_result = calculate_final_score(address=address)
    if score_result.get("status") != "OK":
        raise HTTPException(status_code=500, detail=score_result.get("status", "Unknown error"))

    return score_result
