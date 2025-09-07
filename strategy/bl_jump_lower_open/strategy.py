import backtrader as bt
from datetime import datetime 
from collections import defaultdict
import logging
from strategy.bl_jump_lower_open.sensitive_param import LOOKBACK_DAYS, VOLUME_MULTIPLIER, TAKE_PROFIT_PERCENT, STOP_LOSS_THRESHOLD, MAX_JUMP_DOWN_PERCENT, CROSS_DEEP_PCT, MIN_TOTAL_INCREASE_PERCENT


ONE_TIME_SPENDING_BOLLINGER = 20000  # 每次买入金额


class BollingerVolumeBreakoutStrategy(bt.Strategy):
    params = (
        ('only_scan_last_day', True),
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
        ('global_stats',{"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0, "buy_symbols": [], "sell_symbols": []})
    )
    


    def __init__(self):
        self.boll = bt.indicators.BollingerBands(self.data.close, period=20, devfactor=2)
        self.vol_sma = bt.indicators.SimpleMovingAverage(self.data.volume, period=LOOKBACK_DAYS)
        self.balance_by_date = defaultdict(float)
        self.size = 0
        self.signal_today = False
        self.order = None
        self.entry_price = None
        self.zhusun_price = None   
        self.global_stats = self.p.global_stats
       

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
        
        if (close < low_band)  | (open_ >= low_band ):  # cross over Bollinger low band
            return False
        
        if ((low_band - open_) / low_band) < CROSS_DEEP_PCT:     
            return False
        
        if volume < avg_volume * VOLUME_MULTIPLIER:   #放量
            return False
        
        if abs(close - open_) <  open_ *  MIN_TOTAL_INCREASE_PERCENT:    # 小于涨幅 bar
           
            return False
        
        if (close - self.data.low[-1]) / self.data.low[-1]  > MAX_JUMP_DOWN_PERCENT :   
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
            high = self.data.high[0]
            low = self.data.low[0]
            
            # 止盈
            if high >= self.entry_price * TAKE_PROFIT_PERCENT:
                
                # ==================== 统计 ====================
                self.global_stats[date]["wins"] += 1  
                self.global_stats[date]["Win$"] += ONE_TIME_SPENDING_BOLLINGER * (TAKE_PROFIT_PERCENT - 1)
                self.global_stats[date]["sell_symbols"].append(self.p.symbol)
                # ==============================================
                self.close()
                return
            
            # 止损
            if low < self.zhusun_price:
                
                size = int(ONE_TIME_SPENDING_BOLLINGER / self.entry_price)
                  
                
                # ==================== 统计 ====================
                self.global_stats[date]["losses"] += 1
                self.global_stats[date]["Loss$"] -= size * (self.entry_price - self.zhusun_price)
                self.global_stats[date]["sell_symbols"].append(self.p.symbol)
                # ==============================================
                 
                self.close()
                return

        if self.check_buy_signal():
            self.signal_today = True
             
            #if self.data.datetime.date(0).strftime("%Y-%m-%d") in ["2024-12-20" ,"2020-02-28", "2020-05-29", "2020-06-19",  "2020-11-30","2020-12-18","2021-01-06","2022-01-04","2022-03-18", "2022-06-17" ,
                  #                                                "2022-06-24" , "2022-11-30", "2023-01-31", "2023-05-31" , "2023-11-30",  "2024-03-15" , "2024-05-31" , "2024-09-20", "2025-03-21" , "2025-04-07", "2025-05-30"  ]:
               #    return
            # ==================== 统计 ====================
            
            self.global_stats[date]["buys"] += 1
            self.global_stats[date]["buy_symbols"].append(self.p.symbol)
            # ==============================================
                
            self.order = self.buy( )
            self.entry_price = self.data.close[0]
            self.zhusun_price = self.data.low[0] * STOP_LOSS_THRESHOLD
            logger = logging.getLogger(__name__)
            logger.info(f"[{self.data.datetime.date(0)}] Bollinger Jump - {self.p.symbol} - win: {round(self.entry_price*TAKE_PROFIT_PERCENT, 3 )} - stop:{round(self.zhusun_price, 3 )}")
            
     
           
     