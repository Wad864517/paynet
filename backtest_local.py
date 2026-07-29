# -*- coding: utf-8 -*-
"""本地回测（纯 pandas，不依赖 akshare/backtrader）
用 data/<date>/stock_*_daily.csv 验证双均线+RSI 策略 alpha。
跑：python backtest_local.py  → 输出 backtest_result.json
"""
import pandas as pd
import numpy as np
import os
import glob
import json
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))


def find_stock_csvs():
    return glob.glob(os.path.join(BASE, 'data', '*', 'stock_*_daily.csv'))


def load_csv(path):
    df = pd.read_csv(path, encoding='utf-8-sig')
    df = df.rename(columns={'日期': 'date', '开盘': 'open', '收盘': 'close',
                            '最高': 'high', '最低': 'low', '涨跌幅': 'pct'})
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    return df


def calc_indicators(df, fast=10, slow=30, rsi_period=14):
    df['ma_fast'] = df['close'].rolling(fast).mean()
    df['ma_slow'] = df['close'].rolling(slow).mean()
    delta = df['close'].diff()
    gain = delta.clip(lower=0).rolling(rsi_period).mean()
    loss = -delta.clip(upper=0).rolling(rsi_period).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - 100 / (1 + rs)
    return df


def backtest(df, fast=10, slow=30, rsi_ob=70):
    """双均线交叉 + RSI过滤。返回交易记录 + 指标"""
    df = calc_indicators(df, fast, slow)
    pos = 0
    entry_price = 0
    trades = []
    for i, row in df.iterrows():
        if pd.isna(row['ma_slow']) or pd.isna(row['rsi']):
            continue
        if pos == 0 and row['ma_fast'] > row['ma_slow'] and row['rsi'] < rsi_ob:
            pos = 1
            entry_price = row['close']
            trades.append({'date': row['date'].strftime('%Y-%m-%d'), 'action': 'BUY', 'price': round(float(row['close']), 2)})
        elif pos == 1 and (row['ma_fast'] < row['ma_slow'] or row['rsi'] > rsi_ob):
            pnl = round((row['close'] / entry_price - 1) * 100, 2)
            trades.append({'date': row['date'].strftime('%Y-%m-%d'), 'action': 'SELL', 'price': round(float(row['close']), 2), 'pnl_pct': pnl})
            pos = 0
    if pos == 1:
        last = df.iloc[-1]
        pnl = round((last['close'] / entry_price - 1) * 100, 2)
        trades.append({'date': last['date'].strftime('%Y-%m-%d'), 'action': 'SELL', 'price': round(float(last['close']), 2), 'pnl_pct': pnl})
    sells = [t for t in trades if t['action'] == 'SELL']
    wins = [t for t in sells if t.get('pnl_pct', 0) > 0]
    total_pnl = sum(t.get('pnl_pct', 0) for t in sells)
    buy_hold = (df.iloc[-1]['close'] / df.iloc[0]['close'] - 1) * 100
    # 最大回撤（买入持有）
    cum = (1 + df['close'].pct_change()).cumprod()
    dd = (cum / cum.cummax() - 1).min() * 100
    return {
        'trades': trades,
        'trade_count': len(sells),
        'win_rate': round(len(wins) / len(sells) * 100, 1) if sells else 0,
        'total_pnl_pct': round(total_pnl, 2),
        'buy_hold_pct': round(buy_hold, 2),
        'alpha_vs_buyhold': round(total_pnl - buy_hold, 2),
        'max_drawdown_pct': round(dd, 2),
        'start': df.iloc[0]['date'].strftime('%Y-%m-%d'),
        'end': df.iloc[-1]['date'].strftime('%Y-%m-%d'),
        'bars': len(df),
    }


def main():
    csvs = find_stock_csvs()
    if not csvs:
        print('无 stock_*_daily.csv 数据'); return
    results = []
    for path in csvs:
        code = os.path.basename(path).replace('stock_', '').replace('_daily.csv', '')
        try:
            df = load_csv(path)
        except Exception as e:
            print(f'{code}: 读取失败 {e}'); continue
        if len(df) < 60:
            print(f'{code}: 数据不足({len(df)}行), 跳过'); continue
        r = backtest(df)
        r['code'] = code
        results.append(r)
        print(f"{code}: 交易{r['trade_count']}次 胜率{r['win_rate']}% 策略收益{r['total_pnl_pct']}% "
              f"买入持有{r['buy_hold_pct']}% alpha{r['alpha_vs_buyhold']:+}% 最大回撤{r['max_drawdown_pct']}%")
    out = {'results': results, 'timestamp': datetime.now().isoformat(),
           'strategy': '双均线(10/30)+RSI(14)过滤超买',
           'disclaimer': '回测基于历史数据，历史表现不代表未来收益，不构成投资建议。'}
    with open(os.path.join(BASE, 'backtest_result.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'\n结果存 backtest_result.json ({len(results)} 只标的)')


if __name__ == '__main__':
    main()
