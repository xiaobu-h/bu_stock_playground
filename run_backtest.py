
import backtrader as bt
import pandas as pd
from fetcher import fetch_yahoo_data
from strategy_attack_day import AttackReversalStrategy

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

def run(symbols=["AAPL", "MSFT", "NVDA"]):
    df_dict = fetch_yahoo_data(symbols)
    
    for symbol, df in df_dict.items():
        df = df[["Open", "High", "Low", "Close", "Volume"]]

        cerebro = bt.Cerebro()
        data = PandasData(dataname=df)
        cerebro.adddata(data)

        """ 
        cerebro.optstrategy(
            AttackReversalStrategy,
            boll_period=[20],
            boll_devfactor=[2],
            lookback=[5],
            volume_multiplier=[ 1.75],
            take_profit= [1.15],
            printlog=[True],
            symbol=symbol
        )
        
        """
        cerebro.addstrategy(
            AttackReversalStrategy,
            boll_period=20,
            boll_devfactor=2,
            lookback=5,
            volume_multiplier=1.75,
            take_profit=1.15,
            printlog=True,
            symbol=symbol,
            trailing_stop_pct=0.05
        )

        cerebro.broker.set_cash(10000)
        cerebro.run()
        cerebro.plot()

if __name__ == "__main__":
   # run(["PLTR"])
    #run(["AAPL", "MSFT", "NVDA", "GOOG", "TSLA", "AMD"  ])  
    run(["IBM" , "ORCL", "V" , "META", "AMZN", "MSTR"])  
    
    #run(["SPY", "NFLX", "PYPL", "PLTR", "COIN", "HOOD"  ])  
     #AAPL MSFT  GOOG  TSLA  NVDA  AMD  INTC  IBM  ORCL  CSCO AMZN  META  NFLX  PYPL  SQ  SHOP  BABA  TCEHY  V  MA
