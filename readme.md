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
* **Asset Risk Score:** Evaluates the wallet's interaction with tokens or assets (ERC-20) flagged as high-risk (e.g., privacy coins or tokens associated with mixers).

---

## ⚙️ System Architecture

The project follows a modular data engineering and software development architecture, structured in three phases (ingestion, storage/processing, and scoring).

### Technologies

| Component | Technology | Purpose |
| --- | --- | --- |
| Backend | Python, FastAPI | Business logic, data collection, and score calculation |
| Data Ingestion | Etherscan API | Source of public on-chain data |
| Database | DuckDB | Lightweight local storage |
| Frontend | Streamlit | Interactive visualization and exploration |

### Directory Structure

```bash
wallet-scoring-system/
├── backend/
│   ├── data_ingestion.py
│   ├── scoring_model.py
│   └── main.py
├── frontend/
│   └── app.py
├── data/
│   └── wallet_data.duckdb
├── .env
└── requirements.txt
```

---

## 🛠️ Getting Started (Setup and Execution)

### Prerequisites

* Python 3.8+
* pip
* Etherscan API Key

---

### Clone the repository

```bash
git clone https://github.com/<your-username>/wallet-scoring-system.git
cd wallet-scoring-system
```

### Create virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment variables

Create a `.env` file:

```env
ETHERSCAN_API_KEY=YOUR_ETHERSCAN_API_KEY
```

---

## ▶️ Running the Backend

```bash
uvicorn backend.main:app --reload
```

Endpoint example:

```
GET /wallet/{address}/score
```

---

## 🖥️ Running the Frontend

```bash
streamlit run frontend/app.py
```

Open browser at:

```
http://localhost:8501
```

---

## ⚖️ Indicator Weights

| Indicator | Weight |
|---------|--------|
| Activity Score | 25% |
| Longevity Score | 20% |
| Diversity Score | 25% |
| General Risk Score | 25% |
| Asset Risk Score | 5% |

---

## 🚧 Limitations

Address tags and scam labels from Etherscan require a paid (Pro) API tier.  
The MVP includes the logic to consume these tags when available, but gracefully degrades when they are not accessible.

---

## 🎯 Intended Use

Academic research, education, and experimentation with explainable Web3 reputation models.

---

## 📌 Final Notes

This project demonstrates that meaningful and explainable reputation signals can be derived exclusively from public on-chain data.
