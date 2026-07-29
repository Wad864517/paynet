import akshare as ak
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime, timedelta
from data_manager import save_to_csv, get_date_folder

# ============================================================
# daily_scan.py - 每日自动化选股扫描 v1.0
# 功能：技术面 + 资金面 综合分析，输出今日候选股票
# 用法：python daily_scan.py
# ============================================================

# ========== 配置区（按需修改） ==========
WATCH_LIST = [
    # 自选股池（换成你关注的股票）
    "600519",  # 贵州茅台
    "300750",  # 宁德时代
    "002594",  # 比亚迪
    "000858",  # 五粮液
    "601318",  # 中国平安
]

# 信号强度阈值
MIN_SIGNALS_TO_BUY = 2    # 至少2个买入信号才考虑建仓
RSI_OVERSOLD = 30          # RSI超卖线
RSI_OVERBOUGHT = 70        # RSI超买线
VOLUME_RATIO_THRESHOLD = 2 # 放量标准（量比>2）
# ==========================================

def fetch_with_retry(func, *args, **kwargs):
    """带智能重试的数据获取"""
    for attempt in range(5):
        try:
            result = func(*args, **kwargs)
            if result is None or (hasattr(result, 'empty') and result.empty):
                raise ValueError("返回数据为空")
            return result
        except Exception as e:
            if attempt < 4:
                delay = 2 * (1.5 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
            else:
                raise

def get_stock_data(code, days=120):
    """获取日K线数据"""
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    df = fetch_with_retry(
        ak.stock_zh_a_hist,
        symbol=code, period="daily",
        start_date=start_date, end_date=end_date, adjust="qfq"
    )
    df['日期'] = pd.to_datetime(df['日期'])
    return df

def calc_all_indicators(df):
    """计算全部技术指标"""
    # 均线
    df['MA5'] = df['收盘'].rolling(5).mean()
    df['MA10'] = df['收盘'].rolling(10).mean()
    df['MA20'] = df['收盘'].rolling(20).mean()
    df['MA60'] = df['收盘'].rolling(60).mean()
    
    # MACD
    ema12 = df['收盘'].ewm(span=12, adjust=False).mean()
    ema26 = df['收盘'].ewm(span=26, adjust=False).mean()
    df['DIF'] = ema12 - ema26
    df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
    df['MACD'] = 2 * (df['DIF'] - df['DEA'])
    
    # KDJ
    low9 = df['最低'].rolling(9).min()
    high9 = df['最高'].rolling(9).max()
    rsv = (df['收盘'] - low9) / (high9 - low9) * 100
    df['K'] = rsv.ewm(com=2, adjust=False).mean()
    df['D'] = df['K'].ewm(com=2, adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']
    
    # RSI
    delta = df['收盘'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + gain / loss))
    
    # 量比
    avg_vol = df['成交量'].rolling(5).mean().shift(1)
    df['量比'] = df['成交量'] / avg_vol
    
    return df

def analyze_one_stock(code):
    """分析单只股票，返回分析结果字典"""
    try:
        df = get_stock_data(code)
        df = calc_all_indicators(df)
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        result = {
            'code': code,
            'price': latest['收盘'],
            'change': latest['涨跌幅'],
            'volume_ratio': latest['量比'],
            'signals': [],
            'score': 0,  # 正数偏多，负数偏空
        }
        
        # --- 信号判断 ---
        # 1. 均线金叉
        if prev['MA5'] <= prev['MA20'] and latest['MA5'] > latest['MA20']:
            result['signals'].append("MA金叉")
            result['score'] += 2
        
        # 2. 均线死叉
        if prev['MA5'] >= prev['MA20'] and latest['MA5'] < latest['MA20']:
            result['signals'].append("MA死叉")
            result['score'] -= 2
        
        # 3. MACD金叉
        if prev['DIF'] <= prev['DEA'] and latest['DIF'] > latest['DEA']:
            result['signals'].append("MACD金叉")
            result['score'] += 2
        
        # 4. MACD死叉
        if prev['DIF'] >= prev['DEA'] and latest['DIF'] < latest['DEA']:
            result['signals'].append("MACD死叉")
            result['score'] -= 2
        
        # 5. KDJ超卖
        if latest['J'] < 20:
            result['signals'].append(f"KDJ超卖(J={latest['J']:.0f})")
            result['score'] += 1
        
        # 6. KDJ超买
        if latest['J'] > 80:
            result['signals'].append(f"KDJ超买(J={latest['J']:.0f})")
            result['score'] -= 1
        
        # 7. RSI超卖
        if latest['RSI'] < RSI_OVERSOLD:
            result['signals'].append(f"RSI超卖({latest['RSI']:.0f})")
            result['score'] += 1
        
        # 8. RSI超买
        if latest['RSI'] > RSI_OVERBOUGHT:
            result['signals'].append(f"RSI超买({latest['RSI']:.0f})")
            result['score'] -= 1
        
        # 9. 放量突破
        if latest['量比'] > VOLUME_RATIO_THRESHOLD and latest['收盘'] > latest['MA20']:
            result['signals'].append(f"放量突破20日线(量比{latest['量比']:.1f})")
            result['score'] += 2
        
        # 10. 多头排列
        if latest['MA5'] > latest['MA10'] > latest['MA20'] > latest['MA60']:
            result['signals'].append("均线多头排列")
            result['score'] += 2
        
        # 11. 空头排列
        if latest['MA5'] < latest['MA10'] < latest['MA20'] < latest['MA60']:
            result['signals'].append("均线空头排列")
            result['score'] -= 2
        
        return result
        
    except Exception as e:
        return {'code': code, 'error': str(e)}

def get_north_flow_summary():
    """获取北向资金概况"""
    try:
        north_summary = fetch_with_retry(ak.stock_hsgt_fund_flow_summary_em)
        north_sh = north_summary[north_summary['板块'] == '沪股通']
        north_sz = north_summary[north_summary['板块'] == '深股通']
        total_net = north_sh['成交净买额'].sum() + north_sz['成交净买额'].sum()
        return total_net
    except Exception as e:
        print(f"  ❌ 北向资金获取失败: {e}")
        return None

def run_daily_scan():
    """执行每日扫描"""
    now = datetime.now()
    print(f"""
╔══════════════════════════════════════════════════╗
║         📊 每日量化选股扫描报告                  ║
║         {now.strftime('%Y-%m-%d %H:%M')}                    ║
╚══════════════════════════════════════════════════╝
    """)
    
    # 1. 宏观资金面
    print("━" * 50)
    print("📌 一、宏观资金面")
    print("━" * 50)
    north_5d = get_north_flow_summary()
    if north_5d is not None:
        print(f"  北向资金今日: {north_5d:+.2f} 亿元")
        if north_5d > 50:
            print(f"  状态: 🟢 外资大幅流入")
        elif north_5d > 0:
            print(f"  状态: 🟡 外资小幅流入")
        elif north_5d > -50:
            print(f"  状态: 🟡 外资小幅流出")
        else:
            print(f"  状态: 🔴 外资大幅流出")
    else:
        print("  北向资金数据暂时无法获取")
    
    # 2. 自选股逐个分析
    print(f"\n{'━' * 50}")
    print(f"📌 二、自选股技术面分析（共{len(WATCH_LIST)}只）")
    print("━" * 50)
    
    results = []
    for code in WATCH_LIST:
        r = analyze_one_stock(code)
        results.append(r)
        
        if 'error' in r:
            print(f"\n  ❌ {code}: 分析失败 - {r['error']}")
            continue
        
        emoji = "🟢" if r['score'] >= 2 else ("🔴" if r['score'] <= -2 else "🟡")
        print(f"\n  {emoji} {code} | 收盘:{r['price']:.2f} | 涨跌:{r['change']:+.2f}% | 量比:{r['volume_ratio']:.1f} | 得分:{r['score']:+d}")
        if r['signals']:
            print(f"     信号: {' | '.join(r['signals'])}")
        else:
            print(f"     信号: 无明显信号")
    
    # 3. 汇总推荐
    print(f"\n{'━' * 50}")
    print("📌 三、综合推荐")
    print("━" * 50)
    
    # 按得分排序
    valid_results = [r for r in results if 'error' not in r]
    sorted_results = sorted(valid_results, key=lambda x: x['score'], reverse=True)
    
    buy_candidates = [r for r in sorted_results if r['score'] >= MIN_SIGNALS_TO_BUY]
    avoid_candidates = [r for r in sorted_results if r['score'] <= -MIN_SIGNALS_TO_BUY]
    
    if buy_candidates:
        print(f"\n  🟢 可关注建仓:")
        for r in buy_candidates:
            print(f"     {r['code']} (得分:{r['score']:+d}) - {' | '.join(r['signals'])}")
    
    if avoid_candidates:
        print(f"\n  🔴 建议回避:")
        for r in avoid_candidates:
            print(f"     {r['code']} (得分:{r['score']:+d}) - {' | '.join(r['signals'])}")
    
    neutral = [r for r in sorted_results if -MIN_SIGNALS_TO_BUY < r['score'] < MIN_SIGNALS_TO_BUY]
    if neutral:
        print(f"\n  🟡 观望为主:")
        for r in neutral:
            print(f"     {r['code']} (得分:{r['score']:+d})")
    
    print(f"\n{'━' * 50}")
    print("⚠️ 以上仅为技术面参考，不构成投资建议。")
    print("   请结合基本面、消息面综合判断后再做决策。")
    print(f"{'━' * 50}")

if __name__ == "__main__":
    run_daily_scan()