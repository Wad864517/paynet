# -*- coding: utf-8 -*-
"""风控回测 backtest_risk.py —— 双均线+RSI + 止损 + 仓位管理
对比有无止损的 alpha 差异，让回测更真实。
跑：python backtest_risk.py → backtest_risk_result.json
"""
import backtest_local as bt
import risk_manager as rm
import pandas as pd
import os
import json
from datetime import datetime


def backtest_with_risk(df, fast=10, slow=30, rsi_ob=70, stop_pct=0.05):
    """带止损的双均线+RSI 回测"""
    df = bt.calc_indicators(df, fast, slow)
    pos, entry, stop = 0, 0, 0
    trades = []
    for _, row in df.iterrows():
        if pd.isna(row['ma_slow']) or pd.isna(row['rsi']):
            continue
        # 持仓中：先查止损
        if pos and row['close'] < stop:
            trades.append({'date': row['date'].strftime('%Y-%m-%d'), 'action': 'STOP_LOSS',
                           'price': round(float(row['close']), 2),
                           'pnl_pct': round((row['close'] / entry - 1) * 100, 2)})
            pos = 0
            continue
        # 买入
        if not pos and row['ma_fast'] > row['ma_slow'] and row['rsi'] < rsi_ob:
            pos, entry = 1, row['close']
            stop = rm.stop_loss_price(entry, stop_pct, 'long')
            trades.append({'date': row['date'].strftime('%Y-%m-%d'), 'action': 'BUY',
                           'price': round(float(entry), 2), 'stop_price': stop})
        # 卖出（信号反转）
        elif pos and (row['ma_fast'] < row['ma_slow'] or row['rsi'] > rsi_ob):
            trades.append({'date': row['date'].strftime('%Y-%m-%d'), 'action': 'SELL',
                           'price': round(float(row['close']), 2),
                           'pnl_pct': round((row['close'] / entry - 1) * 100, 2)})
            pos = 0
    if pos:
        last = df.iloc[-1]
        trades.append({'date': last['date'].strftime('%Y-%m-%d'), 'action': 'SELL',
                       'price': round(float(last['close']), 2),
                       'pnl_pct': round((last['close'] / entry - 1) * 100, 2)})
    sells = [t for t in trades if t['action'] in ('SELL', 'STOP_LOSS')]
    wins = [t for t in sells if t.get('pnl_pct', 0) > 0]
    total = sum(t.get('pnl_pct', 0) for t in sells)
    stops = [t for t in trades if t['action'] == 'STOP_LOSS']
    buyhold = (df.iloc[-1]['close'] / df.iloc[0]['close'] - 1) * 100
    return {'trades': trades, 'trade_count': len(sells), 'stop_loss_count': len(stops),
            'win_rate': round(len(wins) / len(sells) * 100, 1) if sells else 0,
            'total_pnl_pct': round(total, 2), 'buy_hold_pct': round(buyhold, 2),
            'alpha_vs_buyhold': round(total - buyhold, 2),
            'stop_pct': stop_pct * 100,
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
        # 对比：无止损 vs 5%止损 vs 8%止损
        base = bt.backtest(df)  # 无止损（原版）
        r5 = backtest_with_risk(df, stop_pct=0.05)
        r8 = backtest_with_risk(df, stop_pct=0.08)
        all_r.append({'code': code, 'no_stop': base, 'stop5': r5, 'stop8': r8})
        print(f"{code}: 无止损 alpha{base['alpha_vs_buyhold']:+}% 胜率{base['win_rate']}% | "
              f"5%止损 alpha{r5['alpha_vs_buyhold']:+}% 胜率{r5['win_rate']}% 止损{r5['stop_loss_count']}次 | "
              f"8%止损 alpha{r8['alpha_vs_buyhold']:+}% 胜率{r8['win_rate']}% 止损{r8['stop_loss_count']}次")
    out = {'results': all_r, 'timestamp': datetime.now().isoformat(),
           'disclaimer': '风控回测基于历史数据，止损不一定提升收益，不构成投资建议。'}
    with open(os.path.join(bt.BASE, 'backtest_risk_result.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'\n结果存 backtest_risk_result.json ({len(all_r)} 只标的)')


if __name__ == '__main__':
    main()
