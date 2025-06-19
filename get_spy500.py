import pandas as pd

# 从维基百科抓取标普500公司表格
url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
tables = pd.read_html(url)
sp500_df = tables[0]

# 获取符号列表，并处理 . 替换为 -
sp500_symbols = sp500_df["Symbol"].str.replace(".", "-", regex=False).tolist()

# 保存或打印前几个看看
print(sp500_symbols[:10])
