import backtrader as bt
from datetime import datetime
import logging


class BreakoutVolumeLogic:
    def __init__(self, data, lookback_days=10, volume_multiplier=1.5, min_total_increse_percent=0.03):
        self.data = data
        self.min_total_increse_percent = min_total_increse_percent
        self.lookback_days = lookback_days
        self.volume_multiplier = volume_multiplier  
        self.vol_sma = bt.indicators.SimpleMovingAverage(self.data.volume, period=self.lookback_days)
        
    def check_buy_signal(self): 
        if len(self.data) < self.lookback_days:
            return False
        open_ = self.data.open[0]
        close = self.data.close[0] 
        volume = self.data.volume[0]
        avg_volume = self.vol_sma[0]
 
        if (close < open_ ):
            #print(f"[{self.data.datetime.date(0)}]Not two bullish candles.")
            return False
        
        if abs(close - open_) <  open_ *  self.min_total_increse_percent:  
            #print(f"[{self.data.datetime.date(0)}]Candle increase is too small.")
            return False
        
        if (volume < self.data.volume[-1]) | (volume < avg_volume * self.volume_multiplier):
           # print(f"[{self.data.datetime.date(0)}]Volume is not a spike.")
            return False
       
        return True
    
class BreakoutVolumeStrategy(bt.Strategy):
    params = (
        ('lookback_days', 10),
        ('volume_multiplier', 2), 
        ('min_total_increse_percent', 0.03),
        ('only_scan_last_day', True),
        ('take_profit', 1.10),
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
    )

    def __init__(self):
        self.signal_today = False
        self.order = None
        self.entry_price = None
        self.increses= None
        self.buy_logic = BreakoutVolumeLogic(
            self.data,
            lookback_days=self.p.lookback_days,
            min_total_increse_percent=self.p.min_total_increse_percent,
            volume_multiplier=self.p.volume_multiplier
        )

    def next(self):
        if self.p.only_scan_last_day:
            if len(self) < 2 or self.data.datetime.date(0) != datetime.today().date():
               return
           
           
        if  self.position: 
            low = self.data.low[0]
            
            if  self.data.high[0]  - self.entry_price> self.increses :
                self.close()
                return
            
         
            if low < self.stop_price: 
                #print(f"[{self.data.datetime.date(0)}] ❌ Stop loss hit: Low {low:.2f} < Stop {self.stop_price:.2f}")
                self.close()
 
        if self.buy_logic.check_buy_signal():
            logging.info(f"[{self.data.datetime.date(0)}] Breakout Volume - {self.p.symbol}!")
            if self.p.only_scan_last_day:
                self.signal_today = True
            else: 
                size = int(5000 / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
                    self.increses = self.data.close[0] - self.data.open[0]
                    
                    #print(f"[{self.data.datetime.date(0)}]")
                    self.entry_price = self.data.close[0]
                    self.stop_price =min ( min(self.data.low[0] , self.data.low[-1] ), self.data.low[-2] )
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