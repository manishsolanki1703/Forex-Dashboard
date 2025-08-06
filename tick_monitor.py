import MetaTrader5 as mt5
import time
import json
from datetime import datetime

TRADES_FILE = "live_trades.json"

# Initialize MT5
if not mt5.initialize():
    print("❌ MT5 initialization failed")
    quit()

print("✅ Tick Monitor Started")

def load_trades():
    try:
        with open(TRADES_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_trades(trades):
    with open(TRADES_FILE, "w") as f:
        json.dump(trades, f, indent=2, default=str)

def check_trade(trade):
    if trade['status'] != 'OPEN':
        return trade

    symbol = trade['symbol']
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return trade

    side = trade['side']
    current_price = tick.ask if side == 'BUY' else tick.bid
    trade['current_price'] = round(current_price, 5)

    # ✅ Handle LIMIT order trigger (tick-by-tick)
    if trade.get("order_type") == "LIMIT" and not trade.get("entry_triggered", False):
        if (side == 'BUY' and trade['current_price'] <= trade['entry_price']) or \
        (side == 'SELL' and trade['current_price'] >= trade['entry_price']):

            trade['entry_triggered'] = True
            trade['entry_time'] = str(datetime.now())
            print(f"🔔 LIMIT order triggered for {symbol} at {current_price}")
        else:
            return trade  # Not yet activated

    # ✅ Proceed only if Market order or LIMIT already triggered
    if trade.get("order_type") == "MARKET" or trade.get("entry_triggered", False):

        sl_hit = trade['stop_loss'] and (
            (side == 'BUY' and current_price <= trade['stop_loss']) or
            (side == 'SELL' and current_price >= trade['stop_loss'])
        )
        tp_hit = trade['take_profit'] and (
            (side == 'BUY' and current_price >= trade['take_profit']) or
            (side == 'SELL' and current_price <= trade['take_profit'])
        )

        time_exit_hit = False
        if trade.get('exit_time_limit'):
            try:
                time_limit = datetime.fromisoformat(trade['exit_time_limit'])
                if datetime.now() >= time_limit:
                    time_exit_hit = True
            except:
                pass

        if sl_hit:
            trade['status'] = 'CLOSED'
            trade['exit_price'] = trade['stop_loss']
            trade['exit_time'] = str(datetime.now())
        elif tp_hit:
            trade['status'] = 'CLOSED'
            trade['exit_price'] = trade['take_profit']
            trade['exit_time'] = str(datetime.now())
        elif time_exit_hit:
            trade['status'] = 'CLOSED'
            trade['exit_price'] = current_price
            trade['exit_time'] = str(datetime.now())

        if trade['status'] == 'CLOSED':
            entry = trade['entry_price']
            exit_ = trade['exit_price']
            lot = trade.get('lot_size', 1)
            pips = (exit_ - entry) if side == 'BUY' else (entry - exit_)
            trade['pnl'] = round(pips * lot * 100, 2)

    return trade

# ✅ Tick loop
while True:
    trades = load_trades()
    updated = [check_trade(t) for t in trades]
    save_trades(updated)
    time.sleep(1)
