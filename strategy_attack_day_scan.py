import backtrader as bt

class AttackReversalSignalScan(bt.Strategy):
    params = (
        ('lookback', 5),
        ('volume_multiplier', 1.2),
        ('symbol', 'UNKNOWN'),
    )

    def __init__(self):
        self.vol_sma5 = bt.indicators.SMA(self.data.volume, period=self.p.lookback)
        self.signal_today = False

    def is_attack_setup(self):
        date = self.data.datetime.date(0)
        if not (
            self.data.close[-1] < self.data.close[-2] and
            self.data.close[-1] < self.data.open[-1] and
            self.data.close[-2] < self.data.close[-3] and
            self.data.close[-2] < self.data.close[-4] and
            self.data.close[-2] < self.data.close[-5] and
            (self.data.close[-5] - self.data.close[-1]) / self.data.close[-1] > 0.12
        ):
            print(self.data.close[-1] , self.data.close[-2], self.data.close[-3], self.data.close[-4], self.data.close[-5])
            print(f"[{date}] ❌ 不满足连续下跌")
            return False

        if self.data.close[0] <= self.data.open[0]:
            
            print(f"[{date}] ❌ 今日不是阳线")
            return False

        if self.data.volume[0] <= self.vol_sma5[0] * self.p.volume_multiplier:
            print(f"[{date}] ❌ 成交量不足")
            return False

        return True

    def next(self):
        if self.is_attack_setup():
            self.signal_today = True
