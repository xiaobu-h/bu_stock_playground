import backtrader as bt
from datetime import datetime ,time
import pandas as pd
import logging  
import pandas_market_calendars as mcal
from strategy.breakout_volume.sensitive_param import MAX_JUMP_DOWN_PERCENT, VOLUME_FOR_QUADRUPLE_WITCH_DAY,VOLUME_MULTIPLIER ,MEGA7, SMA_DAYS,MIN_TOTAL_INCREASE_PERCENT,ZHUSUN_PERCENT  , STOP_LOSS_THRESHOLD, TAKE_PROFIT_PERCENT_SMALL,TAKE_PROFIT_PERCENT_LARGE ,BAR 

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
        self.order = None
        self.entry_price = None
        self.zhusun_price = None 
        self.vol_sma = bt.indicators.SimpleMovingAverage(self.data_daily.volume, period=SMA_DAYS)
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
            return 
        
        
        # =================================================== Backtest ============================================================== 
        if not self.p.is_hourly_backtest or (self.data_mins.datetime.time(0) == time(13, 00) or self.data_mins.datetime.time(0) == time(13, 30)  or self.data_mins.datetime.time(0) == time(14, 30) ) :
            if  self.p.is_backtest and not self.position  and self.check_buy_signal():
                self.is_targeted = False
 
                if date in ["2025-04-09", "2024-12-20" ,"2020-02-28", "2020-05-29", "2020-06-19",  "2020-11-30","2020-12-18","2021-01-06","2022-01-04","2022-03-18", "2022-06-17" ,"2022-06-24" ,"2023-04-27", "2024-08-05", "2024-08-06",
                            "2022-11-30", "2023-01-31", "2023-05-31" , "2023-11-30",  "2024-03-15" , "2024-05-31" , "2024-09-20", "2025-03-21" , "2025-04-07", "2025-05-30" , "2023-03-16","2023-10-03", "2025-03-11",
                            "2021-01-28", "2021-07-20" ,"2021-12-02","2022-01-10" ,"2022-01-24" ,"2022-02-24" ,"2022-04-28" ,"2022-04-25","2022-05-03" ,"2022-06-15", "2022-09-28", "2022-10-13","2023-03-13"]:
                    return
                
                today_increase = (self.data_daily.close[0] - self.data_daily.open[0]) /self.data_daily.open[0]
                self.profile_rate = TAKE_PROFIT_PERCENT_SMALL[self.index] if today_increase < BAR else TAKE_PROFIT_PERCENT_LARGE[self.index]
                self.entry_price = self.data_daily.close[0]
                
              
         
                
                self.zhusun_price = self.data_daily.low[0] * ZHUSUN_PERCENT   # 竹笋点 
                self.buy_date = self.data_daily.datetime.date(0).strftime("%Y-%m-%d")
                
                
              #  if    today_increase> 0.03  and  self.data_daily.volume[-1] * 2.3 < self.data_daily.volume[0] and( self.data_daily.close[-1] >  self.data_daily.open[-1] ) and ( self.data_daily.high[0] -  self.data_daily.close[0] ) * 1.2 > (self.data_daily.close[0]  - self.data_daily.open[0] ) :
                if  (self.data_daily.close[0] - self.data_daily.low[0]) /self.data_daily.low[0] < 0.07:
                    self.global_stats[date]["extra_counter"] += 1
                    self.is_targeted = True
            
                
                # ==================== 统计 ====================
                self.global_stats[date]["buys"] += 1
                self.global_stats[date]["buy_symbols"].append(self.p.symbol)
                # ==============================================
            

                # 重复添加 止盈止损判断 以统计 第二天第一个小时的bar  因为在 self.buy()之后 这个bar会被跳过
                if self.p.is_hourly_backtest:
                    if self.data_mins.low[0] < self.zhusun_price:  
                        self.global_stats[sell_date]["losses"] += 1
                        size = int(ONE_TIME_SPENDING / self.entry_price)
                        self.global_stats[sell_date]["Loss$"] -= size * (self.entry_price - self.zhusun_price)
                        self.global_stats[sell_date]["sell_symbols"].append(self.p.symbol) 
                        return
                        
                    if  self.data_mins.high[0]  > self.entry_price * self.profile_rate:
                        self.global_stats[sell_date]["wins"] += 1  
                        self.global_stats[sell_date]["Win$"] += ONE_TIME_SPENDING * (self.profile_rate - 1)
                        self.global_stats[sell_date]["sell_symbols"].append(self.p.symbol) 
                        return
            
                self.order = self.buy()    
        
        if  self.p.is_backtest and (self.position.size > 0 ): 
        
            
            # 止盈
            if  self.data_mins.high[0]  > self.entry_price * self.profile_rate:
              
                if self.is_targeted:
                    
                    self.global_stats[date]["extra_counter"] += 1000000
                # ==================== 统计 ====================
                self.global_stats[sell_date]["wins"] += 1  # 累加到全局
                self.global_stats[sell_date]["Win$"] += ONE_TIME_SPENDING * (self.profile_rate - 1)
                self.global_stats[sell_date]["sell_symbols"].append(self.p.symbol)
                # ==============================================
                self.close()
                return
             # 止损
            if self.data_mins.low[0] < self.zhusun_price:  
                
                # ==================== 统计 ====================
                self.global_stats[sell_date]["losses"] += 1
                size = int(ONE_TIME_SPENDING / self.entry_price)
                self.global_stats[sell_date]["Loss$"] -= size * (self.entry_price - self.zhusun_price)
                self.global_stats[sell_date]["sell_symbols"].append(self.p.symbol)
                # ==============================================
                self.close()
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
   
                
        
        
             
# 是否是四巫日       
def is_quadruple_witching(date) -> bool:
    #"""仅按规则：3/6/9/12 月的第3个周五（不考虑休市调整）"""
    d = pd.Timestamp(date).tz_localize(None).normalize()
    if d.month not in (3, 6, 9, 12):
        return False 
    third_fris = pd.date_range(start=f'{d.year}-01-01',
                               end=f'{d.year}-12-31',
                               freq='WOM-3FRI').normalize()
    return d in third_fris


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


