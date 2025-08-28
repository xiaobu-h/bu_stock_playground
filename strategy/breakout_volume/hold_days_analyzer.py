import backtrader as bt
from datetime import timedelta

class TradeDurationAnalyzer(bt.Analyzer):
    """
    收集每笔已平仓交易的持仓时长：
      - bars：bar 数（不受周末/停牌影响）
      - days：自然日（含周末/停牌）
    get_analysis() 返回 dict: {"bars": [..], "days": [..]}
    """
    def start(self):
        self._bars = []
        self._days = []

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        bars_held = trade.barclose - trade.baropen
        self._bars.append(int(bars_held))

        dt_open = bt.num2date(trade.dtopen)
        dt_close = bt.num2date(trade.dtclose)
        days_held = (dt_close - dt_open) / timedelta(days=1)
        self._days.append(days_held)

    def get_analysis(self):
        return {"bars": self._bars, "days": self._days}