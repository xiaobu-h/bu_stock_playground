import yfinance as yf
import os
import pandas as pd

def fetch_yahoo_data(symbols, start="2025-01-01", end="2025-06-26", interval="1d", cache_dir="data"):
    os.makedirs(cache_dir, exist_ok=True)
    if isinstance(symbols, str):
        symbols = [symbols]

    data_dict = {}

    for symbol in symbols:
        file_path = os.path.join(cache_dir, f"{symbol}_{interval}_{start}_{end}.csv")

        if os.path.exists(file_path):
            df = pd.read_csv(file_path, index_col="Date", parse_dates=True)
        else:
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
                df.columns = df.columns.droplevel(0)
            df.columns.name = None

            if df.empty:
                print(f"⚠️ No data found for {symbol}")
                continue

            df.to_csv(file_path, index_label="Date")

        data_dict[symbol] = df

    return data_dict