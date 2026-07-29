import pandas as pd
from safe_fetch import safe_fetch_kline

STOCK_CODE = "600519"

print(f"正在获取 {STOCK_CODE} 的日K线数据...")

df = safe_fetch_kline(STOCK_CODE)

if df is None:
    print("❌ 获取数据失败")
    exit(1)

print("✅ 获取真实数据成功!")

print(f"\n数据条数: {len(df)}")
print(f"时间范围: {df['日期'].iloc[0]} - {df['日期'].iloc[-1]}")
print(f"\n最近5个交易日数据:")
print(df.tail(5).to_string())

csv_filename = f"stock_{STOCK_CODE}_daily.csv"
df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
print(f"\n✅ 数据已保存到 {csv_filename}")