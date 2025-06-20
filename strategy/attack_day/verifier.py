import backtrader as bt
import yfinance as yf
import pandas as pd
from scan import AttackReversalSignalScan

class DebugAttackReversalScan(AttackReversalSignalScan):
    params = (("symbol", "Symbol"),)

    def __init__(self):
        super().__init__()
        self.signal_dates = []

    def next(self):
        date = self.data.datetime.date(0)
        # verifier debug
        print(f"[{date}] close[0]={self.data.close[0]:.2f}, close[-1]={self.data.close[-1]}, volume={self.data.volume[0]}, vol_sma5={self.vol_sma5[0]}")

        if not self.position and self.is_attack_setup():
            print(f"✅ Signal triggered at {date}")
            self.signal_dates.append(date)
        super().next()

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

def fetch_data_by_date(symbol, start_date, end_date):
    load_start = pd.to_datetime(start_date) - pd.Timedelta(days=30)   
    df = yf.download(symbol, start=load_start.strftime("%Y-%m-%d"), end=end_date, interval="1d", auto_adjust=False)
    if df.empty:
        raise ValueError(f"No data for {symbol} from {start_date} to {end_date}")
 
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0].capitalize() for col in df.columns]
    else:
        df.columns = [col.capitalize() for col in df.columns]

    df.dropna(inplace=True)
    return df

def test_strategy_on_date(symbol, start_date, end_date):
    load_start = pd.to_datetime(start_date) - pd.Timedelta(days=30)
    df = fetch_data_by_date(symbol, load_start.strftime("%Y-%m-%d"), end_date)

    data = CustomPandasData(dataname=df)
    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.addstrategy(DebugAttackReversalScan, symbol=symbol)
    result = cerebro.run()
    strat = result[0]

    if hasattr(strat, 'signal_dates') and strat.signal_dates:
        print(f"✅ {symbol} triggered buy signal on: {strat.signal_dates}")
    else:
        print(f"❌ {symbol} did not trigger any buy signals from {start_date} to {end_date}.")

if __name__ == "__main__":
    
    test_strategy_on_date("ADBE", "2025-04-20", "2025-06-19")