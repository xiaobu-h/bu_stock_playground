import backtrader as bt
import pandas as pd
import yfinance as yf

from telegram_bot import send_telegram_message 
from strategy_attack_day_scan import AttackReversalSignalScan  # 你定义的轻量策略


def fetch_recent_data(symbol, lookback_days=10):
    try:
        df = yf.download(symbol, period=f"{lookback_days}d", interval="1d", progress=False, auto_adjust=False, group_by='ticker')
  
        if df.empty:
            return None
        df.columns = [str(col).capitalize() for col in df.columns]  # 标准化列名
        df.dropna(inplace=True)
        return df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

def scan_stock(symbol):
    df = fetch_recent_data(symbol)

    data = bt.feeds.PandasData(dataname=df)
    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.addstrategy(AttackReversalSignalScan, symbol=symbol)
    results = cerebro.run()
    return results[0].signal_today

def main():
    sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(sp500_url)
    symbols = tables[0]["Symbol"].str.replace(".", "-", regex=False).tolist()

    alerted = []

    for symbol in symbols[:10]:
        if scan_stock(symbol):
            alerted.append(symbol)
            print(f"✅ Buy Signal: {symbol}")

    if alerted:
        message = "\n".join([f"📈 Buy Signal Detected: {sym}" for sym in alerted])
        send_telegram_message(f"[Stock Alert]\n{message}")
    else:
        print("No buy signals today.")
        send_telegram_message(f"No attack reversal signals today.")

if __name__ == "__main__":
    main()
