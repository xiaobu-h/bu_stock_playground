import backtrader as bt
from datetime import datetime
import pandas as pd
import logging
from collections import defaultdict
import csv 

ONE_TIME_SPENDING = 30000  # 每次买入金额

class SimpleVolumeLogic:
    def __init__(self, data, volume_multiplier, min_total_increse_percent):
        self.data = data
        self.min_total_increse_percent = min_total_increse_percent
 
        self.volume_multiplier = volume_multiplier  
        self.vol_sma3 = bt.indicators.SimpleMovingAverage(self.data.volume, period=3)
        self.vol_sma5 = bt.indicators.SimpleMovingAverage(self.data.volume, period=5)
        self.vol_sma10 = bt.indicators.SimpleMovingAverage(self.data.volume, period=10)
               
            
    def check_buy_signal(self): 
        open_ = self.data.open[0]
        close = self.data.close[0] 
        volume = self.data.volume[0]
        
        if close < open_:
            #print(f"[{self.data.datetime.date(0)}]Close is less than open.")
            return False
        
        if (volume < self.vol_sma3[0] * self.volume_multiplier) & (volume < self.vol_sma10[0] * self.volume_multiplier): #交易量大于1.8倍放量 (大于3天/10天均值）
           # print(f"[{self.data.datetime.date(0)}]Volume is not a spike.")
            return False

        if abs(close - open_) <  open_ *  self.min_total_increse_percent:     #涨幅 1.5%
            #print(f"[{self.data.datetime.date(0)}]Candle increase is too small.")
            return False
        
        if (self.data.low[-1]  > close) & ((self.data.low[-1] - close) > self.data.close[-1] * 0.04):   #没有跳空下跌4%以上
            #print(f"[{self.data.datetime.date(0)}]Jump down too much.")
            return False
        
        if  min(self.data.low[0] , self.data.low[-1] ) < close * 0.93:    #  昨天 or 今天的最低点 没有低于7%   《--神来之笔--》
            return False
        
        return True
    
class SimpleVolumeStrategy(bt.Strategy):
    
    global_stats = defaultdict(lambda: {"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0})

    
    params = (
        ('volume_multiplier', 2), 
        ('min_total_increse_percent', 0.013),  # 最小涨幅 
        ('only_scan_last_day', True),
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
    )
        
    
    def __init__(self):
        self.signal_today = False
        self.order = None
        self.entry_price = None
        self.stop_price = None
        self.entry_date = None
        self.day0_increses= None
        self.buy_logic = SimpleVolumeLogic(
            self.data, 
            min_total_increse_percent=self.p.min_total_increse_percent,
            volume_multiplier=self.p.volume_multiplier
        ) 
         
        self.daily_stats = defaultdict(lambda: {"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0})

    def next(self):
       
        dtd = self.data.datetime.date(0).strftime("%Y-%m-%d")
        
        if self.p.only_scan_last_day:
            if len(self) < 2 or self.data.datetime.date(0) != datetime.today().date():
               return
           
        
        if  self.position:  
            
            rate = 1.013 if (self.day0_increses /self.data.open[0]) < 0.05 else 1.025   # 默认1.5%； 当日上涨超6% 则止盈放宽至2.5%
            size = int(ONE_TIME_SPENDING / self.entry_price)
            
                
            # 止盈
            if  self.data.high[0]  > self.entry_price * rate:
                 
                # ==================== 统计 ====================
                self.daily_stats[dtd]["wins"] += 1
                SimpleVolumeStrategy.global_stats[dtd]["wins"] += 1  # 累加到全局
                self.daily_stats[dtd]["Win$"] += ONE_TIME_SPENDING * (rate - 1)
                SimpleVolumeStrategy.global_stats[dtd]["Win$"] += ONE_TIME_SPENDING * (rate - 1)
                # ==============================================
                self.close()
                return
            
            
            # 止损
            if self.data.low[0] < self.stop_price:  
                
              #  if( dtd == '2025-06-24'   ):
               #     print(f" Close LOSS {self.p.symbol} on {self.data.datetime.date(0)}")
               #    print(f" Entry price {self.entry_price}  Stop price {self.stop_price}  Current low {self.data.low[0]} ")
                #    print(size)
                # ==================== 统计 ====================
                self.daily_stats[dtd]["losses"] += 1
                SimpleVolumeStrategy.global_stats[dtd]["losses"] += 1
                
                self.daily_stats[dtd]["Loss$"] -= size * (self.entry_price - self.stop_price)
                SimpleVolumeStrategy.global_stats[dtd]["Loss$"] -= size * (self.entry_price - self.stop_price)
                # ==============================================
                self.close()
                return
            '''
            
            # 强制平仓：持仓超过5个交易日
            if len( pd.bdate_range(start=self.entry_date, end=self.data.datetime.date(0)) ) > 5:
                
                # ==================== 统计 ====================
                if self.data.close[0] > self.entry_price:
                    self.daily_stats[dtd]["wins"] += 1
                    SimpleVolumeStrategy.global_stats[dtd]["wins"] += 1   
                    self.daily_stats[dtd]["Win$"] +=   (self.data.close[0] - self.entry_price) * size
                    SimpleVolumeStrategy.global_stats[dtd]["Win$"] += (self.data.close[0] - self.entry_price) * size
                else:
                    self.daily_stats[dtd]["losses"] += 1
                    SimpleVolumeStrategy.global_stats[dtd]["losses"] += 1
                    size = int(ONE_TIME_SPENDING / self.entry_price)
                    self.daily_stats[dtd]["Loss$"] -= size * (self.entry_price - self.data.close[0])
                    SimpleVolumeStrategy.global_stats[dtd]["Loss$"] -= size * (self.entry_price - self.data.close[0])
                # ==============================================
                
                self.close()
                return
 '''
        if self.buy_logic.check_buy_signal():
            
            if self.data.datetime.date(0).strftime("%Y-%m-%d") in ["2024-12-20" ,"2020-02-28", "2020-05-29", "2020-06-19",  "2020-11-30","2020-12-18","2021-01-06","2022-01-04","2022-03-18", "2022-06-17" ,
                                                                   "2022-06-24" , "2022-11-30", "2023-01-31", "2023-05-31" , "2023-11-30",  "2024-03-15" , "2024-05-31" , "2024-09-20", "2025-03-21" , "2025-04-07", "2025-05-30"  ]:
               return
            logger = logging.getLogger(__name__)
            logger.info(f"[{self.data.datetime.date(0)}] VOL x 2 - {self.p.symbol}")
            self.signal_today = True
            if not self.p.only_scan_last_day:  # 回测扫描
                # ==================== 统计 ====================
                self.daily_stats[dtd]["buys"] += 1
                SimpleVolumeStrategy.global_stats[dtd]["buys"] += 1
                # ==============================================
                self.order = self.buy()
                self.day0_increses = self.data.close[0] - self.data.open[0]
                self.entry_price = self.data.close[0]
                self.stop_price =(self.data.close[0] + self.data.open[0]) * 0.5  #= min(self.data.low[0] , self.data.low[-1] )   # 止损点 
                self.entry_date = self.data.datetime.date(0)
                    
    @classmethod
    def export_global_csv(cls, filepath: str):
        """
        将 global_stats 导出为 CSV，列为：
        month, wins, losses, win_rate
        其中 win_rate = wins / (wins + losses)，若当月无交易则为 0.
        导出后在控制台打印 total wins / total losses 的汇总。
        """
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
        
        #print("===== 按月统计 =====")
        #for r in rows:
        #    print(f"{r['month']}: Total buy={r['buys']}    | Total close={r['wins']+r['losses']}  |   Wins={r['wins']}   |   Losses={r['losses']}   |   WinRate={r['win_rate']}")
        #
        
        print("----- SUMMARY -----")
        net_profit = round(total_win_money + total_loss_money,2) 
        print(f"Total buys={total_buys} | Total Wins$ = {round(total_win_money,2)} | Total Loss $={round(total_loss_money,2)}  | Net P/L $={net_profit}")

        print(f"Total Wins={total_wins} | Total Losses={total_losses} | Overall WinRate={total_wins / (total_wins + total_losses) if (total_wins + total_losses) > 0 else 0.0:.2f}")

        return total_buys, net_profit
    
    
    
    
    
    
    @classmethod
    def reset_global(cls):
        """如需多轮运行/多批次测试前清空全局统计，可调用此方法。"""
        cls.global_stats.clear()