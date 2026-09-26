
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from delta_rest_client import DeltaRestClient, OrderType, TimeInForce
from frvp import frvp_profile, previous_session_profile
from strategy import detect_poc_signal
from risk import position_size

st.set_page_config(page_title="FRVP POC • Delta V12", page_icon="📊", layout="wide")

st.title("FRVP POC • Delta Exchange V12")
st.caption("ONLY POC Bounce + POC Reversal • Previous completed session FRVP • Delta live feed")

with st.sidebar:
    st.header("Connection")
    mode = st.radio("Mode", ["Paper", "Live"], index=0)
    symbol = st.text_input("Delta product symbol", value="XAUUSD")
    timeframe = st.selectbox("Timeframe", ["5m", "15m"], index=0)
    rows = st.number_input("FRVP Row Size", 20, 200, 60, 5)
    va_pct = st.number_input("Value Area %", 50.0, 90.0, 70.0, 1.0)
    balance = st.number_input("Risk Balance ($)", 100.0, 1_000_000.0, 5000.0, 100.0)
    risk_pct = st.number_input("Risk / trade (%)", 0.1, 5.0, 0.5, 0.1)
    sl_buffer = st.number_input("SL Buffer", 0.0, 10.0, 0.20, 0.05)
    st.divider()
    st.warning("Live mode can place real orders. Keep Paper mode until the feed and signals are verified.")

api_key = st.secrets.get("DELTA_API_KEY", "")
api_secret = st.secrets.get("DELTA_API_SECRET", "")

client = DeltaClient(api_key, api_secret)

try:
    product = client.get_product(symbol)
except Exception as e:
    product = None
    st.error(f"Delta product lookup failed: {e}")

if not product:
    st.warning(
        f"Product **{symbol}** was not found from Delta's live product endpoint. "
        "Enter the exact symbol shown in your Delta Exchange India account. "
        "The app does not substitute Yahoo/GC=F."
    )
    st.info("The product list is discovered from Delta at runtime, so no hard-coded Yahoo symbol is used.")
    st.stop()

symbol = product["symbol"]
st.success(f"Connected to Delta product: {symbol}")

try:
    candles = client.get_candles(symbol, timeframe, limit=500)
except Exception as e:
    st.error(f"Could not load Delta candles: {e}")
    st.stop()

if candles.empty:
    st.warning("No candles returned by Delta.")
    st.stop()

levels = previous_session_profile(candles, rows=int(rows), va_pct=float(va_pct))
if levels is None:
    st.warning("Waiting for a completed previous session.")
    st.stop()

signal = detect_poc_signal(
    candles,
    levels,
    sl_buffer=float(sl_buffer),
    va_pct=float(va_pct),
)

last = candles.iloc[-1]
price = float(last["Close"])

c = st.columns(6)
c[0].metric("LIVE PRICE", f"{price:.2f}")
c[1].metric("POC", f"{levels['POC']:.2f}")
c[2].metric("VAH", f"{levels['VAH']:.2f}")
c[3].metric("VAL", f"{levels['VAL']:.2f}")
c[4].metric("MODE", mode.upper())
c[5].metric("RISK", f"${balance*risk_pct/100:.2f}")

if signal:
    risk = abs(signal["entry"] - signal["sl"])
    qty = position_size(balance, risk_pct, risk, product)
    st.subheader("🚨 SIGNAL")
    cols = st.columns(7)
    cols[0].metric("SETUP", signal["setup"])
    cols[1].metric("SIDE", signal["side"])
    cols[2].metric("ENTRY", f"{signal['entry']:.2f}")
    cols[3].metric("SL", f"{signal['sl']:.2f}")
    cols[4].metric("TP", f"{signal['tp']:.2f}")
    cols[5].metric("R:R", f"{signal['rr']:.2f}")
    cols[6].metric("SIZE", f"{qty:g}")

    if mode == "Live":
        st.error("LIVE MODE selected. This build intentionally requires explicit order confirmation below.")
        if st.button("CONFIRM & SEND ORDER", type="primary"):
            try:
                result = client.place_bracket_market_order(
                    symbol=symbol,
                    side=signal["side"],
                    size=qty,
                    stop_price=signal["sl"],
                    take_profit_price=signal["tp"],
                )
                st.success(f"Order response: {result}")
            except Exception as e:
                st.error(f"Order failed: {e}")
    else:
        st.info("Paper signal only — no Delta order will be sent.")
else:
    st.info("WAITING — no confirmed POC Bounce/Reversal on the latest completed candle.")

fig = go.Figure(go.Candlestick(
    x=candles.index, open=candles.Open, high=candles.High,
    low=candles.Low, close=candles.Close, name=symbol
))
fig.add_hline(y=levels["POC"], annotation_text="POC")
fig.add_hline(y=levels["VAH"], line_dash="dash", annotation_text="VAH")
fig.add_hline(y=levels["VAL"], line_dash="dash", annotation_text="VAL")
if signal:
    fig.add_hline(y=signal["entry"], line_dash="dot", annotation_text="ENTRY")
    fig.add_hline(y=signal["sl"], line_dash="dot", annotation_text="SL")
    fig.add_hline(y=signal["tp"], line_dash="dot", annotation_text="TP")
fig.update_layout(height=650, xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Fixed Previous-Session FRVP")
st.dataframe(pd.DataFrame([levels]).round(4), use_container_width=True, hide_index=True)

st.caption(
    "Delta market data is used directly. The app does not use Yahoo Finance. "
    "Live mode requires Delta API credentials in Streamlit Secrets and should be tested on paper/testnet first."
)
