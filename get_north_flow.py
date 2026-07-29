from safe_fetch import safe_fetch_north_flow

print("正在获取北向资金数据...")

north = safe_fetch_north_flow(symbol="北向资金")

if north is None:
    print("❌ 获取北向资金数据失败")
    exit(1)

print(f"\n最近10个交易日北向资金净买入（亿元）:")
print(north.tail(10).to_string())

recent_5 = north.tail(5)
total_flow = recent_5.iloc[:, 1].sum() if len(recent_5.columns) > 1 else 0
print(f"\n📊 近5日北向资金合计: {total_flow:.2f} 亿元")
if total_flow > 0:
    print("💚 外资近5日整体净买入，态度偏多")
else:
    print("💔 外资近5日整体净卖出，态度偏空")