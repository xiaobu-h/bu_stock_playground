import backtrader as bt
import pandas as pd
import logging
from strategy.attack_day.sensitive_param import VOLUME_MULTIPLIER,YESTERDAY_VOLUME_DECREASE_PERCENT ,LOOKBACK_DAYS,MIN_DROP_FROM_LATST_5_DAYS,STOP_LOSS_THRESHOLD,TAKE_PROFIT_PERCENT ,JUMP_HIGH_OPEN,MEGA7


ONE_TIME_SPENDING_ATTACK = 20000  # 每次买入金额


class AttackReversalStrategy(bt.Strategy):
    
 
    
    params = (
        ('only_scan_last_day', True),
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
        ('global_stats',{"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0, "buy_symbols": [], "sell_symbols": [], "extra_counter":0})
    )     

    def __init__(self):
        self.vol_sma5 = bt.indicators.SMA(self.data.volume, period=LOOKBACK_DAYS)
        self.stop_loss_price = 0.0
        self.entry_price = 0.0 
        self.signal_today = False
        self.global_stats= self.p.global_stats
        self.profile = None
        self.index = 1 if self.p.symbol in MEGA7 else 0
       
 
        
    def is_attack_setup(self):
        
        if self.data.close[0] <= self.data.open[0]:  
            return False
        
        if self.data.close[0] < (self.data.open[-1] * 0.995 ):     # 今天收盘 高于 昨天开盘
            return False
        
        
        if not (
            #self.data.close[-1] < self.data.close[-2] and   # 昨天收盘 低于 前天收盘
            self.data.close[-1] < self.data.open[-1] and    # 昨天是 阴线
            #self.data.close[-2] < self.data.open[-2] and    # 昨天是 阴线
            self.data.close[-1] < self.data.close[-3] and   # 昨天收盘 低于 大前天收盘
            self.data.close[-1] < self.data.close[-4] and   # 昨天收盘 低于 三天前收盘
            self.data.close[-1] < self.data.close[-5] and   # 昨天收盘 低于 四天前收盘
            self.data.low[-1] < self.data.low[-2]  
           # self.data.low[-1] < self.data.low[-3]  
           # self.data.low[-2] < self.data.low[-3]  
            
        ): 
            return False

        if  ((self.data.close[-5] - self.data.low[-1]) / self.data.low[-1] < MIN_DROP_FROM_LATST_5_DAYS[self.index] and
             (self.data.close[-6] - self.data.low[-1]) / self.data.low[-1] < MIN_DROP_FROM_LATST_5_DAYS[self.index] ):
            return False
   

        if self.data.volume[0] <= self.vol_sma5[0] * VOLUME_MULTIPLIER[self.index]:
            return False
        
        if (self.data.open[0] >  self.data.close[-1]) and ((self.data.open[0] - self.data.close[-1]) /self.data.close[-1] > JUMP_HIGH_OPEN[self.index] ): #跳空高开 小于x%
            return False

        if self.data.volume[0] < ( self.data.volume[-1] * YESTERDAY_VOLUME_DECREASE_PERCENT ) :
            return False 
        
        return True
    
    

    def next(self):
  
        date = self.data.datetime.date(0).strftime("%Y-%m-%d")
      
        if date not in self.global_stats:
            self.global_stats[date] = { "buys": 0, "wins": 0, "losses": 0,  "Win$": 0, "Loss$": 0, "buy_symbols": [],"sell_symbols": [],"extra_counter": 0} 
        
        
        # ======== 买入 ===========
        if not self.position:
            if date in ["2025-04-09", "2024-12-20" ,"2020-02-28", "2020-05-29", "2020-06-19",  "2020-11-30","2020-12-18","2021-01-06","2022-01-04","2022-03-18", "2022-06-17" ,"2022-06-24" ,"2023-04-27", "2024-08-05", "2024-08-06",
                            "2022-11-30", "2023-01-31", "2023-05-31" , "2023-11-30",  "2024-03-15" , "2024-05-31" , "2024-09-20", "2025-03-21" , "2025-04-07", "2025-05-30" , "2023-03-16","2023-10-03", "2025-03-11",
                            "2021-01-28", "2021-07-20" ,"2021-12-02","2022-01-10" ,"2022-01-24" ,"2022-02-24" ,"2022-04-28" ,"2022-04-25","2022-05-03" ,"2022-06-15", "2022-09-28", "2022-10-13","2023-03-13"]:
                    return
            
            if self.is_attack_setup(): 
                self.signal_today = True
                self.entry_price = self.data.close[0]
                today_increase = (self.data.close[0] - self.data.open[0]) /self.data.open[0]
                self.profile = TAKE_PROFIT_PERCENT[self.index] if today_increase < 0.07 else 1.038 
                #止盈
                #self.profile = TAKE_PROFIT_PERCENT 
                
                extra_message = "[MEGA7]" if self.index == 1  else "" 
                self.stop_loss_price = self.data.low[0]  * STOP_LOSS_THRESHOLD[self.index] if today_increase < 0.06 else  ( (self.data.open[0] + self.data.open[0] ) / 2)   #竹笋点
             
                logger = logging.getLogger(__name__)
                logger.info(f"[{self.data.datetime.date(0)}] {extra_message}Attack Day - {self.p.symbol} - win: {round(self.entry_price*TAKE_PROFIT_PERCENT[self.index], 3 )} - stop:{round(self.stop_loss_price, 3 )} ")
                      
                self.buy()  
                   
                # ==================== 统计 ====================
                self.global_stats[date]["buys"] += 1
                self.global_stats[date]["buy_symbols"].append(self.p.symbol)
                # ==============================================
                return
 
        if self.position:
            today_increase = (self.data.close[0] - self.data.open[0]) /self.data.open[0]
           
            # ======= 止损 ===========
            if   (self.data.low[0] < self.stop_loss_price): 
              
                # ==================== 统计 ====================
                self.global_stats[date]["losses"] += 1
                size = int(ONE_TIME_SPENDING_ATTACK / self.entry_price)
                self.global_stats[date]["Loss$"] -= size * (self.entry_price - self.stop_loss_price)
                self.global_stats[date]["sell_symbols"].append(self.p.symbol)
                # ==============================================
                self.close()
                return
            
             # ======== 止盈 ===========
            if   (self.data.high[0] >= self.entry_price * self.profile) :
                # ==================== 统计 ====================
                self.global_stats[date]["wins"] += 1  
                self.global_stats[date]["Win$"] += ONE_TIME_SPENDING_ATTACK * (self.profile - 1)
                self.global_stats[date]["sell_symbols"].append(self.p.symbol)
                # ==============================================
                 
                self.close()
                return
                
              
              