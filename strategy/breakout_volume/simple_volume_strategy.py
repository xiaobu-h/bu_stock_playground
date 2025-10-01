import backtrader as bt
from datetime import datetime ,time
import pandas as pd
import logging  
import pandas_market_calendars as mcal
from strategy.breakout_volume.sensitive_param import MAX_JUMP_DOWN_PERCENT, VOLUME_FOR_QUADRUPLE_WITCH_DAY,VOLUME_MULTIPLIER ,MEGA7, SMA_DAYS,MIN_TOTAL_INCREASE_PERCENT,ZHUSUN_PERCENT  , STOP_LOSS_THRESHOLD, TAKE_PROFIT_PERCENT_SMALL,TAKE_PROFIT_PERCENT_LARGE ,BAR 
from strategy.strategy_util import SIGNAL_SPIKE_DATE , is_quadruple_witching , log_buy, log_sell


ONE_TIME_SPENDING = 20000  # 每次买入金额
   
class SimpleVolumeStrategy(bt.Strategy):

    params = (
        ('only_scan_last_day', True),
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
        ('global_stats',{"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0, "buy_symbols": [], "sell_symbols": [], "extra_counter":0}),
        ('is_backtest', False),
        ('is_hourly_backtest', False),
    )
        
    
    def __init__(self): 
        self.symbol = self.p.symbol
        self.data_mins = self.datas[0]
        self.data_daily =  self.datas[1] if self.p.is_hourly_backtest else self.datas[0]
        
        self.boll = bt.indicators.BollingerBands(self.data.close, period=20, devfactor=2)
        
        self.order = None
        self.entry_price = None
        self.zhusun_price = None 
        self.vol_sma = bt.indicators.SimpleMovingAverage(self.data_daily.volume, period=SMA_DAYS)
        self.vol_sma5 = bt.indicators.SimpleMovingAverage(self.data.volume, period=5)  # for logging
        self.vol_sma30 = bt.indicators.SimpleMovingAverage(self.data.volume, period=30) # for logging
        self.signal_today = False
        self.profile_rate = None
        self.global_stats= self.p.global_stats
        self.buy_date = None
        self.is_targeted = False
        self.index = 1 if self.p.symbol in MEGA7 else 0
        

    
    def check_buy_signal(self): 
        open_ = self.data_daily.open[0]
        close = self.data_daily.close[0] 
        volume = self.data_daily.volume[0] 
        if close < open_:
            return False
        
        if abs(close - open_) <  (open_ *  MIN_TOTAL_INCREASE_PERCENT[self.index]):    # 小于涨幅 bar
            #print(f"[{self.data_daily.datetime.date(0)}]Candle increase is too small.")
            return False
        
        vol = VOLUME_FOR_QUADRUPLE_WITCH_DAY[self.index] if is_quadruple_witching(self.data_daily.datetime.date(0)) else VOLUME_MULTIPLIER[self.index]
        
         
        if  volume < self.vol_sma[0] * vol : # 交易量放量倍数 
           # print(f"[{self.data_daily.datetime.date(0)}]Volume is not a spike.")
            return False
        
        if  ( self.data_daily.close[0] - (self.data_daily.low[0] *ZHUSUN_PERCENT )) / self.data_daily.close[0] < 0.03  :    # 竹笋点 3% 之内 失败率太高不考虑
            return 
        
        
        if   (self.data_daily.close[0] - self.data_daily.open[0]) / (self.data_daily.high[0] - self.data_daily.low[0]) < 0.25 :   # 如果上影线或下影线过长  实体不足25%
            return
            
            
        #  从昨天最低点 到今天收盘 没有跳空下跌4%以上    -  
        if (self.data_daily.low[-1]  > close) and ((self.data_daily.low[-1] - close) > (self.data_daily.close[-1] * MAX_JUMP_DOWN_PERCENT[self.index])):   
            #print(f"[{self.data_daily.datetime.date(0)}]Jump down too much.")
            return False
        
        
         
        if  min(self.data_daily.low[0] , self.data_daily.low[-1] ) < (close * STOP_LOSS_THRESHOLD[self.index]):   
            #print("STOP_LOSS_THRESHOLD")
            return False 
     
        return True
    
    
    def next(self): 
        date = self.data_daily.datetime.date(0).strftime("%Y-%m-%d")
        sell_date =  self.data_mins.datetime.date(0).strftime("%Y-%m-%d")
         
        if date not in self.global_stats:
            self.global_stats[date] = { "buys": 0, "wins": 0, "losses": 0,  "Win$": 0, "Loss$": 0, "buy_symbols": [],"sell_symbols": [],"extra_counter": 0} 
              
        if self.p.only_scan_last_day:
            if len(self) < 2 or self.data_daily.datetime.date(0) != datetime.today().date():
               return
 
        # ================================================== Daily Monitor =========================================================
        if  not self.p.is_backtest and self.check_buy_signal():
            
            self.signal_today = True 
            logger = logging.getLogger(__name__)
            today_increase = (self.data_daily.close[0] - self.data_daily.open[0]) /self.data_daily.open[0]
            profile_rate = TAKE_PROFIT_PERCENT_SMALL[self.index] if today_increase < BAR else TAKE_PROFIT_PERCENT_LARGE[self.index]
            zhusun_price =  self.data_daily.low[0] * ZHUSUN_PERCENT # 竹笋点 
            extra_message = "[MEGA7]" if self.index == 1  else "" 
            logger.info(f"[{self.data_daily.datetime.date(0)}] VOL x 2 - {extra_message} {self.p.symbol} - win: {round(self.data_daily.close[0] * profile_rate, 3 )} - stop:{round(zhusun_price, 3 )} ")
            logger.info(f"|-----------> Vol of 5: {round(self.data.volume[0] /self.vol_sma5 [0],2)} - Vol of 30: {round(self.data.volume[0] /self.vol_sma30[0],2)} - Increase:{round((self.data.close[0] - self.data.open[0])/self.data.close[0] *100, 1)}% - Stop%:{round(100 - zhusun_price/self.data_daily.close[0]*100, 2)}%")
            
            return 
        
        
        # =================================================== Backtest ============================================================== 
        if not self.p.is_hourly_backtest or (self.data_mins.datetime.time(0) == time(13, 00) or self.data_mins.datetime.time(0) == time(13, 30)  or self.data_mins.datetime.time(0) == time(14, 30) ) :
            if  self.p.is_backtest and not self.position  and self.check_buy_signal():
                self.is_targeted = False
 
                if date in SIGNAL_SPIKE_DATE:
                    return
                
                today_increase = (self.data_daily.close[0] - self.data_daily.open[0]) /self.data_daily.open[0]
                self.profile_rate = TAKE_PROFIT_PERCENT_SMALL[self.index] if today_increase < BAR else TAKE_PROFIT_PERCENT_LARGE[self.index]
                self.entry_price = self.data_daily.close[0]
                self.zhusun_price = self.data_daily.low[0] * ZHUSUN_PERCENT   # 竹笋点 
                self.buy_date = self.data_daily.datetime.date(0).strftime("%Y-%m-%d")
                
                
                 
                band = self.boll.lines.bot[0]
              #  if    today_increase> 0.03  and  self.data_daily.volume[-1] * 2.3 < self.data_daily.volume[0] and( self.data_daily.close[-1] >  self.data_daily.open[-1] ) and ( self.data_daily.high[0] -  self.data_daily.close[0] ) * 1.2 > (self.data_daily.close[0]  - self.data_daily.open[0] ) :
               # 上阴险 if  (self.data_daily.high[0] - self.data_daily.close[0] ) > ((self.data_daily.close[0] - self.data_daily.open[0] )* 0.5)     :
                #  在上印象之上   if   ( self.data_daily.open[0] > band  )  and  ( self.data_daily.open[0] < band * 1.01)     :   69%
                    
                if   ( self.data_daily.close[0] - (self.data_daily.low[0] *ZHUSUN_PERCENT )) / self.data_daily.close[0]  >= 0.07 :   # 竹笋点 2.5% 之内
                    self.global_stats[date]["extra_counter"] += 1
                    self.is_targeted = True
            
                log_buy(self.global_stats, date, self.p.symbol)
          

                # 重复添加 止盈止损判断 以统计 第二天第一个小时的bar  因为在 self.buy()之后 这个bar会被跳过
                if self.p.is_hourly_backtest:
                    if self.data_mins.low[0] < self.zhusun_price:   
                        size = int(ONE_TIME_SPENDING / self.entry_price)
                        log_sell(global_stats=self.global_stats, date = sell_date, net_change=(-size * (self.entry_price - self.zhusun_price)) ,symbol=self.p.symbol)
                        return
                        
                    if  self.data_mins.high[0]  > self.entry_price * self.profile_rate:
                        log_sell(global_stats=self.global_stats, date = sell_date, net_change= ONE_TIME_SPENDING * (self.profile_rate - 1) ,symbol=self.p.symbol)
                        return
            
                self.order = self.buy()    
        
        if  self.p.is_backtest and (self.position.size > 0 ): 
        
         
             # 止损
            if self.data_mins.low[0] < self.zhusun_price:  
                 
                size = int(ONE_TIME_SPENDING / self.entry_price) 
                log_sell(global_stats=self.global_stats, date = sell_date, net_change=(-size * (self.entry_price - self.zhusun_price)) ,symbol=self.p.symbol)
                 
                if (self.p.printlog):
                    print("LOSS - VOL * 2 -", self.data_daily.datetime.date(0))
                self.close()
                return
               
            # 止盈
            if  self.data_mins.high[0]  > self.entry_price * self.profile_rate:
              
                if self.is_targeted:
                    self.global_stats[date]["extra_counter"] += 1000000
                    
                    
                log_sell(global_stats=self.global_stats, date = sell_date, net_change= ONE_TIME_SPENDING * (self.profile_rate - 1) ,symbol=self.p.symbol)
        
                self.close()
                if (self.p.printlog):
                    print("Win - VOL * 2 -", self.data_daily.datetime.date(0))
                return
            
            '''
            # 第二天收盘 就平仓   已测试 1 - 6 天 大幅提高失败率
            if self.data_mins.datetime.time(0) == time(19, 00) and get_target_time(self.buy_date).strftime("%Y-%m-%d")  ==  self.data_mins.datetime.date(0).strftime("%Y-%m-%d")  :
 
                if self.data_mins.close[0] > self.entry_price:
                        
                    # ==================== 统计 ====================
                    self.global_stats[sell_date]["wins"] += 1  # 累加到全局
                    
                    size = int(ONE_TIME_SPENDING / self.entry_price)
                    self.global_stats[sell_date]["Win$"] += size * abs(self.entry_price - self.data_mins.close[0])
                    self.global_stats[sell_date]["sell_symbols"].append(self.p.symbol)
                    # ==============================================
                    self.close()
                    return
                else:
                     # ==================== 统计 ====================
                    self.global_stats[sell_date]["losses"] += 1
                    size = int(ONE_TIME_SPENDING / self.entry_price)
                    self.global_stats[sell_date]["Loss$"] -= size * (self.entry_price - self.data_mins.close[0])
                    self.global_stats[sell_date]["sell_symbols"].append(self.p.symbol)
                    # ==============================================
                    self.close()
                    return
             '''
   
                
        
  
# 定时卖出 helper function
def get_target_time(date):
    
    # 交易所日历（这里用 NYSE）
    nyse = mcal.get_calendar("XNYS")
    base = pd.Timestamp(date) 
    end = base + pd.Timedelta(days=12)
    # 取出从 date 往后 10 天的交易日
    schedule = nyse.schedule(start_date=base, end_date=end)
    trading_days = mcal.date_range(schedule, frequency="1D")

    target_day = trading_days[6]  #  [0]当天 [1]第二个交易日

    target_time = pd.Timestamp(target_day.date()) + pd.Timedelta(hours=13) 
    return target_time


