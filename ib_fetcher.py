import backtrader as bt
import pandas as pd
from ib_insync import IB, util, Stock

from telegram_bot import send_telegram_message 

def fetch_recent_data(symbol, lookback_days=10):
    try:
        ib = IB()
        ib.connect('127.0.0.1', 7497, clientId=1)  # 确保 TWS 或 IB Gateway 已开启

        contract = Stock(symbol, 'SMART', 'USD')
        ib.qualifyContracts(contract)

        bars = ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr=f'{lookback_days} D',
            barSizeSetting='1 hour',
            whatToShow='TRADES',
            useRTH=False,
            formatDate=1
        )

        if not bars:
            print(f"No data for {symbol}")
            return None

        df = util.df(bars)
        df.set_index('date', inplace=True)
        df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)

        required_columns = ["Open", "High", "Low", "Close", "Volume"]
        if not set(required_columns).issubset(df.columns):
            print(f"Missing columns in {symbol}: {df.columns.tolist()}")
            return None

        df = df[required_columns]
        df.dropna(inplace=True)
        return df

    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

class CustomPandasData(bt.feeds.PandasData):
    params = (
        ('datetime', None),
        ('open', 'Open'),
        ('high', 'High'),
        ('low', 'Low'),
        ('close', 'Close'),
        ('volume', 'Volume'),
        ('openinterest', -1),
    )

def scan_stock(symbol):
    df = fetch_recent_data(symbol)
    if df is None:
        return False

    data = CustomPandasData(dataname=df)
    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.addstrategy(AttackReversalSignalScan, symbol=symbol)
    results = cerebro.run()
    return results[0].signal_today

def main():
    symbols = [
        'AAPL', 'MSFT', 'NVDA', 'META', 'AMZN', 'GOOGL', 'TSLA', 'NFLX', 'AMD', 'INTC'
    ]  

    alerted = []

    for symbol in symbols:
        if scan_stock(symbol):
            alerted.append(symbol)
            print(f"✅ Buy Signal: {symbol}")

    if alerted:
        message = "\n".join([f"📈 Buy Signal Detected: {sym}" for sym in alerted])
        send_telegram_message(f"[Stock Alert]\n{message}")
    else:
        print("No buy signals today.")
        send_telegram_message("No attack reversal signals today.")

if __name__ == "__main__":
    main()
