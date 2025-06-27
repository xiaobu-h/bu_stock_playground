
import backtrader as bt
import pandas as pd
from backtest_fetcher import fetch_yahoo_data
from strategy.bl_jump_lower_open.stratety import BollingerVolumeBreakoutStrategy
from strategy.bl_new_high_w_volumn.stratety import BollingerNewHighWithVolumeBreakoutStrategy
from get_symbols import FINAL_SYMBOLS , NASDAQ100 , TEST_SYMBOLS 
from collections import defaultdict

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
    df_dict = fetch_yahoo_data(symbols)
    from collections import Counter
    position_counter = Counter()
    
    for symbol, df in df_dict.items():
        df = df[["Open", "High", "Low", "Close", "Volume"]]

        cerebro = bt.Cerebro()
        data = PandasData(dataname=df)
        cerebro.adddata(data)
        cerebro.broker.set_coc(True) # set to True to enable close of the current bar to be used for the next bar's open price

        """ 
        cerebro.optstrategy(
            AttackReversalStrategy,
            boll_period=[20],
            boll_devfactor=[2],
            lookback_days=[5],
            volume_multiplier=[ 1.75],
            take_profit= [1.15],
            printlog=[True],
            symbol=symbol
        )
        
        cerebro.addstrategy(
            BollingerVolumeBreakoutStrategy,
            lookback_days=8,
            volume_multiplier=1.25,
            take_profit=1.13,
            printlog=False,
            symbol=symbol,
            only_scan_last_day = False,
        )
        """
        cerebro.addstrategy(
            BollingerNewHighWithVolumeBreakoutStrategy,
            lookback_days=3,
            volume_multiplier=1.6,
            volume_max=3,
            min_increse_percent=0.035,
            take_profit=1.05,
            printlog=False,
            symbol=symbol,
            only_scan_last_day = False,
        )
        
        
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        #cerebro.addanalyzer(TrackPositions, _name='pos_tracker')
        cerebro.broker.set_cash(50000)
        
        results = cerebro.run()
        
        analysis = results[0].analyzers.trades.get_analysis()
        summary['total_trades'] += analysis.get('total', {}).get('total', 0)
        summary['wins'] += analysis.get('won', {}).get('total', 0)
        summary['losses'] += analysis.get('lost', {}).get('total', 0)
        summary['pnl_net'] += analysis.get('pnl', {}).get('net', {}).get('total', 0.0)
        summary['pnl_won'] += analysis.get('won', {}).get('pnl', {}).get('total', 0.0)
        summary['pnl_lost'] += analysis.get('lost', {}).get('pnl', {}).get('total', 0.0)
       
       # daily_positions = results[0].analyzers.pos_tracker.get_analysis()
        #for date, count in daily_positions.items():
        #    position_counter[date] += count
       
       
    print_daily_positions(position_counter)
        #cerebro.plot()


def print_daily_positions( position_counter):
    print("\nDaily Open Positions:")
    for date, count in sorted(position_counter.items()):
        print(f"{date} - {count}")

def print_summary():
    total = summary['total_trades']
    wins = summary['wins']
    losses = summary['losses']
    pnl_net = summary['pnl_net']
    pnl_won = summary['pnl_won']
    pnl_lost = summary['pnl_lost']
    win_rate = (wins / total * 100) if total else 0

    print(
        f"[SUMMARY] Backtest Results:\n"
        f"  Total Trades: {total} | Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.2f}%\n"
        f"  Total Win PnL: {pnl_won:.2f} | Total Loss PnL: {pnl_lost:.2f} | Net PnL: {pnl_net:.2f}"
    )

class TrackPositions(bt.Analyzer):
    def __init__(self):
        self.daily_positions = defaultdict(int)

    def next(self):
        date = self.strategy.data.datetime.date(0)
        position = self.strategy.getposition().size
        if position > 0:
            self.daily_positions[date] += 1

    def get_analysis(self):
        return self.daily_positions

# manually run the backtest

if __name__ == "__main__":
    #run(NASDAQ100)
    #run(["AAPL", "MSFT", "NVDA", "GOOG", "TSLA", "AMD"  ])  #9:6
    #run(["IBM" , "ORCL", "V" , "META", "AMZN", "MSTR"])  #5:11    3:3
    
    #run(["SPY", "NFLX", "PYPL", "PLTR", "COIN", "HOOD"  ])  #12:5    8:1
    
    run(["KO", "OXY", "TSM", "COST", "XLK", "ADBE" , "CRM", "INTU", "AVGO", "QCOM", "TXN", "LRCX", "AMAT", "MU", "ASML",  "PYPL" ])  
    #run(NASDAQ100) 
    print_summary()