import backtrader as bt
import logging 
from datetime import datetime

class AttackReversalSignalScan(bt.Strategy):
    params = (
        ('lookback_days', 5),
        ('volume_multiplier', 1.3),
        ('symbol', 'UNKNOWN'),
        ('only_scan_last_day', True),
    )

    def __init__(self):
        self.vol_sma5 = bt.indicators.SMA(self.data.volume, period=self.p.lookback_days)
        self.signal_today = False

    def is_attack_setup(self):
        
        date = self.data.datetime.date(0)
        if not (
            self.data.close[-1] < self.data.close[-2] and
            self.data.close[-1] < self.data.open[-1] and
            self.data.close[-1] < self.data.close[-3] and
            self.data.close[-1] < self.data.close[-4] and
            self.data.close[-1] < self.data.close[-5] 
           
        ):
            #print(f"[{date}] [-1] not down down down!")
            return False

        if  ( (self.data.close[-5] - self.data.low[-1]) / self.data.low[-1] < 0.10 and (self.data.close[-6] - self.data.low[-1]) / self.data.low[-1] < 0.10 ):
            #print(f"[{date}] [0] not down 10% ") 
            return False
         
        
        if self.data.close[0] <= self.data.open[0]:
            #print(f"[{date}] [1] Today is not a bullish day.")
            logging.info(f"[{date}] [1] Today is not a bullish day.")
            return False

        if self.data.volume[0] <= self.vol_sma5[0] * self.p.volume_multiplier:
            logging.info(f"[{date}] [2] Volume is not sufficiently high.")
            return False

        return True

    def next(self):
        if self.p.only_scan_last_day and self.data.datetime.date(0) != datetime.today().date():
            return 
        if self.is_attack_setup():
            self.signal_today = True
