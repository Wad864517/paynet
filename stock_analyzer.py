import akshare as ak
import pandas as pd
import numpy as np
import time
import random
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler('stock_analyzer.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('stock_analyzer')

# ============================================================
# stock_analyzer.py - 个人量化分析工具 v1.1
# 功能：自动分析个股技术面，生成买卖信号
# 新增：详细日志输出
# ============================================================

def get_stock_data(code, days=120, max_retries=5):
    """获取股票日K线数据，带智能重试"""
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    
    logger.info(f"[数据获取] 开始获取股票 {code} 数据")
    logger.info(f"[数据获取] 日期范围: {start_date} ~ {end_date}, 天数: {days}")
    
    for attempt in range(max_retries):
        try:
            logger.debug(f"[数据获取] 第 {attempt+1}/{max_retries} 次尝试获取 {code}")
            df = ak.stock_zh_a_hist(
                symbol=code, period="daily",
                start_date=start_date, end_date=end_date, adjust="qfq"
            )
            if df is None or df.empty:
                raise ValueError("返回数据为空")
            df['日期'] = pd.to_datetime(df['日期'])
            logger.info(f"[数据获取] ✅ 成功获取 {code} 数据，共 {len(df)} 条记录")
            logger.info(f"[数据获取] 时间范围: {df['日期'].iloc[0].strftime('%Y-%m-%d')} ~ {df['日期'].iloc[-1].strftime('%Y-%m-%d')}")
            return df
        except Exception as e:
            if attempt < max_retries - 1:
                delay = 2 * (1.5 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[数据获取] ⚠️ 获取{code}失败({str(e)[:30]}...)，{delay:.1f}秒后重试")
                time.sleep(delay)
            else:
                logger.error(f"[数据获取] ❌ 网络获取失败，使用演示数据")
                return generate_demo_data(code, days)

def generate_demo_data(code, days):
    """生成演示数据，用于网络不可用时的回退"""
    np.random.seed(int(code[-3:]))
    dates = pd.date_range(end=datetime.now(), periods=days, freq='B')
    
    base_price = 1800 if code == "600519" else (10 if code == "000001" else 30)
    
    prices = [base_price]
    for _ in range(1, days):
        change = np.random.normal(0, base_price * 0.02)
        prices.append(max(prices[-1] + change, base_price * 0.5))
    
    df = pd.DataFrame({
        '日期': dates,
        '开盘': prices,
        '收盘': prices,
        '最高': [p * (1 + np.random.uniform(0, 0.03)) for p in prices],
        '最低': [p * (1 - np.random.uniform(0, 0.03)) for p in prices],
        '成交量': [np.random.randint(100000, 1000000) for _ in range(days)],
        '成交额': [p * v * 100 for p, v in zip(prices, [np.random.randint(100000, 1000000) for _ in range(days)])],
        '振幅': [np.random.uniform(1, 5) for _ in range(days)],
        '涨跌幅': [0.0] + [(prices[i] - prices[i-1])/prices[i-1]*100 for i in range(1, days)],
        '涨跌额': [0.0] + [prices[i] - prices[i-1] for i in range(1, days)],
        '换手率': [np.random.uniform(0.5, 5) for _ in range(days)]
    })
    logger.info(f"[数据获取] 已生成演示数据，共 {len(df)} 条记录")
    return df

# ---------- 技术指标计算函数 ----------

def calc_ma(df):
    """均线系统：MA5/MA10/MA20/MA60"""
    logger.info("[指标计算] 开始计算均线系统 (MA5/MA10/MA20/MA60)")
    df['MA5'] = df['收盘'].rolling(5).mean()
    df['MA10'] = df['收盘'].rolling(10).mean()
    df['MA20'] = df['收盘'].rolling(20).mean()
    df['MA60'] = df['收盘'].rolling(60).mean()
    
    latest = df.iloc[-1]
    logger.info(f"[指标计算] ✅ 均线计算完成")
    logger.info(f"[指标计算]   MA5={latest['MA5']:.2f}  MA10={latest['MA10']:.2f}  MA20={latest['MA20']:.2f}  MA60={latest['MA60']:.2f}")
    return df

def calc_macd(df, fast=12, slow=26, signal=9):
    """MACD指标：判断趋势方向和动量"""
    logger.info(f"[指标计算] 开始计算MACD (fast={fast}, slow={slow}, signal={signal})")
    ema_fast = df['收盘'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['收盘'].ewm(span=slow, adjust=False).mean()
    df['DIF'] = ema_fast - ema_slow
    df['DEA'] = df['DIF'].ewm(span=signal, adjust=False).mean()
    df['MACD'] = 2 * (df['DIF'] - df['DEA'])
    
    latest = df.iloc[-1]
    logger.info(f"[指标计算] ✅ MACD计算完成")
    logger.info(f"[指标计算]   DIF={latest['DIF']:.3f}  DEA={latest['DEA']:.3f}  MACD={latest['MACD']:.3f}")
    return df

def calc_kdj(df, n=9, m1=3, m2=3):
    """KDJ指标：判断超买超卖"""
    logger.info(f"[指标计算] 开始计算KDJ (n={n}, m1={m1}, m2={m2})")
    low_min = df['最低'].rolling(n).min()
    high_max = df['最高'].rolling(n).max()
    rsv = (df['收盘'] - low_min) / (high_max - low_min) * 100
    df['K'] = rsv.ewm(com=m1-1, adjust=False).mean()
    df['D'] = df['K'].ewm(com=m2-1, adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']
    
    latest = df.iloc[-1]
    logger.info(f"[指标计算] ✅ KDJ计算完成")
    logger.info(f"[指标计算]   K={latest['K']:.1f}  D={latest['D']:.1f}  J={latest['J']:.1f}")
    
    if latest['J'] < 20:
        logger.info(f"[指标计算]   ⚠️ J值={latest['J']:.1f} 处于超卖区")
    elif latest['J'] > 80:
        logger.info(f"[指标计算]   ⚠️ J值={latest['J']:.1f} 处于超买区")
    return df

def calc_rsi(df, period=14):
    """RSI指标：相对强弱指标"""
    logger.info(f"[指标计算] 开始计算RSI (period={period})")
    delta = df['收盘'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    latest = df.iloc[-1]
    logger.info(f"[指标计算] ✅ RSI计算完成")
    logger.info(f"[指标计算]   RSI={latest['RSI']:.1f}")
    
    if latest['RSI'] < 30:
        logger.info(f"[指标计算]   ⚠️ RSI={latest['RSI']:.1f} 处于超卖区")
    elif latest['RSI'] > 70:
        logger.info(f"[指标计算]   ⚠️ RSI={latest['RSI']:.1f} 处于超买区")
    return df

def calc_volume_ratio(df, period=5):
    """量比：当日成交量 / 过去N日平均成交量"""
    logger.info(f"[指标计算] 开始计算量比 (period={period})")
    avg_vol = df['成交量'].rolling(period).mean().shift(1)
    df['量比'] = df['成交量'] / avg_vol
    
    latest = df.iloc[-1]
    logger.info(f"[指标计算] ✅ 量比计算完成")
    logger.info(f"[指标计算]   量比={latest['量比']:.2f}")
    
    if latest['量比'] > 2:
        logger.info(f"[指标计算]   ⚠️ 量比={latest['量比']:.2f} 放量")
    elif latest['量比'] < 0.6:
        logger.info(f"[指标计算]   ⚠️ 量比={latest['量比']:.2f} 缩量")
    return df

# ---------- 信号生成函数 ----------

def generate_signals(df):
    """根据技术指标生成买卖信号"""
    logger.info("[信号判断] 开始信号判断...")
    signals = []
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 1. 均线金叉/死叉
    logger.debug(f"[信号判断] 均线交叉检测: MA5(今)={latest['MA5']:.2f}, MA20(今)={latest['MA20']:.2f}, MA5(昨)={prev['MA5']:.2f}, MA20(昨)={prev['MA20']:.2f}")
    if prev['MA5'] <= prev['MA20'] and latest['MA5'] > latest['MA20']:
        signals.append(("📈 买入", "MA5上穿MA20，均线金叉"))
        logger.info(f"[信号判断] 📈 买入信号: MA5上穿MA20，均线金叉")
    elif prev['MA5'] >= prev['MA20'] and latest['MA5'] < latest['MA20']:
        signals.append(("📉 卖出", "MA5下穿MA20，均线死叉"))
        logger.info(f"[信号判断] 📉 卖出信号: MA5下穿MA20，均线死叉")
    else:
        logger.debug(f"[信号判断] 无均线交叉信号")
    
    # 2. MACD金叉/死叉
    logger.debug(f"[信号判断] MACD交叉检测: DIF(今)={latest['DIF']:.3f}, DEA(今)={latest['DEA']:.3f}, DIF(昨)={prev['DIF']:.3f}, DEA(昨)={prev['DEA']:.3f}")
    if prev['DIF'] <= prev['DEA'] and latest['DIF'] > latest['DEA']:
        signals.append(("📈 买入", "MACD金叉，DIF上穿DEA"))
        logger.info(f"[信号判断] 📈 买入信号: MACD金叉，DIF上穿DEA")
    elif prev['DIF'] >= prev['DEA'] and latest['DIF'] < latest['DEA']:
        signals.append(("📉 卖出", "MACD死叉，DIF下穿DEA"))
        logger.info(f"[信号判断] 📉 卖出信号: MACD死叉，DIF下穿DEA")
    else:
        logger.debug(f"[信号判断] 无MACD交叉信号")
    
    # 3. KDJ超买/超卖
    logger.debug(f"[信号判断] KDJ检测: K={latest['K']:.1f}, D={latest['D']:.1f}, J={latest['J']:.1f}")
    if latest['J'] < 20:
        signals.append(("📈 关注", f"KDJ超卖区 J={latest['J']:.1f}，可能反弹"))
        logger.info(f"[信号判断] 📈 关注信号: KDJ超卖区 J={latest['J']:.1f}")
    elif latest['J'] > 80:
        signals.append(("📉 警惕", f"KDJ超买区 J={latest['J']:.1f}，注意回调"))
        logger.info(f"[信号判断] 📉 警惕信号: KDJ超买区 J={latest['J']:.1f}")
    else:
        logger.debug(f"[信号判断] KDJ处于正常区间")
    
    # 4. RSI极端值
    logger.debug(f"[信号判断] RSI检测: RSI={latest['RSI']:.1f}")
    if latest['RSI'] < 30:
        signals.append(("📈 关注", f"RSI超卖 RSI={latest['RSI']:.1f}"))
        logger.info(f"[信号判断] 📈 关注信号: RSI超卖 RSI={latest['RSI']:.1f}")
    elif latest['RSI'] > 70:
        signals.append(("📉 警惕", f"RSI超买 RSI={latest['RSI']:.1f}"))
        logger.info(f"[信号判断] 📉 警惕信号: RSI超买 RSI={latest['RSI']:.1f}")
    else:
        logger.debug(f"[信号判断] RSI处于正常区间")
    
    # 5. 放量突破
    logger.debug(f"[信号判断] 放量突破检测: 量比={latest['量比']:.2f}, 收盘={latest['收盘']:.2f}, MA20={latest['MA20']:.2f}")
    if latest['量比'] > 2 and latest['收盘'] > latest['MA20']:
        signals.append(("📈 买入", f"放量突破20日均线，量比={latest['量比']:.1f}"))
        logger.info(f"[信号判断] 📈 买入信号: 放量突破20日均线，量比={latest['量比']:.1f}")
    else:
        logger.debug(f"[信号判断] 未满足放量突破条件")
    
    # 6. 缩量回踩支撑
    price_diff = abs(latest['收盘'] - latest['MA20']) / latest['MA20']
    logger.debug(f"[信号判断] 缩量回踩检测: 量比={latest['量比']:.2f}, 偏离MA20={price_diff:.4f}")
    if latest['量比'] < 0.6 and price_diff < 0.02:
        signals.append(("📈 关注", "缩量回踩20日均线附近，可能获得支撑"))
        logger.info(f"[信号判断] 📈 关注信号: 缩量回踩20日均线附近")
    else:
        logger.debug(f"[信号判断] 未满足缩量回踩条件")
    
    # 7. 多头排列
    logger.debug(f"[信号判断] 均线排列检测: MA5={latest['MA5']:.2f} > MA10={latest['MA10']:.2f} > MA20={latest['MA20']:.2f} > MA60={latest['MA60']:.2f}")
    if latest['MA5'] > latest['MA10'] > latest['MA20'] > latest['MA60']:
        signals.append(("📈 强势", "均线多头排列，趋势向上"))
        logger.info(f"[信号判断] 📈 强势信号: 均线多头排列")
    else:
        logger.debug(f"[信号判断] 非多头排列")
    
    # 8. 空头排列
    if latest['MA5'] < latest['MA10'] < latest['MA20'] < latest['MA60']:
        signals.append(("📉 弱势", "均线空头排列，趋势向下"))
        logger.info(f"[信号判断] 📉 弱势信号: 均线空头排列")
    else:
        logger.debug(f"[信号判断] 非空头排列")
    
    logger.info(f"[信号判断] ✅ 信号判断完成，共生成 {len(signals)} 个信号")
    return signals

# ---------- 主分析函数 ----------

def analyze_stock(code):
    """对一只股票进行完整技术分析"""
    logger.info(f"\n{'='*70}")
    logger.info(f"[分析开始] 股票分析报告：{code}")
    logger.info(f"{'='*70}")
    
    # 获取数据
    logger.info("[阶段] 1/4 - 数据获取")
    df = get_stock_data(code)
    
    # 计算指标
    logger.info("[阶段] 2/4 - 指标计算")
    df = calc_ma(df)
    df = calc_macd(df)
    df = calc_kdj(df)
    df = calc_rsi(df)
    df = calc_volume_ratio(df)
    
    latest = df.iloc[-1]
    
    # 输出最新行情
    logger.info("[阶段] 3/4 - 行情输出")
    logger.info(f"[行情] 最新交易日: {latest['日期'].strftime('%Y-%m-%d')}")
    logger.info(f"[行情] 收盘价: {latest['收盘']:.2f}  涨跌幅: {latest['涨跌幅']:.2f}%")
    logger.info(f"[行情] 成交量: {latest['成交量']:.0f}  量比: {latest['量比']:.2f}")
    
    # 生成信号
    logger.info("[阶段] 4/4 - 信号生成")
    signals = generate_signals(df)
    
    # 综合评分
    buy_count = sum(1 for s, _ in signals if "买入" in s or "强势" in s)
    sell_count = sum(1 for s, _ in signals if "卖出" in s or "弱势" in s)
    watch_count = sum(1 for s, _ in signals if "关注" in s or "警惕" in s)
    
    logger.info(f"\n[综合评估] 买入信号: {buy_count}个 | 卖出信号: {sell_count}个 | 观望信号: {watch_count}个")
    
    if buy_count >= 2 and sell_count == 0:
        logger.info(f"[综合评估] 🟢 建议：偏多，可以考虑建仓")
    elif sell_count >= 2 and buy_count == 0:
        logger.info(f"[综合评估] 🔴 建议：偏空，建议回避或减仓")
    else:
        logger.info(f"[综合评估] 🟡 建议：信号混合，建议观望或轻仓试探")
    
    csv_filename = f"analysis_{code}.csv"
    df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
    logger.info(f"[分析结束] 分析数据已保存到: {csv_filename}")
    
    return df, signals

# ---------- 运行 ----------
if __name__ == "__main__":
    logger.info(f"\n\n{'='*70}")
    logger.info(f"[程序启动] stock_analyzer v1.1 开始运行")
    logger.info(f"[程序启动] 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*70}")
    
    stocks = ["600519", "300750", "002594"]
    
    for i, code in enumerate(stocks):
        logger.info(f"\n[进度] 正在分析第 {i+1}/{len(stocks)} 只股票: {code}")
        try:
            analyze_stock(code)
        except Exception as e:
            logger.error(f"[错误] 分析 {code} 失败: {e}", exc_info=True)
    
    logger.info(f"\n\n{'='*70}")
    logger.info(f"[程序结束] 分析完成！时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*70}")