import akshare as ak
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime, timedelta
from data_manager import save_to_csv, get_date_folder

STOCK_CODE = "600196"
today = datetime.now().strftime("%Y-%m-%d")

print(f"\n{'='*70}")
print(f"📊 获取股票 {STOCK_CODE} 所有分析结果")
print(f"日期: {today}")
print(f"数据保存目录: {get_date_folder()}")
print(f"{'='*70}")

def fetch_with_retry(func, *args, **kwargs):
    for attempt in range(5):
        try:
            result = func(*args, **kwargs)
            if result is None or (hasattr(result, 'empty') and result.empty):
                raise ValueError("返回数据为空")
            return result
        except Exception as e:
            if attempt < 4:
                delay = 2 * (1.5 ** attempt) + random.uniform(0, 1)
                print(f"  ⚠️ 第{attempt+1}次失败，{delay:.1f}秒后重试...")
                time.sleep(delay)
            else:
                raise

print("\n" + "="*70)
print("📈 1. 获取K线数据")
print("="*70)
try:
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=120)).strftime("%Y%m%d")
    
    df = fetch_with_retry(
        ak.stock_zh_a_hist,
        symbol=STOCK_CODE,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust="qfq"
    )
    
    df['日期'] = pd.to_datetime(df['日期'])
    
    print(f"✅ 获取成功，共 {len(df)} 条数据")
    print(f"时间范围: {df['日期'].iloc[0]} - {df['日期'].iloc[-1]}")
    print("\n最近5个交易日数据:")
    print(df.tail(5)[["日期", "开盘", "收盘", "最高", "最低", "成交量"]].to_string())
    
    save_to_csv(df, f"stock_{STOCK_CODE}_daily.csv")
    
except Exception as e:
    print(f"❌ 获取K线数据失败: {e}")

print("\n" + "="*70)
print("💹 2. 技术指标分析")
print("="*70)
try:
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=120)).strftime("%Y%m%d")
    
    df = fetch_with_retry(
        ak.stock_zh_a_hist,
        symbol=STOCK_CODE,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust="qfq"
    )
    
    df['日期'] = pd.to_datetime(df['日期'])
    
    df['MA5'] = df['收盘'].rolling(5).mean()
    df['MA10'] = df['收盘'].rolling(10).mean()
    df['MA20'] = df['收盘'].rolling(20).mean()
    df['MA60'] = df['收盘'].rolling(60).mean()
    
    ema_fast = df['收盘'].ewm(span=12, adjust=False).mean()
    ema_slow = df['收盘'].ewm(span=26, adjust=False).mean()
    df['DIF'] = ema_fast - ema_slow
    df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
    df['MACD'] = 2 * (df['DIF'] - df['DEA'])
    
    low_min = df['最低'].rolling(9).min()
    high_max = df['最高'].rolling(9).max()
    rsv = (df['收盘'] - low_min) / (high_max - low_min) * 100
    df['K'] = rsv.ewm(com=2, adjust=False).mean()
    df['D'] = df['K'].ewm(com=2, adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']
    
    delta = df['收盘'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    avg_vol = df['成交量'].rolling(5).mean().shift(1)
    df['量比'] = df['成交量'] / avg_vol
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    print(f"\n📅 最新交易日: {latest['日期'].strftime('%Y-%m-%d')}")
    print(f"💰 收盘价: {latest['收盘']:.2f}  涨跌幅: {latest['涨跌幅']:.2f}%")
    print(f"📊 成交量: {latest['成交量']:.0f}  量比: {latest['量比']:.2f}")
    
    print(f"\n--- 技术指标 ---")
    print(f"MA5={latest['MA5']:.2f}  MA10={latest['MA10']:.2f}  MA20={latest['MA20']:.2f}  MA60={latest['MA60']:.2f}")
    print(f"DIF={latest['DIF']:.3f}  DEA={latest['DEA']:.3f}  MACD={latest['MACD']:.3f}")
    print(f"K={latest['K']:.1f}  D={latest['D']:.1f}  J={latest['J']:.1f}")
    print(f"RSI={latest['RSI']:.1f}")
    
    signals = []
    if prev['MA5'] <= prev['MA20'] and latest['MA5'] > latest['MA20']:
        signals.append(("📈 买入", "MA5上穿MA20，均线金叉"))
    elif prev['MA5'] >= prev['MA20'] and latest['MA5'] < latest['MA20']:
        signals.append(("📉 卖出", "MA5下穿MA20，均线死叉"))
    
    if prev['DIF'] <= prev['DEA'] and latest['DIF'] > latest['DEA']:
        signals.append(("📈 买入", "MACD金叉，DIF上穿DEA"))
    elif prev['DIF'] >= prev['DEA'] and latest['DIF'] < latest['DEA']:
        signals.append(("📉 卖出", "MACD死叉，DIF下穿DEA"))
    
    if latest['J'] < 20:
        signals.append(("📈 关注", f"KDJ超卖区 J={latest['J']:.1f}"))
    elif latest['J'] > 80:
        signals.append(("📉 警惕", f"KDJ超买区 J={latest['J']:.1f}"))
    
    if latest['RSI'] < 30:
        signals.append(("📈 关注", f"RSI超卖 RSI={latest['RSI']:.1f}"))
    elif latest['RSI'] > 70:
        signals.append(("📉 警惕", f"RSI超买 RSI={latest['RSI']:.1f}"))
    
    if latest['MA5'] > latest['MA10'] > latest['MA20'] > latest['MA60']:
        signals.append(("📈 强势", "均线多头排列"))
    elif latest['MA5'] < latest['MA10'] < latest['MA20'] < latest['MA60']:
        signals.append(("📉 弱势", "均线空头排列"))
    
    print(f"\n--- 信号判断 ---")
    if signals:
        for signal_type, desc in signals:
            print(f"  {signal_type} | {desc}")
    else:
        print("  ⚪ 无明显信号")
    
    save_to_csv(df, f"analysis_{STOCK_CODE}.csv")
    
except Exception as e:
    print(f"❌ 技术指标分析失败: {e}")

print("\n" + "="*70)
print("💰 3. 资金流向")
print("="*70)
try:
    flow = fetch_with_retry(
        ak.stock_individual_fund_flow,
        stock=STOCK_CODE,
        market="sh"
    )
    
    print(f"\n最近5日资金流向:")
    print(flow.tail(5).to_string())
    
    latest = flow.iloc[-1]
    print(f"\n📊 资金流向判断:")
    print(f"  主力净流入: {latest.get('主力净流入-净额', 'N/A')}")
    print(f"  超大单净流入: {latest.get('超大单净流入-净额', 'N/A')}")
    
    save_to_csv(flow, f"money_flow_{STOCK_CODE}.csv")
    
except Exception as e:
    print(f"❌ 获取资金流向失败: {e}")
    print("提示: 资金流向接口可能需要level-2权限")

print("\n" + "="*70)
print("🏆 4. 龙虎榜数据")
print("="*70)
try:
    lhb = fetch_with_retry(
        ak.stock_lhb_jgmmtj_em,
        start_date="20260715",
        end_date=datetime.now().strftime("%Y%m%d")
    )
    
    stock_lhb = lhb[lhb['代码'] == STOCK_CODE]
    
    if stock_lhb.empty:
        print(f"ℹ️ {STOCK_CODE} 近期未登上龙虎榜")
    else:
        print(f"\n{STOCK_CODE} 龙虎榜数据 ({len(stock_lhb)} 条):")
        print(stock_lhb.to_string())
        
        save_to_csv(stock_lhb, f"lhb_{STOCK_CODE}.csv")
        
except Exception as e:
    print(f"❌ 获取龙虎榜数据失败: {e}")

print("\n" + "="*70)
print(f"✅ {STOCK_CODE} 所有分析完成!")
print("="*70)