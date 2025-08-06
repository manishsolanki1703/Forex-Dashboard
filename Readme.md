# 📊 Forex Dashboard using Streamlit & MetaTrader 5

This project is a real-time **Forex trading dashboard** built with **Streamlit** and connected to **MetaTrader 5 (MT5)**. It allows you to simulate market and limit trades, track live forex prices, manage SL/TP levels, monitor equity, and visualize performance — all in an interactive web interface.

---

## 🚀 Features

- 📈 **Live Candlestick Chart** (using Plotly)
- 💹 **Market & Limit Order Simulation**
- 🔔 **MT5 Tick Monitor** (for SL/TP and time-based exits)
- 💰 **Real-time PnL and Equity Tracking**
- ✅ **Manual Trade Close Option**
- 🧮 **Stats: Win Rate, Avg Win/Loss, TP/SL Hits**
- 📤 **Export Trade Log as CSV**

---

## 🛠️ Tech Stack

- Python
- Streamlit
- MetaTrader5 (Python API)
- Plotly
- Pandas
- JSON for trade logging

---

## 📂 File Structure

```text
ForexDashboard/
│
├── Forex_dashboard.py    # Streamlit UI for dashboard
├── tick_monitor.py       # MT5 Tick monitor for SL/TP automation
└── live_trades.json      # (Auto-created trade log, ignored by Git)
