# -*- coding: utf-8 -*-
"""多策略库 strategies.py —— MACD / 布林带 / 动量
复用 backtest_local 的 load_csv/find_stock_csvs，加3个策略回测。
跑：python strategies.py → strategies_result.json
"""
import backtest_local as bt
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime


def strategy_macd(df, fast=12, slow=26, signal=9):
    """MACD 金叉买入/死叉卖出"""
    df = df.copy()
    ema_f = df['close'].ewm(span=fast).mean()
    ema_s = df['close'].ewm(span=slow).mean()
    macd = ema_f - ema_s
    sig = macd.ewm(span=signal).mean()
    df['buy'] = (macd > sig) & (macd.shift(1) <= sig.shift(1))
    df['sell'] = (macd < sig) & (macd.shift(1) >= sig.shift(1))
    return _backtest_signals(df)


def strategy_boll(df, period=20, std=2):
    """布林带：跌破下轨买入/突破上轨卖出"""
    df = df.copy()
    ma = df['close'].rolling(period).mean()
    sd = df['close'].rolling(period).std()
    df['buy'] = df['close'] < (ma - std * sd)
    df['sell'] = df['close'] > (ma + std * sd)
    return _backtest_signals(df)


def strategy_momentum(df, period=20):
    """动量：N日涨幅>0持有"""
    df = df.copy()
    df['mom'] = df['close'].pct_change(period)
    df['buy'] = df['mom'] > 0
    df['sell'] = df['mom'] < 0
    return _backtest_signals(df)


def _backtest_signals(df):
    pos, entry, trades = 0, 0, []
    for _, row in df.iterrows():
        if pd.isna(row.get('buy')):
            continue
        if not pos and bool(row['buy']):
            pos, entry = 1, row['close']
            trades.append({'date': row['date'].strftime('%Y-%m-%d'), 'action': 'BUY', 'price': round(float(row['close']), 2)})
        elif pos and bool(row['sell']):
            pnl = round((row['close'] / entry - 1) * 100, 2)
            trades.append({'date': row['date'].strftime('%Y-%m-%d'), 'action': 'SELL', 'price': round(float(row['close']), 2), 'pnl_pct': pnl})
            pos = 0
    if pos:
        last = df.iloc[-1]
        trades.append({'date': last['date'].strftime('%Y-%m-%d'), 'action': 'SELL', 'price': round(float(last['close']), 2), 'pnl_pct': round((last['close'] / entry - 1) * 100, 2)})
    sells = [t for t in trades if t['action'] == 'SELL']
    wins = [t for t in sells if t.get('pnl_pct', 0) > 0]
    total = sum(t.get('pnl_pct', 0) for t in sells)
    buyhold = (df.iloc[-1]['close'] / df.iloc[0]['close'] - 1) * 100
    return {'trades': trades, 'trade_count': len(sells),
            'win_rate': round(len(wins) / len(sells) * 100, 1) if sells else 0,
            'total_pnl_pct': round(total, 2), 'buy_hold_pct': round(buyhold, 2),
            'alpha_vs_buyhold': round(total - buyhold, 2),
            'start': df.iloc[0]['date'].strftime('%Y-%m-%d'), 'end': df.iloc[-1]['date'].strftime('%Y-%m-%d'), 'bars': len(df)}


def main():
    csvs = bt.find_stock_csvs()
    if not csvs:
        print('无数据'); return
    all_r = []
    for path in csvs:
        code = os.path.basename(path).replace('stock_', '').replace('_daily.csv', '')
        try:
            df = bt.load_csv(path)
        except Exception as e:
            print(f'{code}: {e}'); continue
        if len(df) < 60:
            continue
        res = {'code': code}
        for name, fn in [('macd', strategy_macd), ('boll', strategy_boll), ('momentum', strategy_momentum)]:
            r = fn(df)
            res[name] = {'alpha': r['alpha_vs_buyhold'], 'pnl': r['total_pnl_pct'],
                         'win_rate': r['win_rate'], 'trades': r['trade_count']}
            print(f"{code} {name:8}: alpha={r['alpha_vs_buyhold']:+6.2f}% 收益{r['total_pnl_pct']:+6.2f}% 胜率{r['win_rate']:5}% 交易{r['trade_count']}")
        all_r.append(res)
    out = {'results': all_r, 'timestamp': datetime.now().isoformat(),
           'disclaimer': '多策略回测基于历史数据，不构成投资建议。不同策略适用不同市场环境。'}
    with open(os.path.join(bt.BASE, 'strategies_result.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'\n结果存 strategies_result.json ({len(all_r)} 只标的)')


if __name__ == '__main__':
    main()
