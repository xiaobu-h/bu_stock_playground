
import backtrader as bt
import pandas as pd
from backtest_fetcher import fetch_yahoo_data
from strategy.bl_jump_lower_open.stratety import BollingerVolumeBreakoutStrategy

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
        cerebro.broker.set_coc(True) # set to True to enable close of the current bar to be used for the next bar's open price

        """ 
        cerebro.optstrategy(
            AttackReversalStrategy,
            boll_period=[20],
            boll_devfactor=[2],
            lookback_days=[5],
            volume_multiplier=[ 1.75],
            take_profit= [1.15],
            printlog=[True],
            symbol=symbol
        )
        
        """
        cerebro.addstrategy(
            BollingerVolumeBreakoutStrategy,
            lookback_days=4,
            volume_multiplier=1.6,
            take_profit=1.10,
            printlog=True,
            symbol=symbol,
            only_scan_last_day = False,
        )
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.broker.set_cash(10000)
        cerebro.addsizer(bt.sizers.FixedSize, stake=10)   
        cerebro.run()
        cerebro.plot()


# manually run the backtest

if __name__ == "__main__":
    #run(["AAPL"])
    run(["AAPL", "MSFT", "NVDA", "GOOG", "TSLA", "AMD"  ])  #9:6
    run(["IBM" , "ORCL", "V" , "META", "AMZN", "MSTR"])  #5:11    3:3
    
    #run(["SPY", "NFLX", "PYPL", "PLTR", "COIN", "HOOD"  ])  #12:5    8:1
     #AAPL MSFT  GOOG  TSLA  NVDA  AMD  INTC  IBM  ORCL  CSCO AMZN  META  NFLX  PYPL  SQ  SHOP  BABA  TCEHY  V  MA

    #1.4 -  16:17         1.6 -  7:9
    #run(["KO", "OXY", "TSM", "COST", "XLK", "ADBE" , "CRM", "INTU", "AVGO", "QCOM", "TXN", "LRCX", "AMAT", "MU", "ASML",  "PYPL" ])  