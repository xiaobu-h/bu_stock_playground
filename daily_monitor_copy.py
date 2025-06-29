import backtrader as bt
import pandas as pd
import yfinance as yf
import logging

from get_symbols import FINAL_SYMBOLS  , NASDAQ100, TEST_SYMBOLS
from datetime import datetime
from telegram_bot import send_telegram_message 
from strategy.bl_jump_lower_open.stratety import BollingerVolumeBreakoutStrategy  
from strategy.bl_new_high_w_volumn.stratety import BollingerNewHighWithVolumeBreakoutStrategy

# logging
log_filename = datetime.now().strftime("bl_jump_monitor_%Y-%m-%d.log")
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


# fetcher
def fetch_recent_data(symbol, lookback_days=10):
    try:
        end_date = pd.Timestamp.today() + pd.Timedelta(days=1)
        start_date = end_date - pd.Timedelta(days=lookback_days + 30)  # load extra data to ensure we have enough for the strategy
        df = yf.download(symbol, start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), interval="1d", auto_adjust=False)

        if df.empty:
            logging.warning(f"No data for {symbol}")
            return None

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


# call scanner 
def scan_stock(symbol, strategy_class=BollingerVolumeBreakoutStrategy):
    df = fetch_recent_data(symbol)
    if df is None:
        return False

    data = CustomPandasData(dataname=df)
    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.addstrategy(strategy_class, symbol=symbol , only_scan_last_day=True)
    results = cerebro.run()
    return results[0].signal_today

def main():
    symbols = FINAL_SYMBOLS
    alerted = []
    
    for symbol in symbols: 
       logging.info(f"Scanning {symbol}...")
       if scan_stock(symbol,BollingerVolumeBreakoutStrategy):
            alerted.append(symbol)
            logging.info(f"✅ Buy Signal: {symbol}")

    if alerted:
        message = "\n".join([f"📈 Buy Signal Detected: {sym}" for sym in alerted])
        send_telegram_message(f"[Stock Alert - Bollinger Strategy]\n{message}")
    else:
        logging.info("No buy signals today.")
        send_telegram_message(f"[Stock Alert - Bollinger Low Jump Strategy] No signals today.")
        
        
        
    alerted = []  
    for symbol in symbols: 
        logging.info(f"Scanning {symbol}...")
        if scan_stock(symbol,BollingerNewHighWithVolumeBreakoutStrategy):
            alerted.append(symbol)
            logging.info(f"✅ Buy Signal: {symbol}")

    if alerted:
        message = "\n".join([f"📈 Buy Signal Detected: {sym}" for sym in alerted])
        send_telegram_message(f"[Stock Alert - Bollinger New High Strategy]\n{message}")
    else:
        logging.info("No buy signals today.")
        send_telegram_message(f"[Stock Alert - Bollinger New High Strategy] No signals today.")

if __name__ == "__main__":
    main()
