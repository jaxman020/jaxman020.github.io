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
    since = exchange.parse8601('2024-01-01T00:00:00Z')  # 从2023年1月1日开始获取数据
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', since=since)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df = df[df['timestamp'] < pd.Timestamp.now(tz='UTC').normalize()]  # 排除当天的数据
    return df

# 计算RS值的方法，使用7天窗口
def calculate_rs(df):
    df = df.copy()  # 避免SettingWithCopyWarning
    df['price_change'] = df['close'].diff()
    df['gain'] = np.where(df['price_change'] > 0, df['price_change'], 0)
    df['loss'] = np.where(df['price_change'] < 0, -df['price_change'], 0)
    if len(df) < v_window:  # 检查数据量是否足够
        return np.nan
    avg_gain = df['gain'].rolling(window=v_window).mean().iloc[-1]
    avg_loss = df['loss'].rolling(window=v_window).mean().iloc[-1]
    rs = avg_gain / avg_loss if avg_loss != 0 else 0
    return rs

# 计算五日内的RS值变化，使用7天窗口
def calculate_rs_change(df):
    rs_values = []
    for i in range(len(df) - (v_window - 1)):  # 确保窗口长度为7
        window_df = df.iloc[i:i+v_window].copy()  # 避免SettingWithCopyWarning
        rs = calculate_rs(window_df)
        if not np.isnan(rs):
            rs_values.append(rs)
    if len(rs_values) < 5:
        return np.nan, np.nan
    return rs_values[-1], rs_values[-5]  # 返回最新的RS值和五天前的RS值

# 获取所有U本位合约的RS值和五日变化
data = []
for symbol in usdt_contracts:
    df = get_historical_data(symbol)
    if len(df) < v_window:  # 跳过数据不足的币种
        continue
    rs = calculate_rs(df)
    if not np.isnan(rs):
        latest_rs, rs_5_days_ago = calculate_rs_change(df)
        if not np.isnan(latest_rs) and not np.isnan(rs_5_days_ago):
            rs_change = latest_rs - rs_5_days_ago
            data.append({
                'symbol': symbol,
                'rs': rs,
                'rs_change': rs_change,
                'latest_rs': latest_rs,
                'rs_5_days_ago': rs_5_days_ago
            })

# 创建DataFrame
df = pd.DataFrame(data)

# 按照RS值排序
sorted_df = df.sort_values(by='rs', ascending=False)

# 提取最强和最弱的各10个币种且RS不為零
sorted_df = sorted_df[sorted_df['rs'] != 0]
top_10 = sorted_df.head(10)
bottom_10 = sorted_df.tail(10)

# 计算五日续强标的和五日渐强标的
continuously_strong = df[df['rs_change'] > 0].sort_values(by='rs_change', ascending=False).head(10)
gradually_strong = df[df['rs_change'] < 0].sort_values(by='rs_change', ascending=True).head(10)

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
    write_df_to_excel(writer, sorted_df, 'All USDT Contracts')
    write_df_to_excel(writer, top_10, 'Top 10 Strongest')
    write_df_to_excel(writer, bottom_10, 'Top 10 Weakest')
    write_df_to_excel(writer, continuously_strong, 'Continuously Strong')
    write_df_to_excel(writer, gradually_strong, 'Gradually Strong')

print("数据已成功导出到 'crypto_strength_weakness_rs.xlsx'")
