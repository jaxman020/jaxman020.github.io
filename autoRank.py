import ccxt
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Alignment

# 初始化Binance交易所
exchange = ccxt.binance()

# 获取所有U本位合约
markets = exchange.load_markets()
usdt_contracts = [symbol for symbol in markets if symbol.endswith('USDT') and 'swap' in markets[symbol]['type']]

# 定義計算RS值的窗口變數
v_window = 7

# 定义获取历史数据的方法
def get_historical_data(symbol):
    since = exchange.parse8601('2024-01-01T00:00:00Z')  # 从2024年1月1日开始获取数据
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', since=since)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df = df[df['timestamp'] < pd.Timestamp.now(tz='UTC').normalize()]  # 排除当天的数据
    return df

# 计算RS值的方法，使用7天窗口
def calculate_rs(df):
    df = df.copy()  # 避免SettingWithCopyWarning
    df['price_change'] = df['close'].pct_change(periods=v_window)  # 计算7天的价格变化百分比
    rs = df['price_change'].iloc[-1]  # 使用最新的价格变化作为RS值
    return rs

# 获取所有U本位合约的RS值
data = []
for symbol in usdt_contracts:
    df = get_historical_data(symbol)
    if len(df) < v_window:  # 跳过数据不足的币种
        continue
    rs = calculate_rs(df)
    if not np.isnan(rs):
        data.append({
            'symbol': symbol,
            'rs': rs
        })

# 创建DataFrame
df = pd.DataFrame(data)

# 按照RS值排序
df = df.sort_values(by='rs', ascending=False)

# 计算RS的排名（PR值）
df['rank'] = df['rs'].rank(pct=True) * 100

# 提取最强和最弱的各10个币种且RS不為零
df = df[df['rs'] != 0]
top_10 = df.head(10)
bottom_10 = df.tail(10)

# 计算五日续强标的和五日渐强标的
continuously_strong = df[df['rs'] > df['rs'].mean()].sort_values(by='rs', ascending=False).head(10)
gradually_strong = df[df['rs'] < df['rs'].mean()].sort_values(by='rs', ascending=True).head(10)

# 将DataFrame写入Excel
def write_df_to_excel(writer, df, sheet_name):
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    worksheet = writer.sheets[sheet_name]
    for col in worksheet.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 2)
        worksheet.column_dimensions[column].width = adjusted_width

with pd.ExcelWriter('crypto_strength_weakness_rs.xlsx', engine='openpyxl') as writer:
    write_df_to_excel(writer, df, 'All USDT Contracts')
    write_df_to_excel(writer, top_10, 'Top 10 Strongest')
    write_df_to_excel(writer, bottom_10, 'Top 10 Weakest')
    write_df_to_excel(writer, continuously_strong, 'Continuously Strong')
    write_df_to_excel(writer, gradually_strong, 'Gradually Strong')

print("数据已成功导出到 'crypto_strength_weakness_rs.xlsx'")
