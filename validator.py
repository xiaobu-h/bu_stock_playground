import backtrader as bt
import pandas as pd
import datetime
import yfinance as yf

import logging
import os

from ib_fetcher import fetch_data_from_ibkr, ib_connect,ib_disconnect
from collections import defaultdict
 
from strategy.breakout_volume.simple_volume_strategy import SimpleVolumeStrategy
from strategy.bl.bl_jump_strategy import BollingerVolumeBreakoutStrategy   
from strategy.attack_day.attack_day_strategy import AttackReversalStrategy 
from strategy.strategy_util import PandasData
from strategy.bcs.bcs_strategy import BullCallOptionStrategy
from strategy.bcs.bcs_strategy_copy import BullCallOptionStrategy2
 
 
global_stats = defaultdict(lambda: {"buys": 0, "wins": 0, "losses": 0, "Win$": 0, "Loss$": 0, "buy_symbols": [],"sell_symbols_win": [], "sell_symbols_loss": [],"extra_counter":0})

   
 
# ==========================================
 
CONNECT_N_DOWNLOAD = True 


def main():
    
    symbol = ["REGN"]
 
    
# ========================================== 
    start=""
    end  =   datetime.datetime.now().strftime("%Y-%m-%d")


    ib = ib_connect() if CONNECT_N_DOWNLOAD else None
    data_srouce = fetch_data_from_ibkr(symbols = symbol, ib = ib, end=end, interval="1d", duration_str="5 Y", start=start,  is_connect_n_download= CONNECT_N_DOWNLOAD)
    df = data_srouce[symbol[0]]
    cerebro = bt.Cerebro()
    data = PandasData(dataname=df)
    cerebro.adddata(data)
 
    cerebro.addstrategy(                  
            AttackReversalStrategy,
            printlog=True,
            symbol=symbol,
            global_stats = global_stats,
        )
    cerebro.run()
    
    cerebro = bt.Cerebro()
    data = PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.addstrategy(
            SimpleVolumeStrategy,
            printlog=True,                    
            symbol=symbol, 
            only_scan_last_day=False,
            global_stats = global_stats,
            is_backtest = True,
            is_hourly_backtest = False,
        )
    cerebro.run()
    
    cerebro = bt.Cerebro()
    data = PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.addstrategy(
            BollingerVolumeBreakoutStrategy,       
            printlog=True,
            symbol=symbol,
            only_scan_last_day = False,
            global_stats = global_stats,
            is_backtest = True,
        )
    cerebro.run() 
    
    cerebro = bt.Cerebro()
    data = PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.addstrategy(
            BullCallOptionStrategy,       
            printlog=True,
            symbol=symbol,
            only_scan_last_day = False,
            global_stats = global_stats,
            is_backtest = True,
        )
    cerebro.run() 
    
    cerebro = bt.Cerebro()
    data = PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.addstrategy(
            BullCallOptionStrategy2,       
            printlog=True,
            symbol=symbol,
            only_scan_last_day = False,
            global_stats = global_stats,
            is_backtest = True,
        )
    cerebro.run() 
    file_path = os.path.join("data_validator_results", f"{end}_{symbol}.log")
    if os.path.exists(file_path):
        os.remove(file_path)
    logging.basicConfig(
        filename=file_path,
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    print_global_stats(global_stats)
    get_next_earnings(symbol[0])
               
    if CONNECT_N_DOWNLOAD:
        ib_disconnect(ib)
     
       
def get_next_earnings(symbol):
    
    print("--------------------------------财报日-----------------------------------")
    logging.info("-------------------------------- EARNING -----------------------------------")
    tk = yf.Ticker(symbol)
    df = tk.get_earnings_dates(limit=6)  # limit 参数控制获取几条
    print( df)
    logging.info( df)
   

    
def print_global_stats(global_stats):

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
        
        extra_counter = global_stats[date]["extra_counter"]
        flat = [s for sub in buy_symbols for s in sub]
         
        rows.append({
            "date": date,
            "wins": wins,
            "losses": losses,
            "buy_symbols": ",".join(flat), 
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

    
    print("------------------------------ SUMMARY ---------------------------------")
    logging.info("------------------------------ SUMMARY ---------------------------------")
    net_profit = round(total_win_money + total_loss_money,2) 
    print(f"Total buys={total_buys} | Total Wins$ = {round(total_win_money,2)} | Total Loss $={round(total_loss_money,2)}  | Net P/L $={net_profit}")
    logging.info(f"Total buys={total_buys} | Total Wins$ = {round(total_win_money,2)} | Total Loss $={round(total_loss_money,2)}  | Net P/L $={net_profit}")
    print(f"Total Wins={total_wins} | Total Losses={total_losses} | Extra={total_extra_counter} | Overall WinRate={round(total_wins / (total_wins + total_losses) ,4)if (total_wins + total_losses) > 0 else 0.0:.4f}")
    logging.info(f"Total Wins={total_wins} | Total Losses={total_losses} | Extra={total_extra_counter} | Overall WinRate={round(total_wins / (total_wins + total_losses) ,4)if (total_wins + total_losses) > 0 else 0.0:.4f}")
 
 
 
if __name__ == "__main__":
    main()
