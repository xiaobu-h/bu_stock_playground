import backtrader as bt

class AttackReversalStrategy(bt.Strategy):
    params = (
        ('boll_period', 20),
        ('boll_devfactor', 2),
        ('lookback', 5),        # 连续阴线数量
        ('volume_multiplier', 1.5),  # 放量倍数
        ('take_profit', 1.10),  # 止盈目标（10%）
        ('printlog', False),
        ('symbol', 'UNKNOWN'),
        ('trailing_stop_pct', 0.05),  # 跟踪止损百分比（5%）
    )

    def __init__(self):
        self.bb = bt.indicators.BollingerBands(
            self.data.close, period=self.p.boll_period, devfactor=self.p.boll_devfactor)
        self.vol_sma = bt.indicators.SMA(self.data.volume, period=self.p.lookback)

        self.buy_price = None

    def is_attack_setup(self):
        if not (
            self.data.close[-1] < self.data.close[-2] and
            self.data.close[-1] < self.data.close[-2] and
            self.data.close[-1] < self.data.close[-3] and
            self.data.close[-1] < self.data.close[-4] and
            self.data.close[-1] < self.data.close[-5]
        ):
            return False

        # 条件2：今日阳线
        if self.data.close[0] <= self.data.open[0]:
            return False

        # 条件4：放量 > N日均量的2倍
        if self.data.volume[0] <= self.vol_sma[0] * self.p.volume_multiplier:
            return False

        return True

    def next(self):
        if not self.position:
            if self.is_attack_setup():
                self.buy()
                self.buy_price = self.data.close[0]
                self.high_watermark = self.data.close[0]
        else:
            current_price = self.data.close[0]
            # 更新最高价
            if current_price > self.high_watermark:
                self.high_watermark = current_price
            # 止盈
            if current_price >= self.buy_price * self.p.take_profit:
                self.close()
                self.buy_price = None

            # 止损：跌破买入价
            elif current_price < self.buy_price * 0.98:
                self.close()
                self.buy_price = None

            # 跟踪止损：跌破最高点 N%
            elif current_price <= self.high_watermark * (1 - self.p.trailing_stop_pct):
                self.close()
                self.buy_price = None
                self.high_watermark = None

    def stop(self):
        if self.p.printlog:
            print(f'[STOP] [{self.p.symbol}]  Final Value: {self.broker.getvalue():.2f} day: {self.p.volume_multiplier} lookback: {self.p.lookback} take_profit: {self.p.take_profit}')