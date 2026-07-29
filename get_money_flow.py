import pandas as pd
from safe_fetch import safe_fetch_money_flow

STOCK_CODE = "600196"

print(f"正在获取 {STOCK_CODE} 的资金流向...")

flow = safe_fetch_money_flow(STOCK_CODE, market="sh")

if flow is None:
    print("❌ 获取资金流向失败")
    print("提示: 资金流向接口可能需要level-2权限，或者换个股票代码试试")
    exit(1)

print(f"\n最近5日资金流向:")
print(flow.tail(5).to_string())

latest = flow.iloc[-1]
print(f"\n📊 今日资金流向判断:")
print(f"  主力净流入: {latest.get('主力净流入-净额', 'N/A')}")
print(f"  超大单净流入: {latest.get('超大单净流入-净额', 'N/A')}")