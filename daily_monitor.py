import backtrader as bt
import pandas as pd
import yfinance as yf
import logging

from telegram_bot import send_telegram_message 
from strategy.attack_day.scan import AttackReversalSignalScan  # 你定义的轻量策略

# 配置日志
logging.basicConfig(
    filename=f'monitor-{pd.Timestamp.today()}.log',
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def fetch_recent_data(symbol, lookback_days=10):
    try:
        end_date = pd.Timestamp.today() + pd.Timedelta(days=1)
        start_date = end_date - pd.Timedelta(days=lookback_days + 5)  # 多加载5天以初始化指标
        df = yf.download(symbol, start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), interval="1d", auto_adjust=False)

        if df.empty:
            logging.warning(f"No data for {symbol}")
            return None

        # ✅ 修复 MultiIndex 列名问题
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].capitalize() for col in df.columns]
        else:
            df.columns = [col.capitalize() for col in df.columns]

        required_columns = ["Open", "High", "Low", "Close", "Volume"]
        if not set(required_columns).issubset(df.columns):
            logging.warning(f"Missing columns in {symbol}: {df.columns.tolist()}")
            return None

        df = df[required_columns]
        df.dropna(inplace=True)
        return df
    except Exception as e:
        logging.warning(f"Error fetching data for {symbol}: {e}")
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
    sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(sp500_url)
    symbols = tables[0]["Symbol"].str.replace(".", "-", regex=False).tolist()

    alerted = []

    for symbol in symbols:
        print(f"Scanning {symbol}...")
        logging.info(f"Scanning {symbol}...")
        if scan_stock(symbol):
            alerted.append(symbol)
            logging.info(f"✅ Buy Signal: {symbol}")

    if alerted:
        message = "\n".join([f"📈 Buy Signal Detected: {sym}" for sym in alerted])
        send_telegram_message(f"[Stock Alert]\n{message}")
    else:
        logging.info("No buy signals today.")
        send_telegram_message(f"No attack reversal signals today.")

if __name__ == "__main__":
    main()
