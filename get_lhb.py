import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

today = datetime.now()
today_str = today.strftime("%Y%m%d")
today_display = today.strftime("%Y-%m-%d")

print(f"🎯 正在获取 {today_display} 的龙虎榜数据...")

try:
    lhb = ak.stock_lhb_jgmmtj_em(start_date="20260715", end_date=today_str)
    
    if lhb is None or lhb.empty:
        print(f"\n⚠️ {today_display} 暂无龙虎榜数据（可能非交易日）")
        print("尝试获取最近一个交易日的数据...")
        lhb = ak.stock_lhb_jgmmtj_em(start_date="20260715", end_date="20260722")
    
    print(f"\n📊 龙虎榜机构买卖数据 ({len(lhb)} 条):")
    print(lhb.head(20).to_string())
    
    latest_date = lhb['上榜日期'].iloc[0]
    print(f"\n📅 最新数据日期: {latest_date}")
    
    if latest_date == today_display:
        print("✅ 获取到今日最新龙虎榜数据!")
    else:
        print(f"ℹ️ 当前最新数据为 {latest_date}，{today_display} 可能非交易日")
        
except Exception as e:
    print(f"\n❌ 龙虎榜数据获取异常: {e}")
    print("尝试另一个接口...")
    try:
        lhb2 = ak.stock_lhb_detail_em(start_date="20260720", end_date=today_str)
        print(lhb2.head(20).to_string())
    except Exception as e2:
        print(f"❌ 备用接口也失败: {e2}")