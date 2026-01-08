# backend/scoring_model.py

import re
import os
import time
import duckdb
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

WEIGHTS = {
    "Activity_Score": 25,
    "Longevity_Score": 20,
    "Diversity_Score": 25,
    "General_Risk_Score": 25,
    "Asset_Risk_Score": 5,
}

DB_PATH = "data/wallet_data.duckdb"
ETH_ADDRESS_RE = re.compile(r"^0x[a-f0-9]{40}$")

INDICATOR_ORDER = [
    "Activity_Score",
    "Longevity_Score",
    "Diversity_Score",
    "General_Risk_Score",
    "Asset_Risk_Score",
]

def normalize_address(address: str) -> str:
    a = (address or "").strip().lower()
    if not ETH_ADDRESS_RE.fullmatch(a):
        raise ValueError("Invalid Ethereum address format")
    return a

def table_name(address: str, table_kind: str) -> str:
    a = normalize_address(address)
    suffix = a[2:]
    if table_kind not in {"tx", "erc20"}:
        raise ValueError("table_kind must be 'tx' or 'erc20'")
    return f"{table_kind}_{suffix}"

def fetch_tx_from_db(address: str) -> pd.DataFrame:
    tname = table_name(address, "tx")
    try:
        conn = duckdb.connect(database=DB_PATH, read_only=True)
        df = conn.execute(f"SELECT * FROM {tname}").fetchdf()
        conn.close()

        if df.empty or "empty_flag" in df.columns:
            return pd.DataFrame()

        df["timeStamp"] = pd.to_numeric(df["timeStamp"], errors="coerce")
        df["datetime"] = pd.to_datetime(df["timeStamp"], unit="s", utc=True)

        df["value"] = pd.to_numeric(df.get("value", 0), errors="coerce").fillna(0)
        df["value_eth"] = df["value"] / 1e18

        if "to" in df.columns:
            df["to"] = df["to"].astype(str).str.lower()
        if "from" in df.columns:
            df["from"] = df["from"].astype(str).str.lower()

        return df
    except Exception:
        return pd.DataFrame()

def fetch_erc20_from_db(address: str) -> pd.DataFrame:
    tname = table_name(address, "erc20")
    try:
        conn = duckdb.connect(database=DB_PATH, read_only=True)
        df = conn.execute(f"SELECT * FROM {tname}").fetchdf()
        conn.close()

        if df.empty or "empty_flag" in df.columns:
            return pd.DataFrame()

        if "contractAddress" in df.columns:
            df["contractAddress"] = df["contractAddress"].astype(str).str.lower()
        if "tokenSymbol" in df.columns:
            df["tokenSymbol"] = df["tokenSymbol"].astype(str)

        return df
    except Exception:
        return pd.DataFrame()

# ----------------------------
# Etherscan tag lookup (address metadata / labels)
# ----------------------------
def get_etherscan_address_tag(address: str, chainid: int = 1) -> dict | None:
    if not ETHERSCAN_API_KEY:
        return None

    a = normalize_address(address)
    url = (
        "https://api.etherscan.io/v2/api"
        f"?chainid={chainid}"
        "&module=nametag&action=getaddresstag"
        f"&address={a}"
        f"&apikey={ETHERSCAN_API_KEY}"
    )
    try:
        r = requests.get(url, timeout=20)
        data = r.json()
        if data.get("status") == "1" and data.get("result"):
            return data["result"][0]
        return None
    except Exception:
        return None

def is_scam_label(tag_obj: dict) -> bool:
    if not tag_obj:
        return False

    labels = tag_obj.get("labels", []) or []
    labels_slug = tag_obj.get("labels_slug", []) or []

    labels_norm = " ".join([str(x).lower() for x in labels])
    slugs_norm = " ".join([str(x).lower() for x in labels_slug])

    scam_markers = ["phish", "hack", "scam", "drainer", "malicious", "exploit", "fraud", "blacklist", "ofac"]
    return any(m in labels_norm for m in scam_markers) or any(m in slugs_norm for m in scam_markers)

def detect_tagged_scam_counterparties(df_tx: pd.DataFrame, max_to_check: int = 40, sleep_s: float = 0.55) -> tuple[int, list[str]]:
    """
    Returns:
      - count of counterparties tagged scam
      - sample list of tagged addresses (up to 10)
    """
    if df_tx.empty or "to" not in df_tx.columns or not ETHERSCAN_API_KEY:
        return 0, []

    top_to = (
        df_tx["to"]
        .dropna()
        .astype(str)
        .str.lower()
        .value_counts()
        .head(max_to_check)
        .index
        .tolist()
    )

    tagged = []
    for addr in top_to:
        if not ETH_ADDRESS_RE.fullmatch(addr):
            continue
        tag = get_etherscan_address_tag(addr)
        if is_scam_label(tag):
            tagged.append(addr)
        time.sleep(sleep_s)

    return len(tagged), tagged[:10]

# ----------------------------
# Indicators
# ----------------------------
def calculate_longevity_score(df_tx: pd.DataFrame) -> float:
    if df_tx.empty:
        return 0.0
    first_tx = df_tx["datetime"].min()
    now = datetime.now(timezone.utc)
    days = max((now - first_tx).days, 0)

    denom = np.log(730 + 1)
    score = (np.log(days + 1) / denom) * 100.0 if denom > 0 else 0.0
    return round(float(min(score, 100.0)), 2)

def calculate_activity_score(df_tx: pd.DataFrame) -> float:
    if df_tx.empty:
        return 0.0

    tx_count = len(df_tx)
    volume_eth = float(df_tx["value_eth"].sum())

    MAX_TX = 5000.0
    MAX_VOL = 10000.0

    tx_norm = np.log10(tx_count + 1) / np.log10(MAX_TX + 1)
    vol_norm = np.log10(volume_eth + 1) / np.log10(MAX_VOL + 1)

    tx_norm = float(np.clip(tx_norm, 0, 1))
    vol_norm = float(np.clip(vol_norm, 0, 1))

    return round(float((0.5 * tx_norm + 0.5 * vol_norm) * 100.0), 2)

def calculate_diversity_score(df_tx: pd.DataFrame) -> float:
    if df_tx.empty:
        return 0.0
    unique_to = int(df_tx["to"].nunique()) if "to" in df_tx.columns else 0
    THRESHOLD = 25.0
    score = min(100.0, (unique_to / THRESHOLD) * 100.0) if THRESHOLD > 0 else 0.0
    return round(float(score), 2)

def calculate_general_risk_score(df_tx: pd.DataFrame, tagged_scam_count: int) -> float:
    if df_tx.empty:
        return 100.0

    KNOWN_SCAM_ADDRESSES = {
        "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        "0x1234567812345678123456781234567812345678",
    }

    incidents_list = 0
    if "to" in df_tx.columns:
        incidents_list = int(df_tx[df_tx["to"].isin(KNOWN_SCAM_ADDRESSES)].shape[0])

    incidents = incidents_list + tagged_scam_count

    lam = 0.9
    score = 100.0 * np.exp(-lam * incidents)
    return round(float(np.clip(score, 0, 100)), 2)

def calculate_asset_risk_score(df_tx: pd.DataFrame, df_erc20: pd.DataFrame) -> float:
    MIXER_OR_PRIVACY_TOOLING = {
        "0x1111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222",
    }

    incidents_tools = 0
    if not df_tx.empty and "to" in df_tx.columns:
        incidents_tools = int(df_tx[df_tx["to"].isin(MIXER_OR_PRIVACY_TOOLING)].shape[0])

    PRIVACY_TOKEN_CONTRACTS = {
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    }

    incidents_tokens = 0
    if not df_erc20.empty and "contractAddress" in df_erc20.columns:
        incidents_tokens = int(df_erc20[df_erc20["contractAddress"].isin(PRIVACY_TOKEN_CONTRACTS)].shape[0])

    incidents = incidents_tools + incidents_tokens

    lam = 0.6
    score = 100.0 * np.exp(-lam * incidents)
    return round(float(np.clip(score, 0, 100)), 2)

# ----------------------------
# Final score
# ----------------------------
def calculate_final_score(address: str) -> dict:
    try:
        a = normalize_address(address)
    except ValueError as e:
        return {"address": address, "status": str(e), "final_score": 0, "indicators": {}}

    df_tx = fetch_tx_from_db(a)
    if df_tx.empty:
        return {"address": a, "status": "Error: Could not load tx data. Check ingestion step.", "final_score": 0, "indicators": {}}

    df_erc20 = fetch_erc20_from_db(a)

    # Tag-based scam detection (for diagnostics + risk)
    tagged_scam_count, tagged_sample = detect_tagged_scam_counterparties(df_tx)

    indicators = {
        "Activity_Score": calculate_activity_score(df_tx),
        "Longevity_Score": calculate_longevity_score(df_tx),
        "Diversity_Score": calculate_diversity_score(df_tx),
        "General_Risk_Score": calculate_general_risk_score(df_tx, tagged_scam_count),
        "Asset_Risk_Score": calculate_asset_risk_score(df_tx, df_erc20),
    }

    final_score = sum(indicators[k] * WEIGHTS[k] for k in WEIGHTS) / 100.0

    if final_score >= 85:
        profile = "Power User - High Reputation"
    elif final_score >= 60:
        profile = "Stable User - Medium Reputation"
    elif final_score >= 30:
        profile = "Inactive/New User - Low Reputation"
    else:
        profile = "Low Trust / Risk-Exposed Wallet"

    return {
        "address": a,
        "status": "OK",
        "final_score": round(float(final_score), 2),
        "profile": profile,
        "indicators": indicators,
        "weights": WEIGHTS,
        "diagnostics": {
            "scam_counterparties_detected": tagged_scam_count,
            "scam_addresses_sample": tagged_sample,
            "tags_source": "etherscan_getaddresstag" if ETHERSCAN_API_KEY else "not_configured",
        },
    }