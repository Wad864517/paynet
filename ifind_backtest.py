# -*- coding: utf-8 -*-
"""iFinD 多股票历史回测 —— 验证 alpha 稳定性
取10只蓝筹近1年K线，跑双均线+RSI策略，统计平均alpha。
跑：python ifind_backtest.py → ifind_backtest_result.json
"""
import ifind_data as idd
import backtest_local as bt
import pandas as pd
import os
import json
from datetime import datetime

STOCKS = ['600519', '601318', '300750', '600036', '002594',
          '000858', '600030', '000333', '601166', '002415']


def fetch_history_df(code, days=365):
    """iFinD 取历史日K，转 backtest_local 兼容 df"""
    end = datetime.now().strftime('%Y-%m-%d')
    start = (datetime.now() - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    h, err = idd.get_history(code, start, end)
    if err or not h.get('tables'):
        return None
    t = h['tables'][0]
    times = t.get('time', [])
    table = t.get('table', {})
    if not times:
        return None
    df = pd.DataFrame({
        'date': pd.to_datetime(times),
        'open': [float(x) for x in table.get('open', [])],
        'close': [float(x) for x in table.get('close', [])],
        'high': [float(x) for x in table.get('high', [])],
        'low': [float(x) for x in table.get('low', [])],
        'pct': [float(x) for x in table.get('changeRatio', [])],
    })
    return df.sort_values('date').reset_index(drop=True)


def main():
    results = []
    for code in STOCKS:
        df = fetch_history_df(code, 365)
        if df is None or len(df) < 60:
            print(f'{code}: 数据不足')
            continue
        r = bt.backtest(df)
        r['code'] = code
        results.append(r)
        print(f"{code}: alpha={r['alpha_vs_buyhold']:+6.2f}% 胜率{r['win_rate']:5}% "
              f"策略{r['total_pnl_pct']:+6.2f}% 买入持有{r['buy_hold_pct']:+6.2f}% 交易{r['trade_count']}")
    if not results:
        print('无可用数据'); return
    alphas = [r['alpha_vs_buyhold'] for r in results]
    print(f'\n{"="*50}')
    print(f'=== {len(results)} 只股票统计（近1年）===')
    print(f'平均 alpha: {sum(alphas)/len(alphas):+.2f}%')
    print(f'正 alpha: {sum(1 for a in alphas if a > 0)}/{len(alphas)}')
    print(f'最大 alpha: {max(alphas):+.2f}%  最小 alpha: {min(alphas):+.2f}%')
    out = {'results': results, 'avg_alpha': round(sum(alphas) / len(alphas), 2),
           'positive_count': sum(1 for a in alphas if a > 0), 'total': len(results),
           'max_alpha': round(max(alphas), 2), 'min_alpha': round(min(alphas), 2),
           'period': '近1年', 'timestamp': datetime.now().isoformat(),
           'disclaimer': '多股票回测基于iFinD历史数据，历史表现不代表未来，不构成投资建议。'}
    with open(os.path.join(bt.BASE, 'ifind_backtest_result.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'\n结果存 ifind_backtest_result.json')


if __name__ == '__main__':
    main()
