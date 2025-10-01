import backtrader as bt
from datetime import datetime ,time
from collections import defaultdict
import pandas as pd 
import logging
from strategy.short.sensitive_param import  VOLUME_FOR_QUADRUPLE_WITCH_DAY,LOOKBACK_DAYS, VOLUME_MULTIPLIER, TAKE_PROFIT_PERCENT, STOP_LOSS_THRESHOLD, CROSS_DEEP_PCT, MIN_TOTAL_INCREASE_PERCENT
from strategy.strategy_util import SIGNAL_SPIKE_DATE, is_quadruple_witching, log_buy, log_sell

ONE_TIME_SPENDING_BOLLINGER = 20000  # 每次买入金额
has_ordered = False

class MuBeiStrategy(bt.Strategy):
    params = (
        ('only_scan_last_day', True),
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
        ('global_stats',{"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0, "buy_symbols": [], "sell_symbols": [], "extra_counter":0}),
        ('is_backtest', False)
    )
 
    def __init__(self):
        self.data = self.datas[0]
        self.boll = bt.indicators.BollingerBands(self.data.close, period=20, devfactor=2)
        self.vol_sma = bt.indicators.SimpleMovingAverage(self.data.volume, period=LOOKBACK_DAYS)
        self.balance_by_date = defaultdict(float)
        self.size = 0
        self.signal_today = False
        self.entry_price = None
        self.zhusun_price = None   
        self.global_stats = self.p.global_stats
        self.ordered = False
        self.symbol = self.p.symbol 
        self.profile = None 
         

    def check_buy_signal(self): 
        if len(self.data) < LOOKBACK_DAYS:
            return False
        open_ = self.data.open[0]
        close = self.data.close[0]
        upper_band = self.boll.lines.top[0]
        volume = self.data.volume[0]
        avg_volume = self.vol_sma[0]
        
        if close >  open_:    
            return False
        
        if (open_ < upper_band) or  (close < upper_band) :  # cross over Bollinger upper band
            return False
        
        if ((open_ -upper_band) / upper_band) < CROSS_DEEP_PCT :     
            return False
        
        vol = VOLUME_FOR_QUADRUPLE_WITCH_DAY  if is_quadruple_witching(self.data.datetime.date(0)) else VOLUME_MULTIPLIER
            
        if volume < avg_volume * vol:   #放量
            return False
        
        if abs(  open_ - close) <  close *  MIN_TOTAL_INCREASE_PERCENT :    # 小于涨幅 bar
            return False
         
        
        return True

    def next(self):
        date = self.data.datetime.date(0).strftime("%Y-%m-%d")

        if date not in self.global_stats:
            self.global_stats[date] = { "buys": 0, "wins": 0, "losses": 0,  "Win$": 0, "Loss$": 0, "buy_symbols": [],"sell_symbols": [],"extra_counter": 0} 
            
        
        if self.p.only_scan_last_day:
            if len(self) < 2 or self.data.datetime.date(0) != datetime.today().date():
               return
        # ================================================== Daily Monitor =========================================================
        if  not self.p.is_backtest and self.check_buy_signal():
            low_band = self.boll.lines.bot[0]
            self.signal_today = True
        
            today_increase = (self.data.close[0] - self.data.open[0]) /self.data.open[0]
            self.profile = TAKE_PROFIT_PERCENT 
            self.zhusun_price = self.data.low[0] * STOP_LOSS_THRESHOLD    #竹笋点
            
            logger = logging.getLogger(__name__)
            logger.info(f"[{date}] Mu Bei - {self.p.symbol} - win: {round(self.data.close[0]*self.profile, 3 )} - stop:{round(self.zhusun_price, 3 )}; VOL:{round(self.data.volume[0] /self.vol_sma[0],2)} - increase:{round((self.data.close[0] - self.data.open[0])/self.data.close[0] *100, 1)}% - cross:{round((low_band - self.data.open[0]) / low_band *100,1)}%")
            return
            
            
        # =================================================== Backtest ==============================================================
        # ------------ 买入 ---------- 
        if  self.p.is_backtest and not self.ordered and  self.check_buy_signal():
           
         
            log_buy(self.global_stats,date, self.p.symbol)
 
            self.entry_price = self.data.close[0]    
            self.profile = TAKE_PROFIT_PERCENT 
            self.zhusun_price = self.data.close[0]  * 1.03   #竹笋点
            
            self.ordered = True
 
            self.buy()
            
             
        if  self.p.is_backtest and self.ordered and self.position:
            high = self.data.high[0]
            low = self.data.low[0]
             # ------------止损------------
            if high > self.zhusun_price:
                if (self.p.printlog):
                    print("LOSS - Mu Bei -", self.data.datetime.date(0))
                size = int(ONE_TIME_SPENDING_BOLLINGER / self.entry_price)
                log_sell(self.global_stats,date, (- size *  ( self.zhusun_price -self.entry_price )), self.p.symbol)
                
                self.ordered = False
                self.close()
                return

            # ------------止盈------------
            if low < self.entry_price * self.profile:
                log_sell(self.global_stats,date, ONE_TIME_SPENDING_BOLLINGER *  (1 - self.profile), self.p.symbol)
                if (self.p.printlog):
                    print("Win -  Mu Bei -", self.data.datetime.date(0))
                self.ordered = False
                self.close()
                return
          
 