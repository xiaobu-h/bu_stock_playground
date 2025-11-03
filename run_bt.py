
import backtrader as bt
import pandas as pd
from ib_fetcher import fetch_data_from_ibkr, ib_connect, ib_disconnect 
from strategy.attack_day.attack_day_strategy import AttackReversalStrategy, ONE_TIME_SPENDING_ATTACK
from strategy.bl.bl_jump_strategy import BollingerVolumeBreakoutStrategy 
from strategy.breakout_volume.simple_volume_strategy import SimpleVolumeStrategy, ONE_TIME_SPENDING
from strategy.bcs.bcs_strategy_copy import BullCallOptionStrategy2
from strategy.bcs.bcs_strategy import BullCallOptionStrategy
from get_symbols import BACKTEST_SYMBOLS, NASDAQ100
from collections import defaultdict
from strategy.breakout_volume.hold_days_analyzer import TradeDurationAnalyzer
import csv

from strategy.strategy_util import PandasData
import statistics


global_stats = defaultdict(lambda: {"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0, "buy_symbols": [],  "sell_symbols_win": [], "sell_symbols_loss": [],"extra_counter":0})
 
SAVE_AS_CSV = True 
    
def export_global_csv(global_stats, filepath: str):

    rows = []
    total_wins = 0
    total_losses = 0
    total_buys = 0
    total_win_money = 0
    total_loss_money = 0
    total_extra_counter = 0
    

    for date in sorted(global_stats.keys()):
        wins = global_stats[date]["wins"]
        losses = global_stats[date]["losses"]
        buy_symbols = global_stats[date]["buy_symbols"]
        sell_symbols_win = global_stats[date]["sell_symbols_win"]
        sell_symbols_loss = global_stats[date]["sell_symbols_loss"]
        
        extra_counter = global_stats[date]["extra_counter"]

        rows.append({
            "date": date,
            "wins": wins,
            "losses": losses,
            "buy_symbols": ",".join(buy_symbols),
            "sell_symbols_win": ",".join(sell_symbols_win),
            "sell_symbols_loss": ",".join(sell_symbols_loss),
            "buys": global_stats[date]["buys"],
            "net_earn$": round(global_stats[date]["Win$"]+ global_stats[date]["Loss$"],2),
            "extra_counter" : extra_counter,
        })

        total_wins += wins
        total_losses += losses
        total_buys += global_stats[date]["buys"]
        total_win_money += global_stats[date]["Win$"]
        total_loss_money += global_stats[date]["Loss$"]
        total_extra_counter += extra_counter 

    if SAVE_AS_CSV:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
           writer = csv.DictWriter(f, fieldnames=["date", "wins", "losses", "buy_symbols", "sell_symbols_win", "sell_symbols_loss", "buys", "net_earn$", "extra_counter"])
           writer.writeheader()
           writer.writerows(rows)

    # 控制台 summary
    
    print("----- SUMMARY -----")
    net_profit = round(total_win_money + total_loss_money,2) 
   # print(f"Total buys={total_buys} | Overall WinRate={round(total_wins / (total_wins + total_losses) ,4)if (total_wins + total_losses) > 0 else 0.0:.4f}")
    print(f"Total buys={total_buys} | Total Wins$ = {round(total_win_money,2)} | Total Loss $={round(total_loss_money,2)}  | Net P/L $={net_profit}")

    print(f"Total Wins={total_wins} | Total Losses={total_losses} | Extra={total_extra_counter} | Overall WinRate={round(total_wins / (total_wins + total_losses) ,4)if (total_wins + total_losses) > 0 else 0.0:.4f}")

    return total_buys, net_profit


def add_strategy_by_index(cerebro, symbol, index):
        if index == 0:
            cerebro.addstrategy(
                SimpleVolumeStrategy,
                printlog=False,                   
                only_scan_last_day=False,
                global_stats = global_stats,
                symbol=symbol,
                is_backtest = True,
                is_hourly_backtest = False,
            ) 
        elif index == 1:
            cerebro.addstrategy(                
                AttackReversalStrategy,
                printlog=False,
                symbol=symbol,
                global_stats = global_stats,
            )   
        elif index == 2:
            cerebro.addstrategy(
                BollingerVolumeBreakoutStrategy,       
                printlog=False,
                symbol=symbol,
                only_scan_last_day = False,
                global_stats = global_stats,
                is_backtest = True,
            )
        elif index == 3:
            cerebro.addstrategy(
                BullCallOptionStrategy,       
                printlog=False,
                symbol=symbol,
                only_scan_last_day = False,
                global_stats = global_stats,
                is_backtest = True,
            )     
        elif index == 4:
            cerebro.addstrategy(
                BullCallOptionStrategy2,       
                printlog=False,
                symbol=symbol,
                only_scan_last_day = False,
                global_stats = global_stats,
                is_backtest = True,
            )

def run(symbols=["AAPL", "MSFT", "NVDA"]):
    
    start="2024-10-01"
    end="2025-10-18"   # 去年一年
    #start="2023-09-01"
    #end="2024-08-28"   #  23 - 24 年
    #start="2022-09-01"
    #end="2023-08-28"   # 22 - 23 年
    #start="2021-09-01"
    #end="2022-08-28"   # 21 - 22 年
     
    
    #start="2022-09-10"
    #end="2025-09-19"   # 三年
    
    #start="2020-09-10"
    #end="2025-09-19"   # 五年
    
    #start="2016-09-10"
    #end="2021-09-19"   # 古早 五年 2016
    
    #start="2015-10-10"
    #end="2025-10-03"   #  十年
    
    #start="2023-10-10"
    #end="2025-10-01"   # 临时 两年
    is_connect_n_download = False
    ib = ib_connect() if is_connect_n_download else None
 
    data_srouce = fetch_data_from_ibkr(interval="1d", duration_str="1 Y", symbols = symbols, start=start, end=end ,useRTH = True, ib = ib, is_connect_n_download=is_connect_n_download, )
    if is_connect_n_download:
        ib_disconnect(ib)
   
    
    all_bars = []
    all_days = [] 
    total_trading_days =  len( pd.bdate_range(start=start, end=end)) 
    for symbol, df in data_srouce.items():
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        

        cerebro = bt.Cerebro()
        data = PandasData(dataname=df)
        cerebro.adddata(data)
        
        
         # == 从 小时线 数据重采样成日线 ===
        #data_min = PandasData(dataname=df , timeframe=bt.TimeFrame.Minutes, compression=60)
        #cerebro.resampledata(data_min,
                    #         timeframe=bt.TimeFrame.Days,
                     #       compression=1)        # datas[1]
        
        # index: 
        # [0 => VOL * 2], 
        # [1 => Attack Day ], 
        # [2 => BL Jump ], 
        # [3 => BCS Option]
        # [4 => BCS Option 2 ]
        add_strategy_by_index(cerebro, symbol, index= 4 )  
        cerebro.addanalyzer(TradeDurationAnalyzer, _name='td')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades") 
        
        
        results = cerebro.run()
        strat = results[0]                     # 拿到策略实例
        analysis = strat.analyzers.td.get_analysis()
         
        all_bars.extend(analysis["bars"])
        all_days.extend(analysis["days"]) 

        #cerebro.plot()
 
    if all_bars:
        avg_bars = statistics.mean(all_bars)
        avg_days = statistics.mean(all_days)
        print("===== 平均持仓时间统计 =====")
        print(f"跨全部 symbol 的平均持仓（bar）：{avg_bars:.2f}")
        print(f"跨全部 symbol 的平均持仓（天）： {avg_days:.2f}")
    else:
        avg_bars = -1
        print("没有任何已平仓交易，无法计算平均持仓。")
    
    return avg_days,total_trading_days
 

# manually run the backtest

if __name__ == "__main__":  
    avg_bars,total_trading_days = run( BACKTEST_SYMBOLS) 
    
     
    total_buys, net_profit = export_global_csv(global_stats, "monthly_winloss.csv")
 
    print("=====  Max money usage: ===== ")
    max_avg_money =  avg_bars * total_buys * ONE_TIME_SPENDING/ total_trading_days
    print( max_avg_money)
      
    if max_avg_money > 0 :
        print("=====  月转化率: ===== ")
        print(  net_profit / max_avg_money / int(total_trading_days / 21 ) )    
    
 
        
          
            