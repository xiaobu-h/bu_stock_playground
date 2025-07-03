import backtrader as bt
import pandas as pd

class AttackReversalStrategy(bt.Strategy):
    params = (
        ('boll_period', 20),
        ('boll_devfactor', 2),
        ('lookback_days', 5),        # 连续阴线数量
        ('volume_multiplier', 1.5),  # 放量倍数
        ('take_profit', 1.10),  # 止盈目标（10%）
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
        ('trailing_stop_pct', 0.05),  # 跟踪止损百分比（5%）
        ('down_pct', 0.12),  # 下跌百分比（12%）
    )

    def __init__(self):
        self.bb = bt.indicators.BollingerBands(
            self.data.close, period=self.p.boll_period, devfactor=self.p.boll_devfactor)
        self.vol_sma5 = bt.indicators.SMA(self.data.volume, period=self.p.lookback_days)
        self.kdj = bt.ind.Stochastic(
            self.data, period=9, period_dfast=3, period_dslow=3
        )
        self.stop_loss_price = 0.0
        self.buy_price = 0.0
        self.net = 0.0
        self.size = 0
        self.has_position = False
        #self.profit_rate = self.p.take_profit
        rate = self.get_profit_rate_by_hv(self.p.symbol)
        if rate is None:
            self.profit_rate = self.p.take_profit
        else:
            self.profit_rate = rate
       
       
       # 修改这个也需要修改 daily_monitor.py 中的 get_profit_rate_by_hv 方法
    @staticmethod 
    def get_profit_rate_by_hv(symbol, csv_path="hv_30d_results.csv"):
        df = pd.read_csv(csv_path)
        
        row = df[df["Symbol"].str.upper() == symbol.upper()]
        if not row.empty:
            if row.iloc[0]["HV_30d"] > 0.7:
                return 1.20
            elif row.iloc[0]["HV_30d"] > 0.5:
                return 1.18
            elif row.iloc[0]["HV_30d"] > 0.3:      
                return 1.15
        
        return 1.1
        
    def is_attack_setup(self):
        date = self.data.datetime.date(0)
        if not (
            self.data.close[-1] < self.data.close[-2] and
            self.data.close[-1] < self.data.open[-1] and
            self.data.close[-1] < self.data.close[-3] and
            self.data.close[-1] < self.data.close[-4] and
            self.data.close[-1] < self.data.close[-5] 
        ): 
            return False

        if  ( (self.data.close[-5] - self.data.low[-1]) / self.data.low[-1] < 0.10 and (self.data.close[-6] - self.data.low[-1]) / self.data.low[-1] < 0.10 ):
            return False
         
        
        if self.data.close[0] <= self.data.open[0]: 
            return False

        if self.data.volume[0] <= self.vol_sma5[0] * self.p.volume_multiplier:
            return False

        return True
    
    

    def next(self):
        
        if not self.position:
            if self.is_attack_setup():
                self.has_position = True
                self.buy_price = self.data.close[0]
                size = int(5000 / self.buy_price)
                if size > 0:
                    self.order = self.buy(size=size)  
                    self.size += size
                
                self.stop_loss_price = self.data.low[0]* 0.95
                
                self.net -= (self.buy_price * self.size)
        if self.position:
            if   (self.data.high[0] >= self.buy_price * self.profit_rate) :
                
                    
                #print(f"[TAKE PROFIT] {self.data.close[0] * self.size}")
                
                self.net += (self.buy_price * self.profit_rate * self.size)
                #print("actural net: ", self.buy_price * self.p.take_profit * self.size)
                self.buy_price = 0
                self.size = 0
                self.has_position = False
                self.close()
                
                # 止损：跌破买入日最低价
            if   (self.data.low[0] < self.stop_loss_price):
                #print(f"[STOP LOSS] {self.data.close[0] * self.size}")
                
                self.net += (self.stop_loss_price * self.size)
                
                #print("actural net: ", self.stop_loss_price * self.size)
                self.buy_price = 0
                self.stop_loss_price = 0
                self.size = 0
                self.has_position = False
                self.close()
            
                
            # ❌【BAD】【BAD】【BAD】 根据backtest， 跌破买入价不如买入日最底下效果好
            
            # 止损：跌破买入价
            #elif current_price < self.buy_price * 0.98:
            #    self.close()
            #    self.buy_price = None
            
            # ❌【BAD】【BAD】【BAD】 根据backtest， 跟踪止损不好 

            # 跟踪止损: 当最高价已经上涨超过买入价的设定百分比后，若价格回落超过该百分比则止损
            #elif ( self.high_watermark >= self.buy_price * (1 + self.p.trailing_stop_pct) and current_price <= self.high_watermark * (1 - self.p.trailing_stop_pct)):
            #    self.close()
            #    self.buy_price = None
            #    self.high_watermark = None

    def stop(self):
        analysis = self.analyzers.trades.get_analysis()
        #print (self.net)
        #print (analysis.get('pnl', {}).get('net', {}).get('total', 0.0))
        if (self.has_position):
            self.net += (self.buy_price * self.size)
            
        #print(self.net - analysis.get('pnl', {}).get('net', {}).get('total', 0.0))
        #if (self.net - analysis.get('pnl', {}).get('net', {}).get('total', 0.0) < -1000): 
        #print(self.p.symbol)
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