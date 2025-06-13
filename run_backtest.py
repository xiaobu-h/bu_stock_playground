
import backtrader as bt
import pandas as pd
from fetcher import fetch_yahoo_data
from strategy import SmaCross

class PandasData(bt.feeds.PandasData):
    params = (
        ("datetime", None),
        ("open", "Open"),
        ("high", "High"),
        ("low", "Low"),
        ("close", "Close"),
        ("volume", "Volume"),
        ("openinterest", -1),
    )

def run(symbol="AAPL"):
    df = fetch_yahoo_data(symbol)
    df = df[["Open", "High", "Low", "Close", "Volume"]]

    cerebro = bt.Cerebro()
    data = PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.addstrategy(SmaCross)
    cerebro.broker.set_cash(10000)
    cerebro.run()
    cerebro.plot()

if __name__ == "__main__":
    run("AAPL")
