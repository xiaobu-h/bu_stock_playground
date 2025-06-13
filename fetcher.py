import yfinance as yf
import os
import pandas as pd

def fetch_yahoo_data(symbol, start="2020-01-01", end="2025-01-01", interval="1d", cache_dir="data"):
    os.makedirs(cache_dir, exist_ok=True)
    file_path = os.path.join(cache_dir, f"{symbol}_{interval}_{start}_{end}.csv")

    if os.path.exists(file_path):
        print(f" Deleting old cache: {file_path}")
        os.remove(file_path)

    print(f"⬇️ Downloading data for {symbol} via yfinance")
    df = yf.download(
        symbol,
        start=start,
        end=end,
        interval=interval,
        progress=False,
        auto_adjust=False,
        group_by='ticker' 
    )

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(0)  # second tier of column ['Open', 'High', ...]

    df.columns.name = None

    if df.empty:
        raise ValueError(f"No data found for {symbol}.")

    df.to_csv(file_path, index_label="Date")
    return df