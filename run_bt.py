
import backtrader as bt
import pandas as pd
from backtest_fetcher import fetch_yahoo_data
from strategy.attack_day.backtest_strategy import AttackReversalStrategy, ONE_TIME_SPENDING_ATTACK
from strategy.bl_jump_lower_open.strategy import BollingerVolumeBreakoutStrategy 
from strategy.breakout_volume.simple_volume_strategy import SimpleVolumeStrategy, ONE_TIME_SPENDING
from get_symbols import FINAL_SYMBOLS , NASDAQ100 , TEST_SYMBOLS ,COMMON_SYMBOLS
from collections import defaultdict
from strategy.breakout_volume.hold_days_analyzer import TradeDurationAnalyzer
import csv
 

import statistics

global_stats = defaultdict(lambda: {"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0, "buy_symbols": [], "sell_symbols": []})
 
SAVE_AS_CSV = True 
    
def export_global_csv(global_stats, filepath: str):

    rows = []
    total_wins = 0
    total_losses = 0
    total_buys = 0
    total_win_money = 0
    total_loss_money = 0
    

    for date in sorted(global_stats.keys()):
        wins = global_stats[date]["wins"]
        losses = global_stats[date]["losses"]
        buy_symbols = global_stats[date]["buy_symbols"]
        sell_symbols = global_stats[date]["sell_symbols"]

        rows.append({
            "date": date,
            "wins": wins,
            "losses": losses,
            "buy_symbols": ",".join(buy_symbols),
            "sell_symbols": ",".join(sell_symbols),
            "buys": global_stats[date]["buys"],
            "net_earn$": round(global_stats[date]["Win$"]+ global_stats[date]["Loss$"],2),
            

        })

        total_wins += wins
        total_losses += losses
        total_buys += global_stats[date]["buys"]
        total_win_money += global_stats[date]["Win$"]
        total_loss_money += global_stats[date]["Loss$"]

    if SAVE_AS_CSV:
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
    

class PandasData(bt.feeds.PandasData):
    params = (
        ("datetime", None),
        ("open", "Open"),
        ("high", "High"),
        ("low", "Low"),
        ("close", "Close"),
        ("volume", "Volume"),
        ("openinterest", -1),
    )


summary = {
    'total_trades': 0,
    'wins': 0,
    'losses': 0,
    'pnl_net': 0.0,
    'pnl_won': 0.0,
    'pnl_lost': 0.0
}


def run(symbols=["AAPL", "MSFT", "NVDA"]):
    start="2020-01-01"
    end="2025-06-01"   # 长期  # 65 个月
     
    '''  
  
      start="2025-01-01"
    end="2025-08-28"   # 近期 2025   8个月
    
   start="2022-10-11"
    end="2025-02-20"     # 牛市 2022 - 2025
  
   
    start="2024-11-01"
    end="2025-08-30"   # 近10个月
      
     
      start="2025-06-01"
    end="2025-08-27"  # 近期  近三个月
    
      
    start="2022-01-01"
    end="2022-12-30"   # 熊市 2022   #  12 个月   
    
    
    start="2025-02-24"
    end="2025-04-07"   # 熊市 2025关税

 
    '''
    df_dict = fetch_yahoo_data(symbols, start=start, end=end)  # 近期 2025 
    total_trading_days =  len( pd.bdate_range(start=start, end=end)) 
    
    all_bars = []
    all_days = []
    for symbol, df in df_dict.items():
        df = df[["Open", "High", "Low", "Close", "Volume"]]

        cerebro = bt.Cerebro()
        data = PandasData(dataname=df)
        cerebro.adddata(data)
        cerebro.broker.set_coc(True) # set to True to enable close of the current bar to be used for the next bar's open price
        cerebro.addstrategy(
            SimpleVolumeStrategy,
            printlog=False,
            symbol=symbol, 
            only_scan_last_day=False,
            global_stats = global_stats,
        ) 
        """   
          cerebro.addstrategy(
            BollingerVolumeBreakoutStrategy,
            printlog=False,
            symbol=symbol,
            only_scan_last_day = False,
            global_stats = global_stats,
        )
       
           cerebro.addstrategy(
            AttackReversalStrategy,
            printlog=False,
            symbol=symbol,
            global_stats = global_stats,
        )
         
        """
        cerebro.addanalyzer(TradeDurationAnalyzer, _name='td')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades") 
        
        cerebro.broker.set_cash(10000)
        
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
        print("没有任何已平仓交易，无法计算平均持仓。")
    
    return avg_bars,total_trading_days


# manually run the backtest

if __name__ == "__main__":
    #run(TEST_SYMBOLS)
    #run(["AAPL", "MSFT", "NVDA", "GOOG", "TSLA", "AMD"  ])  #9:6
    avg_bars,total_trading_days = run(FINAL_SYMBOLS) 
    

    total_buys, net_profit = export_global_csv(global_stats, "monthly_winloss.csv")
 
    print("=====  Max money usage: ===== ")
    max_avg_money =  avg_bars * total_buys * ONE_TIME_SPENDING/ total_trading_days
    print( max_avg_money)
    
    print("=====  月转化率: ===== ")
    print(  net_profit / max_avg_money / int(total_trading_days / 21) )    
    
    
    
