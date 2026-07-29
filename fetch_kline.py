import time
import random
import traceback
import akshare as ak
import pandas as pd
from requests.exceptions import ConnectionError, Timeout, RequestException

def fetch_stock_kline(symbol, start_date="20250101", end_date="20260723", adjust="qfq", max_retries=5):
    """
    获取股票K线数据，带智能重试和详细异常处理
    
    参数:
        symbol: 股票代码，如 "600519"
        start_date: 开始日期，格式 "YYYYMMDD"
        end_date: 结束日期，格式 "YYYYMMDD"
        adjust: 复权方式，"qfq"前复权, "hfq"后复权, ""不复权
        max_retries: 最大重试次数
    
    返回:
        pandas.DataFrame: K线数据，失败返回None
    """
    print(f"🔍 开始获取股票 [{symbol}] K线数据...")
    print(f"   日期范围: {start_date} ~ {end_date}")
    print(f"   复权方式: {adjust if adjust else '不复权'}")
    
    for attempt in range(max_retries):
        attempt_num = attempt + 1
        try:
            print(f"\n   📡 第 {attempt_num}/{max_retries} 次请求...")
            
            data = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
                timeout=15
            )
            
            if data is None:
                raise ValueError("AKShare返回None")
                
            if data.empty:
                raise ValueError("返回数据为空DataFrame")
                
            expected_cols = ["日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额"]
            missing_cols = [col for col in expected_cols if col not in data.columns]
            if missing_cols:
                raise ValueError(f"缺少必要字段: {missing_cols}")
                
            print(f"   ✅ 请求成功! 获取到 {len(data)} 条数据")
            print(f"   📊 数据时间范围: {data['日期'].iloc[0]} ~ {data['日期'].iloc[-1]}")
            return data
            
        except ConnectionError as e:
            error_msg = f"网络连接错误: {str(e)[:60]}"
            print(f"   ❌ {error_msg}")
            
        except Timeout as e:
            error_msg = f"请求超时: {str(e)[:60]}"
            print(f"   ❌ {error_msg}")
            
        except RequestException as e:
            error_msg = f"HTTP请求异常: {str(e)[:60]}"
            print(f"   ❌ {error_msg}")
            
        except ValueError as e:
            error_msg = f"数据验证失败: {str(e)}"
            print(f"   ❌ {error_msg}")
            
        except AttributeError as e:
            error_msg = f"AKShare API属性错误: {str(e)}"
            print(f"   ❌ {error_msg}")
            print(f"   💡 可能是AKShare版本更新导致API变更")
            
        except Exception as e:
            error_msg = f"未知异常: {type(e).__name__}: {str(e)[:60]}"
            print(f"   ❌ {error_msg}")
            if attempt == 0:
                print(f"   📝 详细错误信息:")
                traceback.print_exc(limit=5)
                
        if attempt < max_retries - 1:
            delay = 2 * (1.5 ** attempt) + random.uniform(0, 1)
            print(f"   ⏳ {delay:.1f}秒后进行第 {attempt_num + 1} 次重试...")
            time.sleep(delay)
        else:
            print(f"\n   ❌❌❌ [{symbol}] 获取失败! 已尝试 {max_retries} 次")
            print(f"   💡 可能原因:")
            print(f"      1. 网络连接不稳定或被防火墙拦截")
            print(f"      2. 东方财富API反爬策略限制")
            print(f"      3. AKShare版本与API不兼容")
            print(f"      4. 股票代码格式错误")
            print(f"   💡 建议:")
            print(f"      1. 检查网络连接，尝试使用代理")
            print(f"      2. 稍后再试，避免频繁请求")
            print(f"      3. 更新AKShare: pip install akshare --upgrade")
            print(f"      4. 验证股票代码是否正确")
            return None

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 股票K线数据获取工具")
    print("=" * 60)
    print()
    
    test_stock = "600519"
    print(f"测试股票: {test_stock} (贵州茅台)")
    print()
    
    df = fetch_stock_kline(test_stock)
    
    if df is not None:
        print("\n" + "=" * 60)
        print("📊 获取成功! 最近5个交易日数据:")
        print("=" * 60)
        print(df.tail(5)[["日期", "开盘", "收盘", "最高", "最低", "成交量"]].to_string())
        
        csv_filename = f"stock_{test_stock}_daily.csv"
        df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
        print(f"\n💾 数据已保存到: {csv_filename}")
    else:
        print("\n" + "=" * 60)
        print("❌ 获取失败，请检查网络或稍后再试")
        print("=" * 60)