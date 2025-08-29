import backtrader as bt
from datetime import datetime
import pandas as pd
import logging

class SimpleVolumeLogic:
    def __init__(self, data, volume_multiplier, min_total_increse_percent):
        self.data = data
        self.min_total_increse_percent = min_total_increse_percent
 
        self.volume_multiplier = volume_multiplier  
        self.vol_sma3 = bt.indicators.SimpleMovingAverage(self.data.volume, period=3)
        self.vol_sma5 = bt.indicators.SimpleMovingAverage(self.data.volume, period=5)
        self.vol_sma10 = bt.indicators.SimpleMovingAverage(self.data.volume, period=10)
        
               
            
    def check_buy_signal(self): 
        open_ = self.data.open[0]
        close = self.data.close[0] 
        volume = self.data.volume[0]
        
        if close < open_:
            #print(f"[{self.data.datetime.date(0)}]Close is less than open.")
            return False
        
        if (volume < self.vol_sma3[0] * self.volume_multiplier) & (volume < self.vol_sma5[0] * self.volume_multiplier) & (volume < self.vol_sma10[0] * self.volume_multiplier):
           # print(f"[{self.data.datetime.date(0)}]Volume is not a spike.")
            return False

        if abs(close - open_) <  open_ *  self.min_total_increse_percent:  
            #print(f"[{self.data.datetime.date(0)}]Candle increase is too small.")
            return False
        
        if (self.data.low[-1]  > close) & ((self.data.low[-1] - close) > self.data.close[-1] * 0.03):
            #print(f"[{self.data.datetime.date(0)}]Jump down too much.")
            return False
        
        return True
    
class SimpleVolumeStrategy(bt.Strategy):
    params = (
        ('volume_multiplier', 1.8), 
        ('min_total_increse_percent', 0.0133),  # 最小涨幅 1.33%
        ('only_scan_last_day', True),
        ('take_profit', 1.05),
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
    )
        
    
    def __init__(self):
        self.signal_today = False
        self.order = None
        self.entry_price = None
        self.day0_increses= None
        self.buy_logic = SimpleVolumeLogic(
            self.data, 
            min_total_increse_percent=self.p.min_total_increse_percent,
            volume_multiplier=self.p.volume_multiplier
        ) 

    def next(self):
        if self.p.only_scan_last_day:
            if len(self) < 2 or self.data.datetime.date(0) != datetime.today().date():
               return
           
        
        if  self.position:  
            
            # 止盈
            rate = 1.015 if (self.day0_increses /self.data.open[0]) < 0.06 else 1.025   # 默认1.5%； 当日上涨超6% 则止盈放宽至2.5%
            
            if  self.data.high[0]  > self.entry_price * rate:
                self.close()
                return
            
            
            # 止损
            if self.data.low[0] < self.stop_price * 0.97: 
                #print(f"[{self.data.datetime.date(0)}] ❌ Stop loss hit: Low {self.data.low[0]:.2f} < Stop {self.stop_price:.2f}")
                self.close()
            
 
        if self.buy_logic.check_buy_signal():
            logger = logging.getLogger(__name__)
            logger.info(f"[{self.data.datetime.date(0)}] VOL x 2 - {self.p.symbol}")
            
            if self.p.only_scan_last_day:
                self.signal_today = True
            else: 
                size = int(5000 / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
                    self.day0_increses = self.data.close[0] - self.data.open[0]
                    
                    #print(f"[BUY] [{self.p.symbol}] - {self.data.datetime.date(0)}]")
                    self.entry_price = self.data.close[0]
                    self.stop_price = min(self.data.low[0] , self.data.low[-1] ) 
                    self.signal_today = True
                    
