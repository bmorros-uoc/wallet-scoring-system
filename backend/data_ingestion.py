# backend/data_ingestion.py

import os
import re
import requests
import pandas as pd
import duckdb
from dotenv import load_dotenv

load_dotenv()
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")


def normalize_address(address: str) -> str:
    a = (address or "").strip().lower()
    if not re.fullmatch(r"0x[a-f0-9]{40}", a):
        raise ValueError("Invalid Ethereum address format")
    return a


def table_name(address: str, table_kind: str) -> str:
    """
    Safe DuckDB identifier: tx_<hex> or erc20_<hex>
    """
    a = normalize_address(address)
    suffix = a[2:]  # drop 0x
    if table_kind not in {"tx", "erc20"}:
        raise ValueError("table_kind must be 'tx' or 'erc20'")
    return f"{table_kind}_{suffix}"


def _etherscan_get(url: str) -> dict:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def get_wallet_transactions(address: str) -> pd.DataFrame:
    """
    Normal transactions via Etherscan V2:
    module=account&action=txlist
    """
    a = normalize_address(address)

    if not ETHERSCAN_API_KEY:
        raise ValueError("Etherscan API key is not configured in .env")

    url = (
        f"https://api.etherscan.io/v2/api"
        f"?chainid=1&module=account&action=txlist&address={a}"
        f"&startblock=0&endblock=99999999&sort=asc&apikey={ETHERSCAN_API_KEY}"
    )

    try:
        data = _etherscan_get(url)

        if data.get("status") == "1" and data.get("result"):
            df = pd.DataFrame(data["result"])
            print(f"Success: Retrieved {len(df)} normal transactions for {a}")
            return df

        result_content = data.get("result", "N/A")
        if result_content == "No transactions found":
            print(f"Info: No normal transactions found for {a}")
            return pd.DataFrame()

        print(f"Etherscan API Error (txlist): {data.get('message')} - Result: {result_content}")
        return pd.DataFrame()

    except Exception as e:
        print(f"Error fetching txlist: {e}")
        return pd.DataFrame()


def get_wallet_erc20_transfers(address: str) -> pd.DataFrame:
    """
    ERC-20 token transfers via Etherscan V2:
    module=account&action=tokentx
    """
    a = normalize_address(address)

    if not ETHERSCAN_API_KEY:
        raise ValueError("Etherscan API key is not configured in .env")

    url = (
        f"https://api.etherscan.io/v2/api"
        f"?chainid=1&module=account&action=tokentx&address={a}"
        f"&startblock=0&endblock=99999999&sort=asc&apikey={ETHERSCAN_API_KEY}"
    )

    try:
        data = _etherscan_get(url)

        if data.get("status") == "1" and data.get("result"):
            df = pd.DataFrame(data["result"])
            print(f"Success: Retrieved {len(df)} ERC-20 transfers for {a}")
            return df

        result_content = data.get("result", "N/A")
        if result_content == "No transactions found":
            print(f"Info: No ERC-20 transfers found for {a}")
            return pd.DataFrame()

        # Some cases return status=0 with message=NOTOK but meaning "no data"
        print(f"Etherscan API Info (tokentx): {data.get('message')} - Result: {result_content}")
        return pd.DataFrame()

    except Exception as e:
        print(f"Error fetching tokentx: {e}")
        return pd.DataFrame()


def save_to_db(df: pd.DataFrame, address: str, table_kind: str):
    """
    Stores DataFrame into DuckDB under a safe table name:
    tx_<address> or erc20_<address>
    """
    db_path = "data/wallet_data.duckdb"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    tname = table_name(address, table_kind)

    conn = duckdb.connect(database=db_path)
    conn.execute(f"DROP TABLE IF EXISTS {tname}")

    # Ensure we always create a table (even if empty) with consistent schema:
    if df is None or df.empty:
        conn.execute(f"CREATE TABLE {tname} AS SELECT 1 AS empty_flag WHERE 1=0")
        print(f"Data saved to DuckDB: 0 records in table '{tname}' (empty)")
        conn.close()
        return

    conn.register("temp_df", df)
    conn.execute(f"CREATE TABLE {tname} AS SELECT * FROM temp_df")

    count = conn.execute(f"SELECT COUNT(*) FROM {tname}").fetchone()[0]
    print(f"Data saved to DuckDB: {count} records in table '{tname}'")
    conn.close()


if __name__ == "__main__":
    TEST_WALLET_ADDRESS = "0xdadB0d80178819F2319190D340ce9A924f783711"

    tx = get_wallet_transactions(TEST_WALLET_ADDRESS)
    erc20 = get_wallet_erc20_transfers(TEST_WALLET_ADDRESS)

    if not tx.empty:
        save_to_db(tx, TEST_WALLET_ADDRESS, "tx")
        save_to_db(erc20, TEST_WALLET_ADDRESS, "erc20")
    else:
        print("Test failed: no normal txs or API issue.")