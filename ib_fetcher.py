# -*- coding: utf-8 -*-
from datetime import datetime, date
import math
import pandas as pd
from ib_insync import IB, Stock, util
import os
import time

_IB_HOST = "127.0.0.1"
_IB_PORT = 7497
_IB_CLIENT_ID = 31

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
 

def fetch_data_from_ibkr(
    symbols,
    start =  "2024-01-01",
    end = "2024-12-31",
    useRTH=True,   # useRTH=True 时仅返回常规交易时段（美股 09:30–16:00 ET）. useRTH=False 含盘前盘后
    interval="1h",
    is_daily_scan = False,
    is_connect_n_download = False,
    duration_str = "1 Y",
    ib = None,
    re_download = False,
) -> pd.DataFrame:
    if isinstance(symbols, str):
        symbols = [symbols]
     
    if interval not in _INTERVAL_TO_BARSIZE:
        raise ValueError(f"不支持的 interval: {interval}；可选: {list(_INTERVAL_TO_BARSIZE.keys())}")
    bar_size = _INTERVAL_TO_BARSIZE[interval] 
    end_str = end if end != "" else date.today().strftime("%Y-%m-%d")

    data_dict = {} 
       
    
    for symbol in symbols:
        str_a = "useRTH" if useRTH else "all_day"
        csv_path = "data/daily" if is_daily_scan else "data"
        file_path = os.path.join(csv_path, f"{symbol}_{interval}_{start}_{end_str}_{str_a}IB.csv")
    
        if not re_download and os.path.exists(file_path):
            df = pd.read_csv(file_path, index_col="Date", parse_dates=True)
        elif is_connect_n_download: 
            if re_download and os.path.exists(file_path):
                print(f"|-- Re-downloading data for {symbol} via IBKR")
                os.remove(file_path)
            else:
                print(f"|-- Downloading data for {symbol} via IBKR")
            contract = Stock(symbol, "SMART", "USD")
            ib.qualifyContracts(contract)

            bars = ib.reqHistoricalData(
                contract=contract,
                endDateTime="" if end == "" else pd.to_datetime(end).strftime("%Y%m%d %H:%M:%S"),
                durationStr= duration_str,
                barSizeSetting= bar_size,
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
    
                df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)

            
                df = df.set_index("Date")[["Open", "High", "Low", "Close", "Volume"]]
                df["Volume"] = df["Volume"].fillna(0).astype("int64")
                df.to_csv(file_path, index_label="Date")
                #if not is_daily_scan:
                  #  time.sleep(5)     # Sleep
                    
            
            
        else:
            print(symbol,"没有数据，且没有下载")
            df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        data_dict[symbol] = df

        
    return data_dict




# for daily monitor use only
def download_daily_last_3_months(
    symbol: str,
    ib: IB = None,
    end: str = None,
    is_connect_n_download: bool = True,
    re_download: bool = False,
) -> pd.DataFrame: 
    result = fetch_data_from_ibkr(ib = ib,symbols=symbol,duration_str="3 M" ,interval="1d" , end = end ,useRTH=True , is_daily_scan = True, is_connect_n_download=is_connect_n_download, re_download = re_download)
    return result[symbol]
 
def ib_connect() -> IB:
    ib = IB()
    ib.connect(_IB_HOST, _IB_PORT, clientId=_IB_CLIENT_ID)
    return ib

def ib_disconnect(ib: IB):
    if ib.isConnected():
        ib.disconnect()
    else:
        print("IB was not connected.")
        
        
        
         