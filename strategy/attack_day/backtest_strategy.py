import backtrader as bt

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
        self.buy_price = None

    def is_attack_setup(self):
        
        if not (
            self.data.close[-1] < self.data.close[-2] and
            self.data.close[-1] < self.data.open[-1] and
            self.data.close[-1] < self.data.close[-3] and
            self.data.close[-1] < self.data.close[-4] and
            self.data.close[-1] < self.data.close[-5] 
        ):
            return False


        # 条件1：过去 5 / 6 天 已经下跌超过10%
        if  ( 
                (self.data.close[-5] - self.data.low[-1]) / self.data.low[-1] < self.p.down_pct and
                (self.data.close[-6] - self.data.low[-1]) / self.data.low[-1] < self.p.down_pct 
     ):
            #print(f"[{date}] [0] not down 10% ")
            return False
         
         
        # 条件2：今日阳线
        if self.data.close[0] <= self.data.open[0]:
            return False

        # 条件4：放量 > N日均量的2倍
        if self.data.volume[0] <= self.vol_sma5[0] * self.p.volume_multiplier:
            return False

        return True

    def next(self):
        if not self.position:
            if self.is_attack_setup():
                self.buy(exectype=bt.Order.Close)
                self.buy_price = self.data.close[0]
                self.high_watermark = self.data.close[0]
                self.stop_loss_price = self.data.low[0]
        else:
            current_price = self.data.close[0]
            # 更新最高价
            if current_price > self.high_watermark:
                self.high_watermark = current_price
                
  
            # 止盈
            if current_price >= self.buy_price * self.p.take_profit or self.kdj.percD[0] > 90:
                print(f"[TAKE PROFIT] {self.p.symbol} at {current_price}, bought at {self.buy_price}")
                self.close()
                self.buy_price = None
            
            # 止损：跌破买入日最低价
            elif current_price < self.stop_loss_price:
                print(f"[STOP LOSS] {self.p.symbol} at {current_price}, bought at {self.buy_price}")
                self.close()
                self.buy_price = None
                self.stop_loss_price = None
                
                
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