import pandas as pd
from datetime import datetime
from telegram_bot import send_telegram_message
from get_symbols import DIVIDEN_SYMBOLS
import os
 
def scan_dividend_window(window_days=8, today=None):
    
    print("Current working directory:", os.getcwd())
    if today is None:
        today = pd.to_datetime(datetime.today().date())
    else:
        today = pd.to_datetime(today)
 
    script_dir = os.path.dirname(os.path.abspath(__file__))  # 脚本所在目录
    csv_path = os.path.join(script_dir, "dividend_data.csv")

    df = pd.read_csv(csv_path, parse_dates=["dividend_date"])

    result = {}
    alert = False

    for symbol in DIVIDEN_SYMBOLS:
        ex_dates = df[df["symbol"] == symbol.upper()]["dividend_date"].sort_values()
        future_dates = ex_dates[ex_dates >= today]

        if future_dates.empty:
            result[symbol] = (False, None)
            continue

        next_ex = future_dates.iloc[0]

        # get future trade days (excluding weekends)
        trade_days = pd.bdate_range(end=next_ex - pd.Timedelta(days=1), periods=window_days)

        in_window = today in trade_days
        result[symbol] = (in_window, next_ex.date())
        if in_window: 
            message = f"[Dividen Alert] - {symbol} - The Day: {next_ex.strftime('%Y-%m-%d')}"
            print(message)
            send_telegram_message(message)
            alert = True
            
    if not alert:
        messgae = "No dividend signal today."
        print(messgae)
        send_telegram_message(messgae)

if __name__ == "__main__": 
    scan_dividend_window()
 