# -*- coding: utf-8 -*-
from datetime import datetime
import math
import pandas as pd
from ib_insync import IB, Stock, util
import os
import time

_IB_HOST = "127.0.0.1"
_IB_PORT = 7497
_IB_CLIENT_ID = 33

_INTERVAL_TO_BARSIZE = {
    "1min":  "1 min",
    "5min":  "5 mins",
    "15min": "15 mins",
    "30min": "30 mins",
    "1h":    "1 hour",
    "1hour": "1 hour",
    "1d":    "1 day",
    "1day":  "1 day",
}

def _choose_duration_str(start_dt: datetime, end_dt: datetime, bar_size: str) -> str:
    if end_dt <= start_dt:
        raise ValueError("end 必须晚于 start")
    total_days = (end_dt - start_dt).total_seconds() / 86400.0
    if bar_size in ("1 min", "5 mins", "15 mins", "30 mins"):
        if total_days <= 1:
            return f"{max(1, int(math.ceil(total_days)))} D"
        elif total_days <= 14:
            return f"{int(math.ceil(total_days/7))} W"
        elif total_days <= 60:
            return f"{int(math.ceil(total_days/30))} M"
        else:
            raise ValueError("分钟级区间过长，请缩短到 ~60 天内或改用更粗 bar。")
    elif bar_size == "1 hour":
        if total_days <= 1:
            return f"{max(1, int(math.ceil(total_days)))} D"
        elif total_days <= 60:
            return f"{int(math.ceil(total_days/30))} M"
        elif total_days <= 365:
            return "1 Y"
        else:
            raise ValueError("小时级区间超过 1 年：请缩短区间或自行分段调用。")
    elif bar_size == "1 day":
        if total_days <= 365:
            return "1 Y"
        elif total_days <= 365*3:
            return "3 Y"
        elif total_days <= 365*5:
            return "5 Y"
        else:
            return "10 Y"
    return "1 Y"

def fetch_data_from_ibkr(
    symbols,
    start =  "2024-01-01",
    end = "2024-12-31",
    useRTH=False,   # useRTH=True 时仅返回常规交易时段（美股 09:30–16:00 ET）. useRTH=False 含盘前盘后
    interval="1h",
    is_daily_scan = False,
    is_connect_n_download = False,
) -> pd.DataFrame:
    if isinstance(symbols, str):
        symbols = [symbols]
     
    if interval not in _INTERVAL_TO_BARSIZE:
        raise ValueError(f"不支持的 interval: {interval}；可选: {list(_INTERVAL_TO_BARSIZE.keys())}")

    bar_size = _INTERVAL_TO_BARSIZE[interval]
    # 注意：这里将 start/end 解析为 tz-naive（不带时区）
    start_dt = pd.to_datetime(start)
    end_dt   = pd.to_datetime(end)

   
    data_dict = {}
    
    for symbol in symbols:
        str_a = "useRTH" if useRTH else "all_day"
        file_path = os.path.join("data", f"{symbol}_{interval}_{start}_{end}_{str_a}IB.csv")
        if not is_daily_scan and os.path.exists(file_path):
            df = pd.read_csv(file_path, index_col="Date", parse_dates=True)
        elif is_connect_n_download: 
            duration_str = _choose_duration_str(start_dt, end_dt, bar_size)
            ib = IB()
            ib.connect(_IB_HOST, _IB_PORT, clientId=_IB_CLIENT_ID)
            print(f"⬇️ Downloading data for {symbol} via IBKR")
            contract = Stock(symbol, "SMART", "USD")
            ib.qualifyContracts(contract)

            bars = ib.reqHistoricalData(
                contract=contract,
                endDateTime=end_dt.strftime("%Y%m%d %H:%M:%S"),
                durationStr=duration_str,
                barSizeSetting=bar_size,
                whatToShow="TRADES",
                useRTH=useRTH,
                formatDate=1,
                keepUpToDate=False,
            )
            if not bars:
                df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
            else:
                df = util.df(bars).rename(
                    columns={
                        "date": "Date",
                        "open": "Open",
                        "high": "High",
                        "low": "Low",
                        "close": "Close",
                        "volume": "Volume",
                    }
                )
                if hasattr(df["Date"].dtype, "tz") and df["Date"].dt.tz is not None:
                    # tz-aware -> 转 UTC
                    df["Date"] = df["Date"].dt.tz_convert("UTC")
                else:
                    # tz-naive -> 先标记为 UTC（假定 IB 返回可视为 UTC 时间）
                    df["Date"] = df["Date"].dt.tz_localize("UTC")

                # 统一去掉时区（得到 tz-naive，方便与你的下游流程兼容）
                df["Date"] = df["Date"].dt.tz_convert("UTC").dt.tz_localize(None)
                df = df[(df["Date"] >= start_dt) & (df["Date"] <= end_dt)]

                # 设 index & 列顺序/类型
                df = df.set_index("Date")[["Open", "High", "Low", "Close", "Volume"]]
                df["Volume"] = df["Volume"].fillna(0).astype("int64")
                if not is_daily_scan:
                    df.to_csv(file_path, index_label="Date")
                time.sleep(2) 
                    # 若 Datetime 含时区（常见），先转到 UTC；若不含，先认为是 UTC
            
            ib.disconnect()
        else:
            print(symbol,"没有数据，且没有下载")
            df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        data_dict[symbol] = df
        
    

    return data_dict
 

# 示例
if __name__ == "__main__":
    data = fetch_data_from_ibkr(
        symbols=["AAPL","LULU"],
        start="2023-01-01",
        end="2023-12-31",
        useRTH=False,
        interval="1h",
    )
    
    print("总行数:", len(data)) 
