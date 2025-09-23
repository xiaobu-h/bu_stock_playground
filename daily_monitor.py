import backtrader as bt
import pandas as pd
import yfinance as yf
import logging
import datetime
import pandas_market_calendars as mcal
import os

from ib_fetcher import fetch_data_from_ibkr,download_daily_last_3_months, ib_connect,ib_disconnect

from get_symbols import FINAL_SYMBOLS  , NASDAQ100, TEST_SYMBOLS
from datetime import datetime
from telegram_bot import send_telegram_message 
from strategy.bl_jump_lower_open.bl_jump_strategy import BollingerVolumeBreakoutStrategy   
from strategy.attack_day.attack_day_strategy import AttackReversalStrategy
from strategy.attack_day.sensitive_param import  TAKE_PROFIT_PERCENT as TAKE_PROFIT_ATTACK
from strategy.breakout_volume.sensitive_param import  TAKE_PROFIT_PERCENT_LARGE, TAKE_PROFIT_PERCENT_SMALL
from strategy.bl_jump_lower_open.sensitive_param import TAKE_PROFIT_PERCENT as TAKE_PROFIT_BOLLINGER

from strategy.breakout_volume.simple_volume_strategy import SimpleVolumeStrategy
 

# logging
log_filename = datetime.now().strftime("monitor_log_%Y-%m-%d.log")
if os.path.exists(log_filename):
    os.remove(log_filename)
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ==========================================
ONLY_SCAN_LAST_DAY = False 

SEND_MESSAGE = False

CONNECT_N_DOWNLOAD = True 

# ==========================================
    
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
def scan_stock(symbol, df, strategy_class=BollingerVolumeBreakoutStrategy ):
    data = CustomPandasData(dataname=df)
    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.addstrategy(strategy_class, symbol=symbol , only_scan_last_day=ONLY_SCAN_LAST_DAY)    # ONLY Scan Last Day
   
    results = cerebro.run() 
    return results[0].signal_today

def main():
    #if not is_trading_day():
    #    is_weekend =  datetime.today().weekday() >=  5
     #   send_telegram_message("Enjoy the weekend! :)" if is_weekend else "Enjoy the holiday!! :)")
    #    return
    
    symbols = FINAL_SYMBOLS
    alert = False
    messages = []
    
    ib = ib_connect() if CONNECT_N_DOWNLOAD else None
    for symbol in symbols: 
        df = download_daily_last_3_months(symbol = symbol, ib = ib, end="", is_connect_n_download= CONNECT_N_DOWNLOAD)
        if df is None:
            continue 
    
        logging.info(f"Scanning {symbol}...")
        
        #try: 
        if scan_stock(symbol,df, SimpleVolumeStrategy ):
            alert = True 
            #msg = f"Buy Signal [Vol x 2]: {symbol} - take profit: {(TAKE_PROFIT_PERCENT_SMALL -1 )*100:.1f}% or {(TAKE_PROFIT_PERCENT_LARGE -1)*100:.1f}% "
           # messages.append(msg) 
        #except Exception as e:
        #    logging.warning(f"Error Scanning [Vol x 2] for {symbol}: {e}")
        
        try:           
            if scan_stock(symbol, df, AttackReversalStrategy):
                alert = True 
                #msg = f"Buy Signal [Attack Day]: {symbol} - take profit: {(TAKE_PROFIT_ATTACK - 1)*100:.1f}%"
               # messages.append(msg) 
        except Exception as e:
            logging.warning(f"Error Scanning [Attack Day] for {symbol}: {e}")
        
        
        #try:  
        if scan_stock(symbol,df, BollingerVolumeBreakoutStrategy):
            alert = True 
            #msg = f"Buy Signal [Bollinger Low Jump]: {symbol} - take profit: {(TAKE_PROFIT_BOLLINGER - 1)*100:.1f}%"
            # messages.append(msg)
       # except Exception as e:
          #  logging.warning(f"Error Scanning [Bollinger Low Jump] for {symbol}: {e}")
               
    if CONNECT_N_DOWNLOAD:
        ib_disconnect(ib)
    if SEND_MESSAGE:    # send summary only when scanning last day
        if alert: 
            final_message = "\n".join(messages)
            send_telegram_message(f"[Stock Alert]\n{final_message}")
        else:
            logging.info("No buy signals today.")
            send_telegram_message(f"No signals today.")
     
       
 
 

def is_trading_day():
    
    nyse = mcal.get_calendar('NYSE')
    today = datetime.today()
    schedule = nyse.valid_days(start_date=today.date(), end_date=today.date())
    return not schedule.empty 
    
    
if __name__ == "__main__":
    main()
