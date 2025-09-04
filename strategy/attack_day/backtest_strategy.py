import backtrader as bt
import pandas as pd

import csv 
from collections import defaultdict

ONE_TIME_SPENDING_ATTACK = 20000  # 每次买入金额


class AttackReversalStrategy(bt.Strategy):
    
    global_stats = defaultdict(lambda: {"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0})

    params = (
        ('lookback_days', 6),         
        ('volume_multiplier', 1.35),  # 放量倍数
        ('take_profit', 1.045),   # 止盈目标 
        ('min_drop_from_5_days_ago', 0.1),  # 累计下跌超过10%
        ('stop_loss_pct', 0.965),   # 竹笋点
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
    )     

    def __init__(self):
        
        self.vol_sma5 = bt.indicators.SMA(self.data.volume, period=self.p.lookback_days)
        self.stop_loss_price = 0.0
        self.buy_price = 0.0 
        self.daily_stats = defaultdict(lambda: {"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0})

       
       
 
        
    def is_attack_setup(self):
        date = self.data.datetime.date(0)
        if not (
            self.data.close[-1] < self.data.close[-2] and
            self.data.close[-1] < self.data.open[-1] and
            self.data.close[-1] < self.data.close[-3] and
            self.data.close[-1] < self.data.close[-4] and
            self.data.close[-1] < self.data.close[-5] 
        ): 
            return False

        if  ( (self.data.close[-5] - self.data.low[-1]) / self.data.low[-1] < self.p.min_drop_from_5_days_ago and
             (self.data.close[-6] - self.data.low[-1]) / self.data.low[-1] < self.p.min_drop_from_5_days_ago ):
            return False
         
        
        if self.data.close[0] <= self.data.open[0]: 
            return False

        if self.data.volume[0] <= self.vol_sma5[0] * self.p.volume_multiplier:
            return False

        return True
    
    

    def next(self):
        date = self.data.datetime.date(0).strftime("%Y-%m-%d")
       
       
        # ======== 买入 ===========
        if not self.position:
            if self.data.datetime.date(0).strftime("%Y-%m-%d") in ["2025-04-09", "2024-12-20" ,"2020-02-28", "2020-05-29", "2020-06-19",  "2020-11-30","2020-12-18","2021-01-06","2022-01-04","2022-03-18", "2022-06-17" ,
                                                                   "2022-06-24" , "2022-11-30", "2023-01-31", "2023-05-31" , "2023-11-30",  "2024-03-15" , "2024-05-31" , "2024-09-20", "2025-03-21" , "2025-04-07", "2025-05-30"  ]:
               return
            
            if self.is_attack_setup(): 
                self.buy_price = self.data.close[0]
                self.stop_loss_price = self.data.low[0]  * self.p.stop_loss_pct       
                self.buy()  
                   
                # ==================== 统计 ====================
                self.daily_stats[date]["buys"] += 1
                AttackReversalStrategy.global_stats[date]["buys"] += 1
                # ==============================================
                
 
        if self.position:
            
             # ======== 止盈 ===========
            if   (self.data.high[0] >= self.buy_price * self.p.take_profit) :
                # ==================== 统计 ====================
                self.daily_stats[date]["wins"] += 1
                AttackReversalStrategy.global_stats[date]["wins"] += 1  # 累加到全局
                self.daily_stats[date]["Win$"] += ONE_TIME_SPENDING_ATTACK * (self.p.take_profit - 1)
                AttackReversalStrategy.global_stats[date]["Win$"] += ONE_TIME_SPENDING_ATTACK * (self.p.take_profit - 1)
                # ==============================================
                 
                self.close()
                return
                
            # ======= 止损 ===========
            if   (self.data.low[0] < self.stop_loss_price): 
              
                # ==================== 统计 ====================
                self.daily_stats[date]["losses"] += 1
                AttackReversalStrategy.global_stats[date]["losses"] += 1
                size = int(ONE_TIME_SPENDING_ATTACK / self.buy_price)
                self.daily_stats[date]["Loss$"] -= size * (self.buy_price - self.stop_loss_price)
                AttackReversalStrategy.global_stats[date]["Loss$"] -= size * (self.buy_price - self.stop_loss_price)
                # ==============================================
                self.close()
                return
            
    
 
            
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
    