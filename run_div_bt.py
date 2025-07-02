import yfinance as yf
import pandas as pd

symbols = ["XOM", "CVX",  "KO", "JNJ", "IBM", "PRU"  , "PNC"  , "ENB" , "ET" , "GILD" , "MOH"]
all_records = []
total = 0
for symbol in symbols:
    ticker = yf.Ticker(symbol)
    try:
        div_dates = ticker.dividends.index
        hist = ticker.history(start="2024-01-01")
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
            if idx >= 6:
                buy_date = hist.index[idx - 8].date()
                sell_date = hist.index[idx -1 ].date()
                buy_price = hist.iloc[idx - 8]["Close"]
                sell_price = hist.iloc[idx -1 ]["Close"]
                pct_change = (sell_price - buy_price) / buy_price * 100
                total += pct_change
                all_records.append({
                    "Symbol": symbol,
                    "Buy_Date": buy_date,
                    "Sell_Date": sell_date,
                    "Buy_Price": round(buy_price, 2),
                    "Sell_Price": round(sell_price, 2),
                    "Return (%)": round(pct_change, 2)
                })
        except Exception as e:
            print(f"{symbol} 单次记录失败: {e}")
            continue

# 输出结果
df = pd.DataFrame(all_records)
df = df.sort_values(by=["Symbol", "Buy_Date"])
df.to_csv("dividend_returns.csv", index=False)
print(f"Total Return: {round(total, 2)}%")
