# 🚀 Wallet Scoring System

**Design and implementation of an explainable reputation system for Web3 wallets based on on-chain data.**

This project constitutes a functional prototype (MVP) of a tool that analyzes and calculates the reputation and trustworthiness of a cryptocurrency address (wallet), based exclusively on its observable behavior within the Ethereum blockchain (on-chain data).

The system is designed to be **explainable, transparent, and reproducible**, using a model based on easily interpretable rules and weightings.

---

## ✨ Key Features and Indicators

The scoring system generates a **global score (0-100)** and assigns a qualitative profile, based on the evaluation of the following indicators, each with a configurable weight (the sum of weights is 100%):

* **Longevity Score:** Measures the age of the wallet (since its first transaction), correlating longevity with stability and continuity.
* **Activity Score:** Evaluates the quantity and regularity of transactions, as well as the operational volume, as a sign of authentic usage.
* **Diversity Score:** Quantifies the variety of protocols or tokens with which the wallet has interacted, suggesting experience and legitimate exploratory behavior.
* **Risk Score (General Risk):** Identifies interactions with contracts that have been identified as fraudulent or known scam addresses.
* **Asset Risk Score:** Evaluates the wallet's interaction with tokens or assets (ERC-20) flagged as high-risk (e.g., *privacy coins* or tokens associated with *mixers*). - (To be included)

---

## ⚙️ System Architecture

The project follows a modular data engineering and software development architecture, structured in three phases (ingestion, storage/processing, and scoring).

### Technologies

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | Python, FastAPI | Responsible for the business logic, data collection, and score calculation. |
| **Data Ingestion** | Etherscan API | Main source of public on-chain data (ETH and ERC-20 token transactions). |
| **Database** | DuckDB | Lightweight, serverless database used for temporary storage and normalization of extracted data. |

### Directory Structure

```bash
wallet-scoring-system/
├── backend/
│   ├── data_ingestion.py       # Ingestion from API and storage in DuckDB
│   ├── scoring_model.py        # Logic for calculating indicators and final score
│   └── main.py                 # FastAPI Endpoints and general orchestration
│
├── data/
│   └── wallet_data.duckdb      # Local database (ignored by Git)
│
├── .env                        # Environment variables (API Key, etc.) (ignored by Git)
└── requirements.txt            # Project dependencies
```

## 🛠️ Getting Started (Setup and Execution)

### Prerequisites

* Python 3.8+
* Etherscan API Key (required for `data_ingestion.py`).

...
