import backtrader as bt
from datetime import datetime
import pandas as pd
import logging

class SimpleVolumeLogic:
    def __init__(self, data,   volume_multiplier=1.5, min_total_increse_percent=0.01):
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
        
        if (volume < self.vol_sma3[0] * self.volume_multiplier) & (volume < self.vol_sma5[0] * self.volume_multiplier) & (volume < self.vol_sma10[0] * self.volume_multiplier):
           # print(f"[{self.data.datetime.date(0)}]Volume is not a spike.")
            return False

        if abs(close - open_) <  open_ *  self.min_total_increse_percent:  
            #print(f"[{self.data.datetime.date(0)}]Candle increase is too small.")
            return False
        
        #if (self.data.close[-1]  > close) & ((self.data.close[-1] - close) > self.data.close[-1] * 0.8):
            #print(f"[{self.data.datetime.date(0)}]Jump down too much.")
            #return False
        
        return True
    
class SimpleVolumeStrategy(bt.Strategy):
    params = (
        ('volume_multiplier', 1.5), 
        ('min_total_increse_percent', 0.012),
        ('only_scan_last_day', True),
        ('take_profit', 1.05),
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
    )
        
    @staticmethod 
    def get_profit_rate_by_hv(symbol, csv_path="hv_30d_results.csv"):
        df = pd.read_csv(csv_path)
        
        row = df[df["Symbol"].str.upper() == symbol.upper()]
        if not row.empty:
            if row.iloc[0]["HV_30d"] > 0.5:
                return 1.2
            elif row.iloc[0]["HV_30d"] > 0.3:      
                return 1.09
        return 1.05
    
    
    
    def __init__(self):
        self.signal_today = False
        self.order = None
        self.entry_price = None
        self.increses= None
        self.buy_logic = SimpleVolumeLogic(
            self.data, 
            min_total_increse_percent=self.p.min_total_increse_percent,
            volume_multiplier=self.p.volume_multiplier
        )
        rate = 1.04 # = self.get_profit_rate_by_hv(self.p.symbol)
        if rate is None:
            self.profit_rate = self.p.take_profit
        else:
            self.profit_rate = rate

    def next(self):
        if self.p.only_scan_last_day:
            if len(self) < 2 or self.data.datetime.date(0) != datetime.today().date():
               return
           
           
        if  self.position: 
            low = self.data.low[0]
            
            if  (self.data.high[0]  - self.entry_price) > self.increses  :
                self.close()
                return
            
            if  self.data.high[0]  > self.entry_price * self.profit_rate:
                #print(f"[{self.data.datetime.date(0)}] ✅ Take profit hit: High {self.data.high[0]:.2f} > Entry {self.entry_price:.2f}")
                self.close()
                return
            if low < self.stop_price * 0.97: 
                #print(f"[{self.data.datetime.date(0)}] ❌ Stop loss hit: Low {low:.2f} < Stop {self.stop_price:.2f}")
                self.close()
 
        if self.buy_logic.check_buy_signal():
            logger = logging.getLogger(__name__)
            logger.info(f"[{self.data.datetime.date(0)}] VOL x 2 - {self.p.symbol}")
            
            if self.p.only_scan_last_day:
                self.signal_today = True
            else: 
                size = int(5000 / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
                    self.increses = self.data.close[0] - self.data.open[0]
                    
                    #print(f"[BUY] [{self.p.symbol}] - {self.data.datetime.date(0)}]")
                    self.entry_price = self.data.close[0]
                    self.stop_price = min(self.data.low[0] , self.data.low[-1] ) 
                    self.signal_today = True
    def stop(self):
        if self.p.printlog:
            try:
                analysis = self.analyzers.trades.get_analysis()
                total = analysis.get('total', {}).get('total', 0)
                won = analysis.get('won', {}).get('total', 0)
                lost = analysis.get('lost', {}).get('total', 0)
                pnl_net = analysis.get('pnl', {}).get('net', {}).get('total', 0.0)
                win_rate = (won / total * 100) if total else 0
            except Exception as e:
                print(f"[ERROR] Analyzer error for {self.p.symbol}: {e}")
                total = won = lost = 0
                pnl_net = win_rate = 0

            print(
                f"[STOP] [{self.p.symbol}] Final Value: {self.broker.getvalue():.2f} "
                f"Trades: {total} | Wins: {won} | Losses: {lost} | Win Rate: {win_rate:.2f}% | Net PnL: {pnl_net:.2f}"
            )