# backend/data_ingestion.py

import requests
import os
from dotenv import load_dotenv
import pandas as pd
import duckdb 

# Load environment variables from .env file
load_dotenv()
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

def get_wallet_transactions(address: str, chain: str = "mainnet") -> pd.DataFrame:
    """
    Fetches the normal transaction history for a given wallet address using the Etherscan API V2.
    
    Args:
        address: The wallet address (0x...)
        chain: The blockchain network (currently only supports 'mainnet')
    
    Returns:
        A pandas DataFrame with the transaction results.
    """
    if not ETHERSCAN_API_KEY:
        # Check if the API key was successfully loaded from .env
        raise ValueError("Etherscan API key is not configured in .env")

    # Etherscan URL for normal transaction history (V2 Endpoint)
    # The base URL is now /v2/api, and we must include chainid=1 for Ethereum Mainnet.
    url = (
        f"https://api.etherscan.io/v2/api?chainid=1&module=account&action=txlist&address={address}"
        f"&startblock=0&endblock=99999999&sort=asc&apikey={ETHERSCAN_API_KEY}"
    )
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise exception for HTTP error codes (e.g., 404, 500)
        data = response.json()
        
        # Check for successful API response (status '1' is the legacy success code still used here)
        if data.get('status') == '1' and data.get('result'):
            df = pd.DataFrame(data['result'])
            print(f"Success: Retrieved {len(df)} transactions for address {address}")
            return df
        # Handle the case where the status is 0/NOTOK but with a message (e.g., no transactions found)
        else:
            message = data.get('message', 'No message available')
            result_content = data.get('result', 'N/A')
            
            # If the result is an empty list, it means no transactions, which is not an error
            if result_content == 'No transactions found':
                 print(f"Info: No transactions found for address {address}.")
                 return pd.DataFrame()

            print(f"Etherscan API Error: {message} - Result: {result_content}")
            return pd.DataFrame()

    except requests.exceptions.RequestException as e:
        print(f"Connection Error: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return pd.DataFrame()

def save_to_db(df: pd.DataFrame, address: str):
    """
    Stores the transaction DataFrame into a DuckDB file for persistence and quick access.
    """
    db_path = "data/wallet_data.duckdb"
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True) 
    
    conn = duckdb.connect(database=db_path)
    # Create a unique table name based on the wallet address
    table_name = f"tx_{address}" 
    
    # Drop existing table to ensure fresh data for the address
    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    
    # Save the DataFrame (register it as a temporary view before creating the table)
    conn.register('temp_df', df)
    conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
    
    count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    print(f"Data saved to DuckDB: {count} records in table '{table_name}'")
    
    conn.close()

if __name__ == '__main__':
    # --- Test Configuration ---
    # The real Ethereum address to test with.
    TEST_WALLET_ADDRESS = "0xdadB0d80178819F2319190D340ce9A924f783711" 
    
    print(f"\n--- Testing data ingestion for {TEST_WALLET_ADDRESS} ---\n")
    
    # 1. Run Data Extraction
    transactions_df = get_wallet_transactions(TEST_WALLET_ADDRESS)
    
    # 2. Save to Database
    if not transactions_df.empty:
        save_to_db(transactions_df, TEST_WALLET_ADDRESS)
    else:
        print("Test failed: Check Etherscan key and connection.")
