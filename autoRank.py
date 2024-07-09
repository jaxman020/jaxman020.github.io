import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 代理URL
proxyUrl = "http://Y6R9pAtvxxzmGC@85.208.108.20:5601"

# 代理配置
proxy = {
    "http": proxyUrl,
    "https": proxyUrl,
}


# 获取币安合约资料
def fetch_binance_contracts():
    exchange = ccxt.binance(
        #{"proxies": proxy}
    )
    try:
        markets = exchange.load_markets()

        symbols = [
            symbol
            for symbol in markets
            if symbol.endswith("USDT") and "swap" in markets[symbol]["type"]
        ]
        return symbols
    except ccxt.ExchangeNotAvailable:
        print("Error: Binance API is not available from this location.")
        # 您可以選擇在這裡返回空列表或預設值
        return []  # 或者其他適合您邏輯的值


# 获取单日涨跌幅资料
def fetch_daily_changes(symbol, days=11):
    exchange = ccxt.binance()
    since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1d", since=since)
    df = pd.DataFrame(
        ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["change_pct"] = df["close"].pct_change() * 100
    return df.dropna().iloc[:-1]  # 排除今天的数据


# 计算所有标的的RS值
def calculate_rs(all_data):
    all_data["rs"] = all_data.groupby("date")["change_pct"].rank(
        ascending=True, method="min"
    )
    max_rank = all_data["rs"].max()
    all_data["rs"] = (all_data["rs"] - 1) / (max_rank - 1) * 100
    return all_data


# 计算加权RS值
def calculate_weighted_rs(rs_series):
    weights = np.array([5, 4, 3, 2, 1])
    weighted_rs = np.dot(rs_series[-5:], weights) / weights.sum()
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
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = max_length + 2
        worksheet.column_dimensions[column].width = adjusted_width


# 主函数
def main():
    symbols = fetch_binance_contracts()
    if symbols == []:
        return

    all_data = pd.DataFrame()

    for symbol in symbols:
        try:
            df = fetch_daily_changes(symbol)
            if len(df) < 5:
                continue

            df["symbol"] = symbol
            all_data = pd.concat([all_data, df], ignore_index=True)
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    all_data = calculate_rs(all_data)

    results = []
    for symbol in symbols:
        df = all_data[all_data["symbol"] == symbol]
        if len(df) < 5:
            continue

        weighted_rs_list = []
        for i in range(4, len(df)):
            weighted_rs = calculate_weighted_rs(df["rs"].iloc[i - 4 : i + 1])
            weighted_rs_list.append(weighted_rs)

        weighted_rs_list = [np.nan] * (
            len(df) - len(weighted_rs_list)
        ) + weighted_rs_list

        results.append(
            {
                "symbol": symbol,
                "weighted_rs": weighted_rs_list[-1],
                "rs_last_day": df["rs"].iloc[-1],
                "rs_last_5_days": list(df["rs"][-5:]),
                "weighted_rs_last_5_days": weighted_rs_list[-5:],
            }
        )

    df_results = pd.DataFrame(results)
    df_top_10 = df_results.sort_values(by="rs_last_day", ascending=False).head(10)
    df_next_10 = df_results.sort_values(by="rs_last_day", ascending=False).iloc[10:20]
    df_continuously_strong = df_results[
        df_results["weighted_rs_last_5_days"].apply(
            lambda x: all(r > 75 for r in x if not np.isnan(r))
        )
    ]
    df_gradually_strong = df_results[
        df_results["weighted_rs_last_5_days"].apply(
            lambda x: all(
                x[i] <= x[i + 1]
                for i in range(len(x) - 1)
                if not np.isnan(x[i]) and not np.isnan(x[i + 1])
            )
        )
    ]
    df_weakest = df_results.sort_values(by="rs_last_day", ascending=True).head(10)

    # 添加前五日的每日加权与未加权RS值
    def add_rs_values(df):
        df = df.copy()  # 确保对 DataFrame 的操作不会引发 SettingWithCopyWarning
        df.loc[:, "rs_day_1"] = df["rs_last_5_days"].apply(
            lambda x: x[0] if len(x) > 0 else np.nan
        )
        df.loc[:, "rs_day_2"] = df["rs_last_5_days"].apply(
            lambda x: x[1] if len(x) > 1 else np.nan
        )
        df.loc[:, "rs_day_3"] = df["rs_last_5_days"].apply(
            lambda x: x[2] if len(x) > 2 else np.nan
        )
        df.loc[:, "rs_day_4"] = df["rs_last_5_days"].apply(
            lambda x: x[3] if len(x) > 3 else np.nan
        )
        df.loc[:, "rs_day_5"] = df["rs_last_5_days"].apply(
            lambda x: x[4] if len(x) > 4 else np.nan
        )
        df.loc[:, "weighted_rs_day_1"] = df["weighted_rs_last_5_days"].apply(
            lambda x: x[0] if len(x) > 0 else np.nan
        )
        df.loc[:, "weighted_rs_day_2"] = df["weighted_rs_last_5_days"].apply(
            lambda x: x[1] if len(x) > 1 else np.nan
        )
        df.loc[:, "weighted_rs_day_3"] = df["weighted_rs_last_5_days"].apply(
            lambda x: x[2] if len(x) > 2 else np.nan
        )
        df.loc[:, "weighted_rs_day_4"] = df["weighted_rs_last_5_days"].apply(
            lambda x: x[3] if len(x) > 3 else np.nan
        )
        df.loc[:, "weighted_rs_day_5"] = df["weighted_rs_last_5_days"].apply(
            lambda x: x[4] if len(x) > 4 else np.nan
        )
        return df

    df_top_10 = add_rs_values(df_top_10)
    df_next_10 = add_rs_values(df_next_10)
    df_continuously_strong = add_rs_values(df_continuously_strong)
    df_gradually_strong = add_rs_values(df_gradually_strong)
    df_weakest = add_rs_values(df_weakest)

    # 生成TXT文件内容
    date_str = datetime.now().strftime("%Y/%m/%d")
    sheets = {
        "###Top 10 Strongest": df_top_10,
        "###Next 10 Strongest": df_next_10,
        "###Continuously Strong": df_continuously_strong,
        "###Gradually Strong": df_gradually_strong,
        "###Top 10 Weakest": df_weakest,
    }

    txt_content = f"###{date_str}"
    for sheet_name, df in sheets.items():
        symbols_list = ",".join(
            [
                f'BINANCE:{symbol.replace("/", "").replace(":USDT", ".p")}'
                for symbol in df["symbol"]
            ]
        )
        txt_content += f" {sheet_name},{symbols_list}\n"

    with open("binance_contracts_rs.txt", "w") as f:
        f.write(txt_content)

    # 匯出到Excel
    with pd.ExcelWriter("binance_contracts_rs.xlsx", engine="openpyxl") as writer:
        write_df_to_excel(writer, df_top_10, "Top 10 Strongest")
        write_df_to_excel(writer, df_next_10, "Next 10 Strongest")
        write_df_to_excel(writer, df_continuously_strong, "Continuously Strong")
        write_df_to_excel(writer, df_gradually_strong, "Gradually Strong")
        write_df_to_excel(writer, df_weakest, "Top 10 Weakest")


if __name__ == "__main__":
    main()
