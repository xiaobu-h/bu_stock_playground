import backtrader as bt
from datetime import datetime

from collections import defaultdict

class BollingerVolumeBreakoutLogic:
    def __init__(self, data, lookback_days=10, volume_multiplier=2):
        self.data = data
        self.lookback_days = lookback_days
        self.volume_multiplier = volume_multiplier
        self.boll = bt.indicators.BollingerBands(self.data.close, period=20, devfactor=2)
        self.vol_sma = bt.indicators.SimpleMovingAverage(self.data.volume, period=self.lookback_days)
        self.cash = 50000
        self.balance_by_date = defaultdict(float)
        self.size = 0
        
    def check_buy_signal(self): 
        if len(self.data) < self.lookback_days:
            return False
        open_ = self.data.open[0]
        close = self.data.close[0]
        low_band = self.boll.lines.bot[0]
        volume = self.data.volume[0]
        avg_volume = self.vol_sma[0]
        if open_ >= low_band:
            return False
        
        if close < open_:
            #print(f"[{self.data.datetime.date(0)}]Not a bullish candle.")
            return False
        
        
        if ((low_band - open_) / low_band) < 0.01:
            #print(f"[{self.data.datetime.date(0)}]Jump is too small.")
            return False
        
        if volume < avg_volume * self.volume_multiplier:
            #print(f"[{self.data.datetime.date(0)}]Volume is not a spike.")
            return False
       

        return True
    
class BollingerVolumeBreakoutStrategy(bt.Strategy):
    params = (
        ('lookback_days', 7),
        ('volume_multiplier', 2),
        ('only_scan_last_day', True),
        ('take_profit', 1.10),
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
    )

    def __init__(self):
        self.signal_today = False
        self.order = None
        self.entry_price = None
        self.buy_logic = BollingerVolumeBreakoutLogic(
            self.data,
            lookback_days=self.p.lookback_days,
            volume_multiplier=self.p.volume_multiplier
        )
        self.cash = 50000
        self.balance_by_date = defaultdict(float)
        self.size = 0

    def next(self):
        if self.p.only_scan_last_day:
            if len(self) < 2 or self.data.datetime.date(0) != datetime.today().date():
               return
           
           
        if  self.position:
            high = self.data.high[0]
            low = self.data.low[0]
            if high >= self.entry_price * (self.p.take_profit):
                sell= self.entry_price * (self.p.take_profit) * self.size
                self.log_balance( sell)
                self.close()
                self.log_balance(self.broker.getvalue() - self.cash)
                #print(f"[{self.data.datetime.date(0)}] ✅ Take profit hit: High {high:.2f} ≥ Target {(self.entry_price * 1.10):.2f}")
                
                return
            if low < self.stop_price:
                self.log_balance( self.stop_price * self.size)
                self.close()
                #print(f"[{self.data.datetime.date(0)}] ❌ Stop loss hit: Low {low:.2f} < Stop {self.stop_price:.2f}")
                return

        if self.buy_logic.check_buy_signal():
            
            if self.p.only_scan_last_day:
                self.signal_today = True
            else: 
                self.size = int(5000 / self.data.close[0])
                if self.size > 0:
                    cost = self.size * self.data.close[0]
                    self.order = self.buy(size=self.size)
                    self.log_balance(-cost)
                    self.entry_price = self.data.close[0]
                    self.stop_price = self.data.low[0]
                    self.signal_today = True
    def stop(self):
        #print("📈 每日 balance 变化：")
        
        
        if self.p.printlog:
            try:
                total = 0
                for date in sorted(self.balance_by_date):
                    change = self.balance_by_date[date]
                    total += change
                    #print(f"{date}: {change:+.2f}")
                print(f"💰 总收益变化: {total:+.2f}")
                
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
            

    def log_balance(self, amount):
        date = self.datas[0].datetime.date(0)
        self.balance_by_date[date] += amount