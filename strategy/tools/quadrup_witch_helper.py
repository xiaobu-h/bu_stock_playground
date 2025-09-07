import pandas as pd

def is_quadruple_witching(date) -> bool:
    """仅按规则：3/6/9/12 月的第3个周五（不考虑休市调整）"""
    d = pd.Timestamp(date).tz_localize(None).normalize()
    if d.month not in (3, 6, 9, 12):
        return False
    # 这一年的所有“第3个周五”
    third_fris = pd.date_range(start=f'{d.year}-01-01',
                               end=f'{d.year}-12-31',
                               freq='WOM-3FRI').normalize()
    return d in third_fris