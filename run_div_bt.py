import yfinance as yf
import pandas as pd
from get_symbols import DIVIDEN_SYMBOLS



# back test param
# 5000 USD per trade

x_days = 8  # buy 8 days before the dividend date
start_date = "2025-01-01"  # start date for the backtest 

all_records = []
total = 0
for symbol in DIVIDEN_SYMBOLS:
    ticker = yf.Ticker(symbol)
    try:
        div_dates = ticker.dividends.index
        hist = ticker.history(start=start_date)
    except Exception as e:
        print(f"{symbol} 数据加载失败: {e}")
        continue

    if div_dates.empty or hist.empty:
        continue

    for date in div_dates:
        if date not in hist.index:
            continue
        
        try:
            idx = hist.index.get_loc(date)
            if idx >= 9:
                buy_date = hist.index[idx - x_days].date()
                sell_date = hist.index[idx -1 ].date()
                entry_price = hist.iloc[idx - x_days]["Close"]
                
                number = 5000 / entry_price
                sell_price = hist.iloc[idx -1 ]["Close"]
                change = (sell_price *  number) - (entry_price * number)
                total += change
                all_records.append({
                    "Symbol": symbol,
                    "Buy_Date": buy_date,
                    "Sell_Date": sell_date,
                    "entry_price": round(entry_price, 2), 
                    "Sell_Price": round(sell_price, 2),
                    "Return ": round(change, 2)
                })
        except Exception as e:
            print(f"{symbol} 单次记录失败: {e}")
            continue

# 输出结果
df = pd.DataFrame(all_records)
df = df.sort_values(by=["Symbol", "Buy_Date"])
df.to_csv("dividend_returns.csv", index=False)
print(f"Total Return: {round(total, 2)}")
