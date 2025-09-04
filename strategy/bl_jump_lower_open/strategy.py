import backtrader as bt
from datetime import datetime 

from collections import defaultdict
import csv
import logging


ONE_TIME_SPENDING_BOLLINGER = 20000  # 每次买入金额


class BollingerVolumeBreakoutLogic:
    def __init__(self, data, lookback_days, volume_multiplier):
        self.data = data
        self.lookback_days = lookback_days
        self.volume_multiplier = volume_multiplier
        self.boll = bt.indicators.BollingerBands(self.data.close, period=20, devfactor=2)
        self.vol_sma = bt.indicators.SimpleMovingAverage(self.data.volume, period=self.lookback_days)
        self.balance_by_date = defaultdict(float)
        self.size = 0
        
    def check_buy_signal(self): 
        if len(self.data) < self.lookback_days:
            return False
        open_ = self.data.open[0]
        close = self.data.close[0]
        low_band = self.boll.lines.bot[0]
        volume = self.data.volume[0]
        avg_volume = self.vol_sma[0]
        
        if close <  open_:    # must be a green candle
            return False
        
        if (close < low_band)  | (open_ >= low_band ):  # cross over Bollinger low band
            return False
        
        if ((low_band - open_) / low_band) < 0.005:    # 下穿的比较深
            return False
        
        if volume < avg_volume * self.volume_multiplier:   #放量
            return False
        
        if (close - self.data.low[-1]) / self.data.low[-1]  > 0.05 :   # 止损太低 - 风险过高
            return False
         
        return True
    
class BollingerVolumeBreakoutStrategy(bt.Strategy):
    params = (
        ('lookback_days', 10),
        ('volume_multiplier', 1.3),
        ('only_scan_last_day', True),
        ('take_profit', 1.026),
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
    )
    
    global_stats = defaultdict(lambda: {"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0})


    def __init__(self):
        self.signal_today = False
        self.order = None
        self.entry_price = None
        self.buy_logic = BollingerVolumeBreakoutLogic(
            self.data,
            lookback_days=self.p.lookback_days,
            volume_multiplier=self.p.volume_multiplier
        )   
        self.daily_stats = defaultdict(lambda: {"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0})


    def next(self):
        date = self.data.datetime.date(0).strftime("%Y-%m-%d")
        
        if self.p.only_scan_last_day:
            if len(self) < 2 or self.data.datetime.date(0) != datetime.today().date():
               return
           
           
        if  self.position:
            high = self.data.high[0]
            low = self.data.low[0]
            if high >= self.entry_price * (self.p.take_profit):
                
                # ==================== 统计 ====================
                self.daily_stats[date]["wins"] += 1
                BollingerVolumeBreakoutStrategy.global_stats[date]["wins"] += 1  # 累加到全局
                self.daily_stats[date]["Win$"] += ONE_TIME_SPENDING_BOLLINGER * (self.p.take_profit - 1)
                BollingerVolumeBreakoutStrategy.global_stats[date]["Win$"] += ONE_TIME_SPENDING_BOLLINGER * (self.p.take_profit - 1)
                

                self.close()
                return
            if low < self.stop_price:
                
                size = int(ONE_TIME_SPENDING_BOLLINGER / self.entry_price)
                if self.data.datetime.date(0).strftime("%Y-%m-%d") in[ "2025-04-08" , "2025-04-16"]:
                    print ("stop hit on ", self.data.datetime.date(0).strftime("%Y-%m-%d") , " for ", self.p.symbol)
                    print(size * (self.entry_price - self.stop_price))
                    
                
                # ==================== 统计 ====================
                self.daily_stats[date]["losses"] += 1
                BollingerVolumeBreakoutStrategy.global_stats[date]["losses"] += 1
                
                self.daily_stats[date]["Loss$"] -= size * (self.entry_price - self.stop_price)
                BollingerVolumeBreakoutStrategy.global_stats[date]["Loss$"] -= size * (self.entry_price - self.stop_price)
                # ==============================================
                 
                self.close()
                return

        if self.buy_logic.check_buy_signal():
            logger = logging.getLogger(__name__)
            logger.info(f"[{self.data.datetime.date(0)}] Bollinger Jump - {self.p.symbol}")
            self.signal_today = True
            if not self.p.only_scan_last_day:
                #if self.data.datetime.date(0).strftime("%Y-%m-%d") in ["2024-12-20" ,"2020-02-28", "2020-05-29", "2020-06-19",  "2020-11-30","2020-12-18","2021-01-06","2022-01-04","2022-03-18", "2022-06-17" ,
                 #                                                  "2022-06-24" , "2022-11-30", "2023-01-31", "2023-05-31" , "2023-11-30",  "2024-03-15" , "2024-05-31" , "2024-09-20", "2025-03-21" , "2025-04-07", "2025-05-30"  ]:
                 #   return
                # ==================== 统计 ====================
                self.daily_stats[date]["buys"] += 1
                BollingerVolumeBreakoutStrategy.global_stats[date]["buys"] += 1
                # ==============================================
                 
                self.order = self.buy( )
                self.entry_price = self.data.close[0]
                self.stop_price = self.data.low[0] * 0.98 # 初始止损价设为买入价的 98.5%
     
    @classmethod
    def export_global_csv(cls, filepath: str):
       
        rows = []
        total_wins = 0
        total_losses = 0
        total_buys = 0
        total_win_money = 0
        total_loss_money = 0

        for month in sorted(cls.global_stats.keys()):
            wins = cls.global_stats[month]["wins"]
            losses = cls.global_stats[month]["losses"]
            trades = wins + losses
            win_rate = (wins / trades) if trades > 0 else 0.0

            rows.append({
                "month": month,
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 3),  # 保留4位小数，方便后续报表
                "closed_trades": trades,
                "buys": cls.global_stats[month]["buys"],
                "net_earn$": round(cls.global_stats[month]["Win$"]+ cls.global_stats[month]["Loss$"],2),
    
            })

            total_wins += wins
            total_losses += losses
            total_buys += cls.global_stats[month]["buys"]
            total_win_money += cls.global_stats[month]["Win$"]
            total_loss_money += cls.global_stats[month]["Loss$"]

        # 写 CSV
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["month", "wins", "losses", "win_rate", "closed_trades", "buys", "net_earn$"])
            writer.writeheader()
            writer.writerows(rows)

        # 控制台 summary
        print("----- SUMMARY -----")
        net_profit = round(total_win_money + total_loss_money,2) 
        print(f"Total buys={total_buys} | Total Wins$ = {round(total_win_money,2)} | Total Loss $={round(total_loss_money,2)}  | Net P/L $={net_profit}")

        print(f"Total Wins={total_wins} | Total Losses={total_losses} | Overall WinRate={total_wins / (total_wins + total_losses) if (total_wins + total_losses) > 0 else 0.0:.2f}")

        return total_buys, net_profit
    
    
    
     