import backtrader as bt
import pandas as pd
import csv 
import logging
from collections import defaultdict
from strategy.attack_day.sensitive_param import VOLUME_MULTIPLIER,YESTERDAY_VOLUME_DECREASE_PERCENT ,LOOKBACK_DAYS,MIN_DROP_FROM_LATST_5_DAYS,STOP_LOSS_THRESHOLD,TAKE_PROFIT_PERCENT 


ONE_TIME_SPENDING_ATTACK = 20000  # 每次买入金额


class AttackReversalStrategy(bt.Strategy):
    
    global_stats = defaultdict(lambda: {"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0, "buy_symbols": [], "sell_symbols": []})

    
    params = (
        ('only_scan_last_day', True),
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
    )     

    def __init__(self):
        self.vol_sma5 = bt.indicators.SMA(self.data.volume, period=LOOKBACK_DAYS)
        self.stop_loss_price = 0.0
        self.buy_price = 0.0 
        self.signal_today = False
       
       
 
        
    def is_attack_setup(self):
        
        if not (
            self.data.close[-1] < self.data.close[-2] and
            self.data.close[-1] < self.data.open[-1] and
            self.data.close[-1] < self.data.close[-3] and
            self.data.close[-1] < self.data.close[-4] and
            self.data.close[-1] < self.data.close[-5] 
        ): 
            return False

        if  ( (self.data.close[-5] - self.data.low[-1]) / self.data.low[-1] < MIN_DROP_FROM_LATST_5_DAYS and
             (self.data.close[-6] - self.data.low[-1]) / self.data.low[-1] < MIN_DROP_FROM_LATST_5_DAYS ):
            return False
         
        
        if self.data.close[0] <= self.data.open[0]: 
            return False

        if self.data.volume[0] <= self.vol_sma5[0] * VOLUME_MULTIPLIER:
            return False


        if self.data.volume[0] < ( self.data.volume[-1] * YESTERDAY_VOLUME_DECREASE_PERCENT ) :
            return False
        
        
        return True
    
    

    def next(self):
  
        date = self.data.datetime.date(0).strftime("%Y-%m-%d")
      
        if date not in AttackReversalStrategy.global_stats:
            AttackReversalStrategy.global_stats[date] = {"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0, "buy_symbols": [], "sell_symbols": []}
        
        
        # ======== 买入 ===========
        if not self.position:
            if self.data.datetime.date(0).strftime("%Y-%m-%d") in ["2025-04-09", "2024-12-20" ,"2020-02-28", "2020-05-29", "2020-06-19",  "2020-11-30","2020-12-18","2021-01-06","2022-01-04","2022-03-18", "2022-06-17" ,
                                                                   "2022-06-24" , "2022-11-30", "2023-01-31", "2023-05-31" , "2023-11-30",  "2024-03-15" , "2024-05-31" , "2024-09-20", "2025-03-21" , "2025-04-07", "2025-05-30"  ]:
               return
            
            if self.is_attack_setup(): 
                self.signal_today = True
                self.buy_price = self.data.close[0]
                self.stop_loss_price = self.data.low[0]  * STOP_LOSS_THRESHOLD 
                
                logger = logging.getLogger(__name__)
                logger.info(f"[{self.data.datetime.date(0)}] Attack Day - {self.p.symbol} - win: {round(self.buy_price*TAKE_PROFIT_PERCENT, 3 )} - stop:{round(self.stop_loss_price, 3 )} ")
                      
                self.buy()  
                   
                # ==================== 统计 ====================
                AttackReversalStrategy.global_stats[date]["buys"] += 1
                AttackReversalStrategy.global_stats[date]["buy_symbols"].append(self.p.symbol)
                # ==============================================
                return
 
        if self.position:
            
             # ======== 止盈 ===========
            if   (self.data.high[0] >= self.buy_price * TAKE_PROFIT_PERCENT) :
                # ==================== 统计 ====================
                AttackReversalStrategy.global_stats[date]["wins"] += 1  # 累加到全局
                AttackReversalStrategy.global_stats[date]["Win$"] += ONE_TIME_SPENDING_ATTACK * (TAKE_PROFIT_PERCENT - 1)
                AttackReversalStrategy.global_stats[date]["sell_symbols"].append(self.p.symbol)
                # ==============================================
                 
                self.close()
                return
                
            # ======= 止损 ===========
            if   (self.data.low[0] < self.stop_loss_price): 
              
                # ==================== 统计 ====================
                AttackReversalStrategy.global_stats[date]["losses"] += 1
                size = int(ONE_TIME_SPENDING_ATTACK / self.buy_price)
                AttackReversalStrategy.global_stats[date]["Loss$"] -= size * (self.buy_price - self.stop_loss_price)
                AttackReversalStrategy.global_stats[date]["sell_symbols"].append(self.p.symbol)
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
        

        for date in sorted(cls.global_stats.keys()):
            wins = cls.global_stats[date]["wins"]
            losses = cls.global_stats[date]["losses"]
            buy_symbols = cls.global_stats[date]["buy_symbols"]
            sell_symbols = cls.global_stats[date]["sell_symbols"]

            rows.append({
                "date": date,
                "wins": wins,
                "losses": losses,
                "buy_symbols": ",".join(buy_symbols),
                "sell_symbols": ",".join(sell_symbols),
                "buys": cls.global_stats[date]["buys"],
                "net_earn$": round(cls.global_stats[date]["Win$"]+ cls.global_stats[date]["Loss$"],2),
                
    
            })

            total_wins += wins
            total_losses += losses
            total_buys += cls.global_stats[date]["buys"]
            total_win_money += cls.global_stats[date]["Win$"]
            total_loss_money += cls.global_stats[date]["Loss$"]

        # 写 CSV
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "wins", "losses", "buy_symbols", "sell_symbols", "buys", "net_earn$"])
            writer.writeheader()
            writer.writerows(rows)

        # 控制台 summary
        
        print("----- SUMMARY -----")
        net_profit = round(total_win_money + total_loss_money,2) 
        print(f"Total buys={total_buys} | Total Wins$ = {round(total_win_money,2)} | Total Loss $={round(total_loss_money,2)}  | Net P/L $={net_profit}")

        print(f"Total Wins={total_wins} | Total Losses={total_losses} | Overall WinRate={total_wins / (total_wins + total_losses) if (total_wins + total_losses) > 0 else 0.0:.2f}")

        return total_buys, net_profit
    