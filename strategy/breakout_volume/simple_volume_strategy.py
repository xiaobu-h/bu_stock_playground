import backtrader as bt
from datetime import datetime
import pandas as pd
import logging
from collections import defaultdict
import csv 
from strategy.breakout_volume.sensitive_param import  VOLUME_MULTIPLIER , MIN_TOTAL_INCREASE_PERCENT ,MAX_JUMP_DOWN_PERCENT , STOP_LOSS_THRESHOLD, TAKE_PROFIT_PERCENT_SMALL,TAKE_PROFIT_PERCENT_LARGE ,BAR ,ZHUSUN_PERCENT

ONE_TIME_SPENDING = 20000  # 每次买入金额
   
class SimpleVolumeStrategy(bt.Strategy):

    params = (
        ('only_scan_last_day', True),
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
        ('global_stats',{"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0, "buy_symbols": [], "sell_symbols": []})
    )
        
    
    def __init__(self): 
        self.order = None
        self.entry_price = None
        self.zhusun_price = None
        self.day0_increses= None 
        self.vol_sma3 = bt.indicators.SimpleMovingAverage(self.data.volume, period=3)
        self.vol_sma5 = bt.indicators.SimpleMovingAverage(self.data.volume, period=5)
        self.vol_sma10 = bt.indicators.SimpleMovingAverage(self.data.volume, period=10)
        self.signal_today = False
        self.profile_rate = None
        self.global_stats= self.p.global_stats

    
    
    def check_buy_signal(self): 
        open_ = self.data.open[0]
        close = self.data.close[0] 
        volume = self.data.volume[0]
        
        if close < open_:
            return False
        
        if (volume < self.vol_sma3[0] * VOLUME_MULTIPLIER) & (volume < self.vol_sma10[0] * VOLUME_MULTIPLIER): # 交易量放量倍数 (大于3天/10天均值）
           # print(f"[{self.data.datetime.date(0)}]Volume is not a spike.")
            return False

        if abs(close - open_) <  open_ *  MIN_TOTAL_INCREASE_PERCENT:    # 小于涨幅 bar
            #print(f"[{self.data.datetime.date(0)}]Candle increase is too small.")
            return False
        
        if (self.data.low[-1]  > close) & ((self.data.low[-1] - close) > self.data.close[-1] * MAX_JUMP_DOWN_PERCENT):   #没有跳空下跌4%以上
            #print(f"[{self.data.datetime.date(0)}]Jump down too much.")
            return False
        
        if  min(self.data.low[0] , self.data.low[-1] ) < close * STOP_LOSS_THRESHOLD:   
            return False
        
        return True
    
    
    def next(self):
       
        date = self.data.datetime.date(0).strftime("%Y-%m-%d")
        if date not in self.global_stats:
            self.global_stats[date] = {
            "buys": 0, 
            "wins": 0, 
            "losses": 0, 
            "Win$": 0, 
            "Loss$": 0, 
            "buy_symbols": [],
            "sell_symbols": []
        }
            
            
        if self.p.only_scan_last_day:
            if len(self) < 2 or self.data.datetime.date(0) != datetime.today().date():
               return
           
        
        if  self.position:  
        
            # 止盈
            if  self.data.high[0]  > self.entry_price * self.profile_rate:
                 
                # ==================== 统计 ====================
                self.global_stats[date]["wins"] += 1  # 累加到全局
                self.global_stats[date]["Win$"] += ONE_TIME_SPENDING * (self.profile_rate - 1)
                self.global_stats[date]["sell_symbols"].append(self.p.symbol)
                # ==============================================
                self.close()
                return
            
            
            # 止损
            if self.data.low[0] < self.zhusun_price:  
                
   
                # ==================== 统计 ====================
                self.global_stats[date]["losses"] += 1
                size = int(ONE_TIME_SPENDING / self.entry_price)
                self.global_stats[date]["Loss$"] -= size * (self.entry_price - self.zhusun_price)
                self.global_stats[date]["sell_symbols"].append(self.p.symbol)
                # ==============================================
                self.close()
                return
     
        
        if self.check_buy_signal():
            self.signal_today = True
            if self.data.datetime.date(0).strftime("%Y-%m-%d") in ["2024-12-20" ,"2020-02-28", "2020-05-29", "2020-06-19",  "2020-11-30","2020-12-18","2021-01-06","2022-01-04","2022-03-18", "2022-06-17" ,
                                                                   "2022-06-24" , "2022-11-30", "2023-01-31", "2023-05-31" , "2023-11-30",  "2024-03-15" , "2024-05-31" , "2024-09-20", "2025-03-21" , "2025-04-07", "2025-05-30"  ]:
               return

            # ==================== 统计 ====================
            self.global_stats[date]["buys"] += 1
            self.global_stats[date]["buy_symbols"].append(self.p.symbol)
            # ==============================================
            
            self.order = self.buy()
            self.day0_increses = self.data.close[0] - self.data.open[0]
            self.profile_rate = TAKE_PROFIT_PERCENT_SMALL if (self.day0_increses /self.data.open[0]) < BAR else TAKE_PROFIT_PERCENT_LARGE
            self.entry_price = self.data.close[0]
            self.zhusun_price = ((self.data.close[0] + self.data.open[0]) * 0.5 ) * ZHUSUN_PERCENT    # 竹笋点 
            logger = logging.getLogger(__name__)
            logger.info(f"[{self.data.datetime.date(0)}] VOL x 2 - {self.p.symbol} - win: {round(self.entry_price*self.profile_rate, 3 )} - stop:{round(self.zhusun_price, 3 )} ")
       
      