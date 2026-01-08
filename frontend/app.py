import re
import json
from datetime import datetime, timezone

import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Wallet Scoring System", page_icon="🧪", layout="wide")

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; padding-bottom: 1.2rem; }
      div[data-testid="stMetricValue"] { font-size: 1.8rem; }
      div[data-testid="stMetricLabel"] { opacity: 0.8; }
    </style>
    """,
    unsafe_allow_html=True,
)

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
ETH_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")

PRESETS = {
    "Blank": "",
    "Example (from thesis)": "0xdadB0d80178819F2319190D340ce9A924f783711",
}

INDICATOR_ORDER = [
    "Activity_Score",
    "Longevity_Score",
    "Diversity_Score",
    "General_Risk_Score",
    "Asset_Risk_Score",
]

if "api_base_url" not in st.session_state:
    st.session_state.api_base_url = DEFAULT_API_BASE_URL

if "history" not in st.session_state:
    st.session_state.history = []

if "last_payload_by_address" not in st.session_state:
    st.session_state.last_payload_by_address = {}


def is_valid_eth_address(addr: str) -> bool:
    return bool(addr and ETH_ADDRESS_RE.fullmatch(addr.strip()))


def now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def api_get_score(api_base: str, address: str) -> tuple[int, dict]:
    url = f"{api_base.rstrip('/')}/wallet/{address}/score"
    r = requests.get(url, timeout=90)
    try:
        data = r.json()
    except Exception:
        data = {"detail": r.text}
    return r.status_code, data


def radar_chart(indicators: dict) -> go.Figure:
    labels = INDICATOR_ORDER
    values = [float(indicators.get(k, 0)) for k in labels]
    labels_closed = labels + [labels[0]]
    values_closed = values + [values[0]]

    fig = go.Figure(
        data=[go.Scatterpolar(r=values_closed, theta=labels_closed, fill="toself")]
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        margin=dict(l=10, r=10, t=30, b=10),
        height=360,
    )
    return fig


def indicators_df(indicators: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [{"Indicator": k, "Score": float(indicators.get(k, 0))} for k in INDICATOR_ORDER]
    )


def weights_df(weights: dict) -> pd.DataFrame:
    order = {name: i for i, name in enumerate(INDICATOR_ORDER)}
    df = pd.DataFrame([{"Indicator": k, "Weight (%)": v} for k, v in weights.items()])
    df["__ord"] = df["Indicator"].map(order).fillna(999)
    return df.sort_values("__ord").drop(columns="__ord")


def history_to_dataframe(history_items: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Timestamp": item.get("ts"),
                "Address": item.get("address"),
                "Final Score": item.get("final_score"),
                "Profile": item.get("profile"),
            }
            for item in history_items
        ]
    )


def payloads_export_df(history_items: list[dict]) -> pd.DataFrame:
    rows = []
    for item in history_items:
        p = item.get("payload", {})
        ind = p.get("indicators", {}) if isinstance(p, dict) else {}
        row = {
            "timestamp": item.get("ts"),
            "address": item.get("address"),
            "final_score": item.get("final_score"),
            "profile": item.get("profile"),
        }
        for k in INDICATOR_ORDER:
            row[k] = ind.get(k)
        # include tag diagnostics if present
        diag = p.get("diagnostics", {}) if isinstance(p, dict) else {}
        row["scam_counterparties_detected"] = diag.get("scam_counterparties_detected")
        row["scam_addresses_sample"] = json.dumps(diag.get("scam_addresses_sample", []))
        rows.append(row)
    return pd.DataFrame(rows)


def upsert_history(payload: dict):
    addr = payload.get("address")
    if not addr:
        return
    st.session_state.history = [h for h in st.session_state.history if h.get("address") != addr]
    st.session_state.history.insert(
        0,
        {
            "address": addr,
            "ts": now_str(),
            "final_score": payload.get("final_score"),
            "profile": payload.get("profile"),
            "payload": payload,
        },
    )
    st.session_state.history = st.session_state.history[:20]


with st.sidebar:
    st.markdown("## Wallet Scoring System")
    st.caption("Streamlit frontend for the FastAPI MVP")

    st.markdown("### Backend")
    api_base = st.text_input("API Base URL", value=st.session_state.api_base_url)
    st.session_state.api_base_url = api_base.strip() or DEFAULT_API_BASE_URL

    st.markdown("### Presets")
    preset_keys = list(PRESETS.keys())
    blank_index = preset_keys.index("Blank")
    preset_name = st.selectbox("Pick a preset", preset_keys, index=blank_index)
    preset_address = PRESETS[preset_name]

    st.markdown("### History")
    if st.session_state.history:
        recent = [h["address"] for h in st.session_state.history[:8]]
        selected_recent = st.selectbox("Open a recent wallet", [""] + recent)
    else:
        selected_recent = ""

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("Clear history", width='stretch'):
            st.session_state.history = []
            st.session_state.last_payload_by_address = {}
            st.rerun()

    with col_s2:
        show_debug = st.toggle("Show raw JSON", value=False)

st.markdown("## 🧪 Wallet Scoring")
st.caption("Explainable on-chain reputation score (Activity, Longevity, Diversity, General Risk, Asset Risk).")

left, mid, right = st.columns([2.2, 1.2, 1])
default_addr = selected_recent or preset_address

with left:
    address = st.text_input("Ethereum address (0x...)", value=default_addr, placeholder="0x...").strip()

with mid:
    use_cache = st.toggle("Use session cache", value=True)

with right:
    run = st.button("Calculate", type="primary", width='stretch')

payload = None

if run:
    if not is_valid_eth_address(address):
        st.error("Invalid Ethereum address. Please paste a valid `0x...` address.")
        st.stop()

    if use_cache and address.lower() in st.session_state.last_payload_by_address:
        payload = st.session_state.last_payload_by_address[address.lower()]
    else:
        with st.spinner("Fetching data + computing score…"):
            status_code, data = api_get_score(st.session_state.api_base_url, address)

        if status_code == 200:
            payload = data
            st.session_state.last_payload_by_address[address.lower()] = payload
        elif status_code == 404:
            st.warning(data.get("detail", "No transactions found for this address."))
            st.stop()
        else:
            st.error(f"API error ({status_code}): {data.get('detail', data)}")
            st.stop()

    if payload:
        upsert_history(payload)

if payload is None and st.session_state.history:
    payload = st.session_state.history[0]["payload"]

if payload:
    final_score = payload.get("final_score", 0)
    profile = payload.get("profile", "N/A")
    addr = payload.get("address", address)
    indicators = payload.get("indicators", {}) or {}
    weights = payload.get("weights", {}) or {}
    diagnostics = payload.get("diagnostics", {}) or {}

    c1, c2, c3, c4 = st.columns([1, 1.3, 2.2, 1.2])
    c1.metric("Final Score", f"{final_score} / 100")
    c2.metric("Profile", profile)
    c3.metric("Address", addr)
    c4.metric("Updated", st.session_state.history[0]["ts"] if st.session_state.history else now_str())

    st.divider()

    colA, colB = st.columns([1.1, 1])

    with colA:
        st.markdown("### Indicator Radar")
        st.plotly_chart(radar_chart(indicators), width='stretch')

        st.markdown("### Indicator Breakdown")
        st.dataframe(indicators_df(indicators), width='stretch', hide_index=True)

    with colB:
        st.markdown("### Weights")
        st.dataframe(weights_df(weights), width='stretch', hide_index=True)

        st.markdown("### Scam/Tag diagnostics (Etherscan labels)")
        if diagnostics:
            st.metric("Scam counterparties detected", diagnostics.get("scam_counterparties_detected", 0))
            sample = diagnostics.get("scam_addresses_sample", [])
            if sample:
                st.write("Sample tagged addresses:")
                st.code("\n".join(sample))
            else:
                st.caption("No tagged scam addresses returned (or tags API unavailable).")
        else:
            st.caption("No diagnostics available. (Backend must return a 'diagnostics' field.)")

        if show_debug:
            st.markdown("### Raw JSON")
            st.json(payload)

    st.divider()

    st.markdown("## Recent Queries")
    if st.session_state.history:
        st.dataframe(history_to_dataframe(st.session_state.history), width='stretch', hide_index=True)

        export_df = payloads_export_df(st.session_state.history)
        export_col1, export_col2, export_col3 = st.columns([1, 1, 2])

        with export_col1:
            st.download_button(
                "Download CSV",
                data=export_df.to_csv(index=False).encode("utf-8"),
                file_name="wallet_scoring_history.csv",
                mime="text/csv",
                width='stretch',
            )
        with export_col2:
            st.download_button(
                "Download JSON",
                data=json.dumps([h["payload"] for h in st.session_state.history], indent=2).encode("utf-8"),
                file_name="wallet_scoring_history.json",
                mime="application/json",
                width='stretch',
            )
        with export_col3:
            st.caption("Exports include final score + indicator columns + basic tag diagnostics.")