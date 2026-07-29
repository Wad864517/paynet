import time
import random
import akshare as ak

def safe_fetch_kline(symbol, start_date="20250101", end_date="20260723", adjust="qfq", max_retries=5):
    """带智能重试的K线数据获取，解决东方财富反爬问题"""
    for attempt in range(max_retries):
        try:
            data = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            if not data.empty:
                return data
            else:
                raise ValueError("返回数据为空")
        except Exception as e:
            if attempt < max_retries - 1:
                delay = 2 * (1.5 ** attempt) + random.uniform(0, 1)
                print(f"  ⚠️ 第{attempt+1}次失败({str(e)[:50]}...)，{delay:.1f}秒后重试...")
                time.sleep(delay)
            else:
                print(f"  ❌ {symbol} 获取失败，跳过")
                return None

def safe_fetch_money_flow(symbol, market="sh", max_retries=5):
    """带智能重试的资金流向数据获取"""
    for attempt in range(max_retries):
        try:
            data = ak.stock_individual_fund_flow(stock=symbol, market=market)
            if not data.empty:
                return data
            else:
                raise ValueError("返回数据为空")
        except Exception as e:
            if attempt < max_retries - 1:
                delay = 2 * (1.5 ** attempt) + random.uniform(0, 1)
                print(f"  ⚠️ 第{attempt+1}次失败({str(e)[:50]}...)，{delay:.1f}秒后重试...")
                time.sleep(delay)
            else:
                print(f"  ❌ {symbol} 资金流向获取失败，跳过")
                return None

def safe_fetch_north_flow(symbol="北向资金", max_retries=5):
    """带智能重试的北向资金数据获取"""
    for attempt in range(max_retries):
        try:
            data = ak.stock_hsgt_hist_em(symbol=symbol)
            if not data.empty:
                return data
            else:
                raise ValueError("返回数据为空")
        except Exception as e:
            if attempt < max_retries - 1:
                delay = 2 * (1.5 ** attempt) + random.uniform(0, 1)
                print(f"  ⚠️ 第{attempt+1}次失败({str(e)[:50]}...)，{delay:.1f}秒后重试...")
                time.sleep(delay)
            else:
                print(f"  ❌ 北向资金获取失败，跳过")
                return None

def batch_fetch(stock_list, fetch_func, **kwargs):
    """批量获取股票数据，带频率控制"""
    results = {}
    for i, code in enumerate(stock_list):
        print(f"[{i+1}/{len(stock_list)}] 正在获取 {code}...")
        df = fetch_func(code, **kwargs)
        
        if df is not None:
            results[code] = df
            print(f"  ✅ 获取成功，共{len(df)}条数据")
        
        time.sleep(random.uniform(3, 5))
        
        if (i + 1) % 10 == 0:
            print(f"  💤 已获取{i+1}只，暂停20秒避免限流...")
            time.sleep(20)
    
    return results

if __name__ == "__main__":
    print("=== safe_fetch 测试 ===")
    print("测试1: 获取单只股票K线数据")
    df = safe_fetch_kline("600519")
    if df is not None:
        print(f"成功获取 {len(df)} 条数据")
        print("最近5条:")
        print(df.tail(5)[["日期", "开盘", "收盘", "最高", "最低"]].to_string())
    
    print("\n测试2: 获取北向资金数据")
    north = safe_fetch_north_flow("北向资金")
    if north is not None:
        print(f"成功获取 {len(north)} 条数据")
        print("最近5条:")
        print(north.tail(5)[["日期", "当日成交净买额", "买入成交额", "卖出成交额"]].to_string())