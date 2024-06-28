import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 初始化Binance交易所
exchange = ccxt.binance()

# 获取所有U本位合约
markets = exchange.load_markets()
usdt_contracts = [
    symbol
    for symbol in markets
    if symbol.endswith("USDT") and "swap" in markets[symbol]["type"]
]

# 获取历史数据的方法（仅获取过去15天的）
def get_historical_data(symbol):
    since = exchange.parse8601(
        (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=15)).strftime(
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

# 转换为DataFrame
df_data = pd.DataFrame(data)

# 计算RS值
def calculate_rs(df):
    # 按时间戳分组并计算每个合约的RS值
    rs_values = df.groupby("timestamp")["price_change"].rank(ascending=False, pct=True) * 100
    rs_values = 100 - rs_values
    return rs_values

# 计算加权RS值
def calculate_weighted_rs(rs_values):
    weighted_rs = []  # 初始值为NaN
    times = 0;
    for i in range(5, len(rs_values)):
        weighted_rs.append(np.dot(rs_values[i - 5 : i], [5, 4, 3, 2, 1]) / 15)
        times += 1
        if times == 5:
            break
        
    return weighted_rs

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

# 主程式
def main():
    weighted_rs_data = []
    pd.options.mode.copy_on_write = True
    for symbol in usdt_contracts:
        df = df_data[df_data["symbol"] == symbol]
        if len(df) < 6:  # 確保有足夠的數據來計算加權RS值
            continue
        df["rs"] = calculate_rs(df)
        df["weighted_rs"] = calculate_weighted_rs(df["rs"].values)
        
        weighted_rs_data.append(df)

    # 合併所有合約的加權RS值數據
    if weighted_rs_data:
        final_df = pd.concat(weighted_rs_data)
        # print(final_df)
        with pd.ExcelWriter(
            "crypto_strength_weakness_rs.xlsx", engine="openpyxl"
        ) as writer:
            write_df_to_excel(writer, final_df, "All USDT Contracts")
    else:
        print("No data available")

if __name__ == "__main__":
    main()
