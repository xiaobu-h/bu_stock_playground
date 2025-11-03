import backtrader as bt
from datetime import datetime ,time
from collections import defaultdict
import pandas as pd 
import pandas_market_calendars as mcal
import logging
from strategy.bcs.sensitive_param import LOOKBACK_DAYS, VOLUME_MULTIPLIER, TAKE_PROFIT_PERCENT, CROSS_DEEP_PCT, MIN_TOTAL_INCREASE_PERCENT,OPTION_DAYS_AHEAD , VOLUME_MULTIPLIER_FOR_SCAN, CROSS_DEEP_PCT_FOR_SCAN, MIN_TOTAL_INCREASE_PERCENT_FOR_SCAN
from strategy.strategy_util import SIGNAL_SPIKE_DATE, is_quadruple_witching, log_buy, log_sell

has_ordered = False

class BullCallOptionStrategy(bt.Strategy):
    params = (
        ('only_scan_last_day', True),
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
        ('global_stats',{"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0, "buy_symbols": [], "sell_symbols_win": [], "sell_symbols_loss": [],"extra_counter":0}),
        ('is_backtest', False)
    )
 
    def __init__(self):
        self.data = self.datas[0]
        self.boll = bt.indicators.BollingerBands(self.data.close, period=20, devfactor=2)
        self.vol_sma = bt.indicators.SimpleMovingAverage(self.data.volume, period=LOOKBACK_DAYS) #用于判断
        self.vol_sma5 = bt.indicators.SimpleMovingAverage(self.data.volume, period=5)  # for logging
        self.vol_sma30 = bt.indicators.SimpleMovingAverage(self.data.volume, period=30) # for logging
        self.signal_today = False
        self.entry_price = None
        self.zhusun_price = None   
        self.global_stats = self.p.global_stats
        self.ordered = False
        self.symbol = self.p.symbol 
        
        
        self.is_targeted = False
        self.buy_date = None
        
        
        
    def check_buy_signal(self): 
        if len(self.data) < LOOKBACK_DAYS:
            return False
        open_ = self.data.open[0]
        close = self.data.close[0]
        low_band = self.boll.lines.bot[0]
        volume = self.data.volume[0]
        avg_volume = self.vol_sma[0]
        
        if close <  open_:    
            return False
        
        if (close < low_band)  or (open_ >= low_band ):  # cross over Bollinger low band
            return False
        
        cross_deep_pct = CROSS_DEEP_PCT if self.p.is_backtest else CROSS_DEEP_PCT_FOR_SCAN
        
        if ((low_band - open_) / low_band) < cross_deep_pct:     
            return False
        
        volume_multiplier = VOLUME_MULTIPLIER if self.p.is_backtest else VOLUME_MULTIPLIER_FOR_SCAN
        
        if volume < avg_volume * volume_multiplier:   #放量
            return False
        
        min_total_increase_percent = MIN_TOTAL_INCREASE_PERCENT if self.p.is_backtest else MIN_TOTAL_INCREASE_PERCENT_FOR_SCAN
        if abs(close - open_) <  (open_ *  min_total_increase_percent):    # 小于涨幅 bar
            return False
         
        if self.data.high[-2] < self.data.low[0] or  (self.data.high[-2] - self.data.low[0] ) /self.data.low[0] < 0.1:
            return 
        
        return True

    def next(self):
        date = self.data.datetime.date(0).strftime("%Y-%m-%d")

        if date not in self.global_stats:
            self.global_stats[date] = { "buys": 0, "wins": 0, "losses": 0,  "Win$": 0, "Loss$": 0, "buy_symbols": [],"sell_symbols_win": [], "sell_symbols_loss": [],"extra_counter": 0} 
            
        
        if self.p.only_scan_last_day:
            if len(self) < 2 or self.data.datetime.date(0) != datetime.today().date():
               return
        # ================================================== Daily Monitor =========================================================
        if  not self.p.is_backtest and self.check_buy_signal():
            low_band = self.boll.lines.bot[0]
            self.signal_today = True 
            
            logger = logging.getLogger(__name__)
            logger.info(f"[{date}] [OPTION] - Bull Call S(BL) - {self.p.symbol} ")
            logger.info(f"|-----------> Vol of 5: {round(self.data.volume[0] /self.vol_sma5[0],2)} - Vol of 30: {round(self.data.volume[0] /self.vol_sma30[0],2)} - Increase:{round((self.data.close[0] - self.data.open[0])/self.data.close[0] *100, 1)}% - Cross:{round((low_band - self.data.open[0]) / low_band *100,1)}%  ")
            return
            
            
        # =================================================== Backtest ==============================================================
        # ------------ 买入 ---------- 
        if  self.p.is_backtest and not self.ordered and  self.check_buy_signal():
           
            if date in ["2022-01-24","2025-04-07","2025-04-09"  ] :
                    return
          
            log_buy(self.global_stats,date, self.p.symbol)
 
            self.entry_price = self.data.close[0]   
            
            self.ordered = True
            self.is_targeted = False
            self.buy_date = self.data.datetime.date(0)
            
            self.buy()
            
             
        if  self.p.is_backtest and self.ordered and self.position:
            high = self.data.high[0]
            
                
            d1 = datetime.strptime(date, "%Y-%m-%d")
            d2 = datetime.strptime(self.buy_date.strftime("%Y-%m-%d"), "%Y-%m-%d")
            delta = (d1 - d2).days    # 第二天
            if delta == 1 and self.data.open[0] > self.data.close[0] and  (self.data.open[0] - self.data.close[0]) > (self.data.close[-1] - self.data.open[-1])  :
                    self.global_stats[date]["extra_counter"] += 1
                    self.is_targeted = True
         
            
            # ------------止损------------
            if  get_target_time(self.buy_date).strftime("%Y-%m-%d")  ==  self.data.datetime.date(0).strftime("%Y-%m-%d")  :
                if (self.p.printlog):
                    print("LOSS - OPTION - Bull Call S(BL) -", self.data.datetime.date(0))  
                log_sell(self.global_stats,date, (-1000), self.p.symbol)
                

                self.ordered = False
                self.close()
                return

            # ------------止盈------------
            if high >= self.entry_price *TAKE_PROFIT_PERCENT:
                log_sell(self.global_stats,date, (1000) , self.p.symbol)
                if (self.p.printlog):
                    print("Win - OPTION - Bull Call S(BL) -", self.data.datetime.date(0)) 
                self.ordered = False
                self.close()
                if self.is_targeted:
                    self.global_stats[date]["extra_counter"] += 1000000
                    
                return
            
            
            
                
                
 
                
 # 定时卖出 helper function
def get_target_time(date):
    
    # 交易所日历（这里用 NYSE）
    nyse = mcal.get_calendar("XNYS")
    base = pd.Timestamp(date) 
    n_day = OPTION_DAYS_AHEAD * 2 + 3
    end = base + pd.Timedelta(days=38)
    # 取出从 date 往后 X 天的交易日
    schedule = nyse.schedule(start_date=base, end_date=end)
    trading_days = mcal.date_range(schedule, frequency="1D")

    target_day = trading_days[OPTION_DAYS_AHEAD - 1]  #  [0]当天 [1]第二个交易日

    target_time = pd.Timestamp(target_day.date()) + pd.Timedelta(hours=13) 
    return target_time