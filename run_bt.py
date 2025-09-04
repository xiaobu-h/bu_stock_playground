
import backtrader as bt
import pandas as pd
from backtest_fetcher import fetch_yahoo_data
from strategy.attack_day.backtest_strategy import AttackReversalStrategy, ONE_TIME_SPENDING_ATTACK
from strategy.bl_jump_lower_open.strategy import BollingerVolumeBreakoutStrategy 
from strategy.breakout_volume.simple_volume_strategy import SimpleVolumeStrategy, ONE_TIME_SPENDING
from get_symbols import FINAL_SYMBOLS , NASDAQ100 , TEST_SYMBOLS ,COMMON_SYMBOLS
from collections import defaultdict
from strategy.breakout_volume.hold_days_analyzer import TradeDurationAnalyzer
 

import statistics
 

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
    
    start="2024-11-01"
    end="2025-08-30"   # 近10个月
    '''
     
      start="2025-01-01"
    end="2025-08-28"   # 近期 2025   8个月
    
    start="2022-10-11"
    end="2025-02-20"     # 牛市 2022 - 2025  
     start="2020-01-01"
    end="2025-06-01"   # 长期  # 65 个月
  
      start="2025-06-01"
    end="2025-08-27"  # 近期  近三个月
    
      
    start="2022-01-01"
    end="2022-12-30"   # 熊市 2022   #  12 个月   
    
    
    start="2025-02-24"
    end="2025-04-07"   # 熊市 2025关税
    
 
  
    start="2022-10-11"
    end="2025-02-20"     # 牛市 2022 - 2025
 
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
            AttackReversalStrategy,
            printlog=False,
            symbol=symbol
        ) 
   
        """   cerebro.addstrategy(
            SimpleVolumeStrategy,
            printlog=False,
            symbol=symbol, 
            only_scan_last_day=False
        )
        cerebro.addstrategy(
            BollingerVolumeBreakoutStrategy,
            printlog=False,
            symbol=symbol,
            only_scan_last_day = False,
        )
        
         cerebro.addstrategy(
            SimpleVolumeStrategy,
            printlog=False,
            symbol=symbol, 
            only_scan_last_day=False
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
    
    
    
    #total_buys, net_profit = SimpleVolumeStrategy.export_global_csv("monthly_winloss.csv")
    
    total_buys, net_profit = AttackReversalStrategy.export_global_csv("monthly_winloss.csv")
    
    #total_buys, net_profit = BollingerVolumeBreakoutStrategy.export_global_csv("monthly_winloss.csv")
 
    print("=====  Max money usage: ===== ")
    max_avg_money =  avg_bars * total_buys * ONE_TIME_SPENDING/ total_trading_days
    print( max_avg_money)
    
    print("=====  月转化率: ===== ")
    print(  net_profit / max_avg_money / 10 )    
       