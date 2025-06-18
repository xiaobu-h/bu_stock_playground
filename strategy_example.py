
import backtrader as bt

class SmaCross(bt.SignalStrategy):
    def __init__(self):
        sma_short = bt.ind.SMA(period=20)
        sma_long = bt.ind.SMA(period=50)
        self.signal_add(bt.SIGNAL_LONG, bt.ind.CrossOver(sma_short, sma_long))
