import pandas as pd

start = "2022-11-08"
end   = "2025-02-18"

# 生成日期序列（B = business day, 周一到周五）
bdays = pd.bdate_range(start=start, end=end)

print("交易日数量（不含周末，不考虑节假日）:", len(bdays))