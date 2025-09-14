import backtrader as bt
from datetime import datetime ,time
from collections import defaultdict
import pandas as pd 
import logging
from strategy.bl_jump_lower_open.sensitive_param import VOLUME_FOR_QUADRUPLE_WITCH_DAY,LOOKBACK_DAYS, VOLUME_MULTIPLIER, TAKE_PROFIT_PERCENT, STOP_LOSS_THRESHOLD, CROSS_DEEP_PCT, MIN_TOTAL_INCREASE_PERCENT
 

ONE_TIME_SPENDING_BOLLINGER = 20000  # 每次买入金额
has_ordered = False

class BollingerVolumeBreakoutStrategy(bt.Strategy):
    params = (
        ('only_scan_last_day', True),
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
        ('global_stats',{"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0, "buy_symbols": [], "sell_symbols": []}),
        ('is_backtest', False)
    )
 
    def __init__(self):
        self.data_mins = self.datas[0]
        self.data_daily = self.datas[0]
        #self.data_daily =  self.datas[1] if self.p.is_backtest else self.datas[0]
        
        self.boll = bt.indicators.BollingerBands(self.data_daily.close, period=20, devfactor=2)
        self.vol_sma = bt.indicators.SimpleMovingAverage(self.data_daily.volume, period=LOOKBACK_DAYS)
        self.balance_by_date = defaultdict(float)
        self.size = 0
        self.signal_today = False
        self.entry_price = None
        self.zhusun_price = None   
        self.global_stats = self.p.global_stats
        self.ordered = False
       

    def check_buy_signal(self): 
        if len(self.data) < LOOKBACK_DAYS:
            return False
        open_ = self.data_daily.open[0]
        close = self.data_daily.close[0]
        low_band = self.boll.lines.bot[0]
        volume = self.data_daily.volume[0]
        avg_volume = self.vol_sma[0]
      
        if close <  open_:    
            return False
        
        if (close < low_band)  | (open_ >= low_band ):  # cross over Bollinger low band
            return False
        
        if ((low_band - open_) / low_band) < CROSS_DEEP_PCT:     
            return False
        
        vol = VOLUME_FOR_QUADRUPLE_WITCH_DAY if is_quadruple_witching(self.data_daily.datetime.date(0)) else VOLUME_MULTIPLIER
            
        if volume < avg_volume * vol:   #放量
            return False
        
        if abs(close - open_) <  open_ *  MIN_TOTAL_INCREASE_PERCENT:    # 小于涨幅 bar
           
            return False
        
        return True

    def next(self):
        date = self.data_daily.datetime.date(0).strftime("%Y-%m-%d")
        sell_date =  self.data_mins.datetime.date(0).strftime("%Y-%m-%d")
        
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
            if len(self) < 2 or self.data_daily.datetime.date(0) != datetime.today().date():
               return
        # ================================================== Daily Monitor =========================================================
        if  not self.p.is_backtest and self.check_buy_signal():
            self.signal_today = True
            logger = logging.getLogger(__name__)
            logger.info(f"[{date}] Bollinger Jump - {self.p.symbol} - win: {round(self.data_daily.close[0]*TAKE_PROFIT_PERCENT, 3 )} - stop:{round((self.data_daily.low[0] * STOP_LOSS_THRESHOLD), 3 )}")
            return
            
            
        # =================================================== Backtest ==============================================================
        # ------------ 买入 ----------
        #and (self.data_mins.datetime.time(0) == time(13,00) or self.data_mins.datetime.time(0) == time(13,30)) 
        if  self.p.is_backtest and not self.ordered and  self.check_buy_signal():
           
            if date in ["2024-12-20" ,"2020-02-28", "2020-05-29", "2020-06-19",  "2020-11-30","2020-12-18","2021-01-06","2022-01-04","2022-03-18", "2022-06-17" ,"2022-06-24" ,
                        "2022-11-30", "2023-01-31", "2023-05-31" , "2023-11-30",  "2024-03-15" , "2024-05-31" , "2024-09-20", "2025-03-21" , "2025-04-07", "2025-05-30" , "2025-04-09"]:
               return
            # ==================== 统计 ====================
            self.global_stats[date]["buys"] += 1
            self.global_stats[date]["buy_symbols"].append(self.p.symbol)
            # ==============================================
 
            self.entry_price = self.data_daily.close[0]
            self.zhusun_price = self.data_daily.low[0] * STOP_LOSS_THRESHOLD
             
            self.ordered = True
            '''
             # 重复添加 止盈止损判断 以统计 第二天第一个小时的bar  因为在 self.buy()之后 这个bar会被跳过
            if self.data_mins.low[0] < self.zhusun_price:  
                self.global_stats[sell_date]["losses"] += 1
                size = int(ONE_TIME_SPENDING_BOLLINGER / self.entry_price)
                self.global_stats[sell_date]["Loss$"] -= size * (self.entry_price - self.zhusun_price)
                self.global_stats[sell_date]["sell_symbols"].append(self.p.symbol) 
                self.ordered = False
                return
                
            if  self.data_mins.high[0]  > self.entry_price * TAKE_PROFIT_PERCENT:
                self.global_stats[sell_date]["wins"] += 1  
                self.global_stats[sell_date]["Win$"] += ONE_TIME_SPENDING_BOLLINGER * (TAKE_PROFIT_PERCENT - 1)
                self.global_stats[sell_date]["sell_symbols"].append(self.p.symbol) 
                self.ordered = False
                return
            '''
            self.buy()
            
             
        if  self.p.is_backtest and self.ordered and self.position:
            high = self.data_mins.high[0]
            low = self.data_mins.low[0]
             # 止损
            if low < self.zhusun_price:
                
                # ==================== 统计 ====================
                size = int(ONE_TIME_SPENDING_BOLLINGER / self.entry_price)
                self.global_stats[date]["losses"] += 1
                self.global_stats[date]["Loss$"] -= size * (self.entry_price - self.zhusun_price)
                self.global_stats[date]["sell_symbols"].append(self.p.symbol)
                # ==============================================
                self.ordered = False
                self.close()
                return

            # 止盈
            if high >= self.entry_price * TAKE_PROFIT_PERCENT:
                
                # ==================== 统计 ====================
                self.global_stats[date]["wins"] += 1  
                self.global_stats[date]["Win$"] += ONE_TIME_SPENDING_BOLLINGER * (TAKE_PROFIT_PERCENT - 1)
                self.global_stats[date]["sell_symbols"].append(self.p.symbol)
                # ==============================================
                self.ordered = False
                self.close()
                return
            
           
 
           
def is_quadruple_witching(date) -> bool: 
    d = pd.Timestamp(date).tz_localize(None).normalize()
    if d.month not in (3, 6, 9, 12):
        return False 
    third_fris = pd.date_range(start=f'{d.year}-01-01',
                               end=f'{d.year}-12-31',
                               freq='WOM-3FRI').normalize()
    return d in third_fris