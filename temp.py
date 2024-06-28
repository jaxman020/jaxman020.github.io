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
usdt_contracts = [
    symbol
    for symbol in markets
    if symbol.endswith("USDT") and "swap" in markets[symbol]["type"]
]


# 获取历史数据的方法（仅获取过去11天的）
def get_historical_data(symbol):
    since = exchange.parse8601(
        (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=11)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    )
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1d", since=since)
    df = pd.DataFrame(
        ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(
        df["timestamp"], unit="ms", utc=True
    ).dt.tz_convert(None)
    df = df[df["timestamp"] < pd.Timestamp.now().normalize()]  # 排除当天的数据
    return df


# 获取所有U本位合约的每日涨跌幅
data = []
for symbol in usdt_contracts:
    df = get_historical_data(symbol)
    if len(df) < 2:  # 跳过数据不足的币种
        continue
    df["price_change"] = df["close"].pct_change()  # 计算每日涨跌幅
    df.dropna(inplace=True)
    for _, row in df.iterrows():
        data.append(
            {
                "symbol": symbol,
                "timestamp": row["timestamp"],
                "price_change": row["price_change"],
            }
        )

# 创建DataFrame
df = pd.DataFrame(data)

# 按时间戳分组并计算每个合约的RS值
df["rank"] = (
    df.groupby("timestamp")["price_change"].rank(ascending=False, pct=True) * 100
)
df["rank"] = 100 - df["rank"]


# 計算加權平均的函數
def calculate_weighted_average(data, weights):
    # 確保權重的數量與數據點的數量相匹配
    weights = weights[-len(data):]
    return np.average(data, weights=weights)

# 计算加权RS值
def calculate_weighted_rs(df):
    weights = np.array([5, 4, 3, 2, 1])
    df["weighted_rs"] = df.sort_values(by="timestamp").groupby("symbol")["rank"].apply(
        lambda x: np.average(x[-5:], weights=weights[-len(x[-5:]) :])
    )
    return df

# 为df添加加权RS值
df = calculate_weighted_rs(df)

# 提取最新一个交易日的加权RS值
latest_df = df[df["timestamp"] == df["timestamp"].max()]

# 按加权RS值排序
latest_df = latest_df.sort_values(by="rank", ascending=False)

# 提取最强和次强标的
top_10 = latest_df.head(10)
next_10 = latest_df.iloc[10:20]
next_10 = next_10[next_10["rank"] >= 80]
weak_10 = latest_df.tail(10)

# 计算五日续强标的和五日转强标的
def calculate_rs_trends(df):
    continuously_strong = []
    gradually_strong = []
    for symbol in usdt_contracts:
        symbol_df = df[df["symbol"] == symbol].sort_values(by="timestamp")
        if len(symbol_df) < 6:
            continue
        weighted_rs = np.average(symbol_df["rank"][-5:], weights=[5, 4, 3, 2, 1])
        if all(symbol_df["rank"][-5:] > 80):
            continuously_strong.append({"symbol": symbol, "weighted_rs": weighted_rs})
        if all(symbol_df["rank"][-5:].diff().dropna() > 0) and all(
            symbol_df["rank"][-2:] > 80
        ):
            gradually_strong.append({"symbol": symbol, "weighted_rs": weighted_rs})
    return pd.DataFrame(continuously_strong), pd.DataFrame(gradually_strong)

# 计算持续强势和逐渐转强的标的
continuously_strong, gradually_strong = calculate_rs_trends(df)

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
        adjusted_width = max_length + 2
        worksheet.column_dimensions[column].width = adjusted_width

with pd.ExcelWriter("crypto_strength_weakness_rs.xlsx", engine="openpyxl") as writer:
    write_df_to_excel(writer, latest_df, "All USDT Contracts")
    write_df_to_excel(writer, top_10, "Top 10 Strongest")
    write_df_to_excel(writer, next_10, "Next 10 Strongest")
    write_df_to_excel(writer, weak_10, "Top 10 Weakest")
    if not continuously_strong.empty:
        write_df_to_excel(writer, continuously_strong.sort_values(by="weighted_rs", ascending=False).head(10), "Continuously Strong")
    if not gradually_strong.empty:
        write_df_to_excel(writer, gradually_strong.sort_values(by="weighted_rs", ascending=False).head(10), "Gradually Strong")

print("数据已成功导出到 'crypto_strength_weakness_rs.xlsx'")
