import backtrader as bt
import logging 

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
            return False

        if self.data.close[0] <= self.data.open[0]:
            logging.info(f"[{date}] [1] Today is not a bullish day.")
            return False

        if self.data.volume[0] <= self.vol_sma5[0] * self.p.volume_multiplier:
            logging.info(f"[{date}] [2] Volume is not sufficiently high.")
            return False

        return True

    def next(self):
        if self.is_attack_setup():
            self.signal_today = True
