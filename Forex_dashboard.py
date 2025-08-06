import streamlit as st
import pandas as pd
import MetaTrader5 as mt5
import time
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os

st.set_page_config(page_title="Forex Market Dashboard", layout="wide")
st.title("Live Forex Dashboard (MT5)")

# ----------------- CONFIG ------------------ #
SYMBOLS = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
TRADES_FILE = "live_trades.json"
STARTING_BALANCE = 100000
REFRESH_INTERVAL = 5  # seconds

# ----------------- INIT MT5 ------------------ #
if not mt5.initialize():
    st.error("Failed to initialize MT5. Make sure MetaTrader 5 is open and logged in.")
    st.stop()
else:
    account_info = mt5.account_info()
    if account_info is None:
        st.warning("MT5 is initialized but not connected to a valid account.")
    else:
        st.success(f"Connected to account: {account_info.login} ({account_info.name})")

# ----------------- UTILS ------------------ #
def load_trades():
    if not os.path.exists(TRADES_FILE):
        return []
    with open(TRADES_FILE, "r") as f:
        return json.load(f)

def save_trades(trades):
    with open(TRADES_FILE, "w") as f:
        json.dump(trades, f, indent=2, default=str)

# ----------------- MINI CHART VIEWER ------------------ #
def load_candles(symbol, timeframe=mt5.TIMEFRAME_M5, bars=100):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def plot_candlestick(df, symbol):
    fig = go.Figure(data=[go.Candlestick(
        x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name=symbol
    )])
    fig.update_layout(title=f"Candlestick - {symbol}", xaxis_rangeslider_visible=False, height=400)
    return fig

# ----------------- TRADE SIMULATOR ------------------ #
def simulate_trade(symbol, side, entry_type, price, sl_diff, tp_diff, lot_size, duration_minutes=None):
    if entry_type == 'MARKET':
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            st.error("Tick data not available.")
            return
        price = tick.ask if side == 'BUY' else tick.bid

    sl = price - sl_diff if side == 'BUY' else price + sl_diff
    tp = price + tp_diff if side == 'BUY' else price - tp_diff
    exit_time_limit = datetime.now() + timedelta(minutes=duration_minutes) if duration_minutes else None

    trade = {
        'symbol': symbol,
        'side': side,
        'order_type': entry_type,
        'entry_triggered': False if entry_type == 'LIMIT' else True,
        'entry_price': round(price, 5),
        'stop_loss': round(sl, 5),
        'take_profit': round(tp, 5),
        'lot_size': lot_size,
        'time': str(datetime.now()),
        'exit_time_limit': str(exit_time_limit) if exit_time_limit else None,
        'status': 'OPEN',
        'exit_time': None,
        'exit_price': None,
        'pnl': 0.0,
        'current_price': price
    }

    trades = load_trades()
    trades.append(trade)
    save_trades(trades)
    st.success(f"Simulated {side} {entry_type} trade on {symbol} @ {price} | SL: {sl}, TP: {tp} | Lot: {lot_size}")

# ----------------- UI ------------------ #
symbol_selected = st.selectbox("Select symbol", SYMBOLS)

# ----------------- MINI CHART ------------------ #
st.subheader(f"Mini Chart: {symbol_selected}")
chart_data = load_candles(symbol_selected)
if chart_data is not None:
    chart = plot_candlestick(chart_data, symbol_selected)
    st.plotly_chart(chart, use_container_width=True)
else:
    st.warning("No candle data available.")

# ----------------- MARKET DATA ------------------ #
st.subheader("Live Quotes")
data_placeholder = st.empty()
def get_market_data():
    data = []
    for symbol in SYMBOLS:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            data.append({"Symbol": symbol, "Bid": "-", "Ask": "-", "Spread (pips)": "-", "Last": "-", "Time": "-"})
            continue
        spread = (tick.ask - tick.bid) * 10000
        data.append({
            "Symbol": symbol,
            "Bid": round(tick.bid, 5),
            "Ask": round(tick.ask, 5),
            "Spread (pips)": round(spread, 2),
            "Last": round(tick.last, 5),
            "Time": pd.to_datetime(tick.time, unit='s')
        })
    return pd.DataFrame(data)

data = get_market_data()
data_placeholder.dataframe(data, use_container_width=True)

# ----------------- TRADE INPUTS ------------------ #
st.subheader("New Trade")
entry_type = st.selectbox("Order Type", ["MARKET", "LIMIT"])
limit_price = st.number_input("Limit Order Price (Only if LIMIT order)", min_value=0.0, value=0.0) if entry_type == "LIMIT" else 0.0
sl_diff = st.number_input("Stop Loss difference (from entry)", min_value=0.0, step=0.1)
tp_diff = st.number_input("Take Profit difference (from entry)", min_value=0.0, step=0.1)
lot_size = st.number_input("Lot Size", min_value=0.01, step=0.01, value=1.0)
duration_minutes = st.number_input("Time-based Exit (minutes, optional)", min_value=0, step=1, value=0)

col1, col2 = st.columns(2)
with col1:
    if st.button(f"Simulate Buy {symbol_selected}"):
        simulate_trade(symbol_selected, "BUY", entry_type, limit_price, sl_diff, tp_diff, lot_size, duration_minutes if duration_minutes > 0 else None)
with col2:
    if st.button(f"Simulate Sell {symbol_selected}"):
        simulate_trade(symbol_selected, "SELL", entry_type, limit_price, sl_diff, tp_diff, lot_size, duration_minutes if duration_minutes > 0 else None)

# ----------------- UPDATE TRADES ------------------ #
trades = load_trades()
for trade in trades:
    if trade['status'] == 'OPEN':
        tick = mt5.symbol_info_tick(trade['symbol'])
        if tick:
            current_price = tick.ask if trade['side'] == 'BUY' else tick.bid
            trade['current_price'] = round(current_price, 5)

            if trade.get('entry_triggered', True):
                pips = (current_price - trade['entry_price']) if trade['side'] == 'BUY' else (trade['entry_price'] - current_price)
                trade['pnl'] = round(pips * trade.get('lot_size', 1) * 100, 2)
            else:
                trade['pnl'] = 0.0

save_trades(trades)
# ----------------- STATS ------------------ #
df_log = pd.DataFrame(trades)

if not df_log.empty and all(col in df_log.columns for col in ['status', 'pnl']):
    closed = df_log[df_log['status'] == 'CLOSED']
    total_pnl = closed['pnl'].sum()
    win_rate = (closed['pnl'] > 0).mean() * 100
    avg_win = closed[closed['pnl'] > 0]['pnl'].mean()
    avg_loss = closed[closed['pnl'] < 0]['pnl'].mean()
    df_log['equity'] = STARTING_BALANCE + df_log['pnl'].cumsum()
else:
    closed = pd.DataFrame()
    total_pnl = 0
    win_rate = 0
    avg_win = 0
    avg_loss = 0
    df_log['equity'] = STARTING_BALANCE

st.subheader("Performance Summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total PnL", f"${total_pnl:.2f}")
col2.metric("Win Rate", f"{win_rate:.2f}%")
col3.metric("Avg Win", f"{avg_win:.2f}")
col4.metric("Avg Loss", f"{avg_loss:.2f}")

st.subheader("Equity Curve")
equity_fig = go.Figure()
equity_fig.add_trace(go.Scatter(x=df_log['time'], y=df_log['equity'], mode='lines+markers', name='Equity'))
equity_fig.update_layout(height=400, xaxis_title="Time", yaxis_title="Equity ($)")
st.plotly_chart(equity_fig, use_container_width=True)

# ----------------- TRADE FILTERS ------------------ #
st.subheader("🔍 Filter Trades")
filter_status = st.selectbox("Filter by Status", ["All", "OPEN", "CLOSED"])
filter_side = st.selectbox("Filter by Side", ["All", "BUY", "SELL"])
filter_symbol = st.selectbox("Filter by Symbol", ["All"] + SYMBOLS)

filtered_df = df_log.copy()
if filter_status != "All":
    filtered_df = filtered_df[filtered_df['status'] == filter_status]
if filter_side != "All":
    filtered_df = filtered_df[filtered_df['side'] == filter_side]
if filter_symbol != "All":
    filtered_df = filtered_df[filtered_df['symbol'] == filter_symbol]

# ----------------- SESSION SUMMARY ------------------ #
st.subheader("📊 Session Summary")
today = datetime.now().date()
today_trades = df_log[df_log['time'].apply(lambda x: pd.to_datetime(x).date() == today if isinstance(x, str) else False)]

count_today = len(today_trades)
tp_hits = today_trades[(today_trades['status'] == 'CLOSED') & (today_trades['exit_price'] == today_trades['take_profit'])].shape[0]
sl_hits = today_trades[(today_trades['status'] == 'CLOSED') & (today_trades['exit_price'] == today_trades['stop_loss'])].shape[0]

col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("📅 Date", str(today))
col_b.metric("📌 Trades Today", count_today)
col_c.metric("✅ TP Hit", tp_hits)
col_d.metric("🛑 SL Hit", sl_hits)

st.sidebar.markdown(f"### 🕒 {datetime.now().strftime('%H:%M:%S')}")

# ----------------- MODIFY SL/TP ------------------ #
open_trades_indices = [i for i, t in enumerate(trades) if t['status'] == 'OPEN']
if open_trades_indices:
    st.subheader("✏️ Modify SL/TP for Open Trades")
    options = [f"{i}. {t['symbol']} {t['side']} @ {t['entry_price']}" for i, t in enumerate(trades) if t['status'] == 'OPEN']
    selected = st.selectbox("Select trade to modify", options)
    idx = int(selected.split('.')[0])

    new_sl = st.number_input("New Stop Loss", value=trades[idx]['stop_loss'], key="mod_sl")
    new_tp = st.number_input("New Take Profit", value=trades[idx]['take_profit'], key="mod_tp")

    if st.button("Update SL/TP"):
        trades[idx]['stop_loss'] = round(new_sl, 5)
        trades[idx]['take_profit'] = round(new_tp, 5)
        save_trades(trades)
        st.success("SL/TP updated successfully!")

# ----------------- MODIFY LIMIT PRICE ------------------ #
limit_pending = [i for i, t in enumerate(trades) if t['status'] == 'OPEN' and t.get('order_type') == 'LIMIT' and not t.get('entry_triggered', True)]
if limit_pending:
    st.subheader("📝 Modify Limit Price (Untriggered Orders Only)")
    options = [f"{i}. {t['symbol']} {t['side']} @ {t['entry_price']}" for i, t in enumerate(trades) if i in limit_pending]
    selected = st.selectbox("Select limit order to modify", options, key="mod_limit_selector")
    idx = int(selected.split('.')[0])

    new_price = st.number_input("New Limit Entry Price", value=trades[idx]['entry_price'], key="mod_limit_price")

    if st.button("Update Limit Price"):
        trades[idx]['entry_price'] = round(new_price, 5)
        save_trades(trades)
        st.success("Limit price updated successfully!")

# ----------------- TRADE LOG ------------------ #
st.subheader("Trade Log")
st.dataframe(filtered_df, use_container_width=True)

# ----------------- EXPORT ------------------ #
csv = df_log.to_csv(index=False).encode('utf-8', errors='ignore')
st.download_button(
    label="Download Trade Log as CSV",
    data=csv,
    file_name='simulated_trades.csv',
    mime='text/csv',
)

# ----------------- MANUAL EXIT ------------------ #
open_trades = [f"{i}. {t['symbol']} {t['side']} @ {t['entry_price']}" for i, t in enumerate(trades) if t['status'] == 'OPEN']
if open_trades:
    st.subheader("Manually Close Trade")
    trade_to_close = st.selectbox("Select trade to close", options=open_trades, index=0)
    if st.button("Close Selected Trade"):
        index = int(trade_to_close.split(".")[0])
        selected_trade = trades[index]
        tick = mt5.symbol_info_tick(selected_trade['symbol'])
        if tick:
            exit_price = tick.bid if selected_trade['side'] == 'SELL' else tick.ask
            trades[index]['status'] = 'CLOSED'
            trades[index]['exit_price'] = round(exit_price, 5)
            trades[index]['exit_time'] = str(datetime.now())
            trades[index]['current_price'] = round(exit_price, 5)
            if trades[index]['pnl'] == 0.0 and selected_trade.get('entry_triggered', True):
                pips = (exit_price - selected_trade['entry_price']) if selected_trade['side'] == 'BUY' else (selected_trade['entry_price'] - exit_price)
                trades[index]['pnl'] = round(pips * selected_trade.get('lot_size', 1) * 100, 2)
            else:
                trades[index]['pnl'] = 0.0  # No trade execution happened, so no PnL
            save_trades(trades)
            st.success(f"Trade {selected_trade['symbol']} closed manually at {exit_price}")
