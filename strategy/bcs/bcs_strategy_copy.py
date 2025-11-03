import backtrader as bt
from datetime import datetime ,time
import pandas as pd 
import pandas_market_calendars as mcal
import logging
from strategy.bcs.sensitive_param_copy import  VOLUME_MULTIPLIER,TAKE_PROFIT_PERCENT, SMA_DAYS, MIN_TOTAL_INCREASE_PERCENT,OPTION_DAYS_AHEAD , VOLUME_MULTIPLIER_FOR_SCAN, MIN_TOTAL_INCREASE_PERCENT_FOR_SCAN
from strategy.strategy_util import SIGNAL_SPIKE_DATE, log_buy, log_sell

has_ordered = False

class BullCallOptionStrategy2(bt.Strategy):
    params = (
        ('only_scan_last_day', True),
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
        ('global_stats',{"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0, "buy_symbols": [], "sell_symbols_win": [], "sell_symbols_loss": [], "extra_counter":0}),
        ('is_backtest', False)
    )
 
    def __init__(self):
        self.data = self.datas[0]
        self.boll = bt.indicators.BollingerBands(self.data.close, period=20, devfactor=2)
        self.vol_sma = bt.indicators.SimpleMovingAverage(self.data.volume, period=SMA_DAYS) #用于判断
        self.signal_today = False
        self.entry_price = None
        self.zhusun_price = None   
        self.global_stats = self.p.global_stats
        self.ordered = False
        self.symbol = self.p.symbol 
        self.targeted_date = None
        
        self.is_targeted = False
        self.buy_date = None
        
        
        
    def check_buy_signal(self): 
        open_ = self.data.open[0]
        close = self.data.close[0] 
        volume = self.data.volume[0] 
        if close < open_:
            return False
        
        increases = MIN_TOTAL_INCREASE_PERCENT if self.p.is_backtest else MIN_TOTAL_INCREASE_PERCENT_FOR_SCAN
        if abs(close - open_) <  (open_ *  increases):    # 小于涨幅 bar
            #print(f"[{self.data_daily.datetime.date(0)}]Candle increase is too small.")
            return False
        
     
        volume_multiplier = VOLUME_MULTIPLIER if self.p.is_backtest else VOLUME_MULTIPLIER_FOR_SCAN
        if  volume < self.vol_sma[0] * volume_multiplier : # 交易量放量倍数 
           # print(f"[{self.data_daily.datetime.date(0)}]Volume is not a spike.")
            return False
        
   
        if  (self.data.close[0] - self.data.open[0]) / (self.data.high[0] - self.data.low[0]) < 0.25 :   # 如果上影线或下影线过长  实体不足25%
            return
 
        
        return True

    def next(self):
        date = self.data.datetime.date(0).strftime("%Y-%m-%d")
        low_band = self.boll.lines.bot[0]
        if date not in self.global_stats:
            self.global_stats[date] = { "buys": 0, "wins": 0, "losses": 0,  "Win$": 0, "Loss$": 0, "buy_symbols": [],"sell_symbols_win": [], "sell_symbols_loss": [],"extra_counter": 0} 
            
        
        if self.p.only_scan_last_day:
            if len(self) < 2 or self.data.datetime.date(0) != datetime.today().date():
               return
        # ================================================== Daily Monitor =========================================================
        if  not self.p.is_backtest and self.check_buy_signal():
           
            self.signal_today = True 
            
            logger = logging.getLogger(__name__)
            logger.info(f"[{date}] [OPTION] - BCS - VOL - {self.p.symbol} ")
            logger.info(f"|-----------> Volume: {round(self.data.volume[0] /self.vol_sma[0],2)} - Increase:{round((self.data.close[0] - self.data.open[0])/self.data.close[0] *100, 1)}%  ")
            return
            
            
        # =================================================== Backtest ==============================================================
        # ------------ 买入 ---------- 
        if  self.p.is_backtest and not self.ordered and  self.check_buy_signal():
           
            if date in SIGNAL_SPIKE_DATE:
                    return
          
            log_buy(self.global_stats,date, self.p.symbol)
 
            self.entry_price = self.data.close[0]   
            
            self.ordered = True
            self.is_targeted = False
            self.buy_date = self.data.datetime.date(0)
            self.targeted_date = get_target_time(self.buy_date).strftime("%Y-%m-%d")
            
            if  self.data.close[-1] > self.data.open[-1] and (self.data.close[-1] - self.data.open[-1]) /self.data.open[-1] > 0.05 and(self.data.close[0] - self.data.open[0]) /self.data.open[0] > 0.05:
                    self.global_stats[date]["extra_counter"] += 1
                    self.is_targeted = True

            self.buy()
            
             
        if  self.p.is_backtest and self.ordered and self.position:
             
            high = self.data.high[0]
            # ------------止损------------
            if  self.targeted_date  ==  self.data.datetime.date(0).strftime("%Y-%m-%d")  :
                
                if (self.p.printlog):
                    print("LOSS - OPTION - Bull Call S(vol) -", self.data.datetime.date(0))  
                    
                if high > self.entry_price * 0.99:
                    log_sell(self.global_stats,date, (300) , self.p.symbol)
                else:
                    log_sell(self.global_stats,date, (-2500), self.p.symbol)
                
                self.ordered = False
                self.close()
                return

            # ------------止盈------------
            if high >= self.entry_price *TAKE_PROFIT_PERCENT:
                log_sell(self.global_stats,date, (300) , self.p.symbol)
                if (self.p.printlog):
                    print("Win - OPTION - Bull Call S(vol) -", self.data.datetime.date(0)) 
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