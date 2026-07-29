# -*- coding: utf-8 -*-
"""iFinD 多股票 grid search —— 找全局最优参数（所有股票平均 alpha 最高）
跑：python ifind_grid_search.py → ifind_grid_result.json
"""
import ifind_backtest as ib
import backtest_local as bt
import json
import os
from datetime import datetime

PARAMS = [(f, s, r) for f in [5, 10, 15, 20] for s in [20, 30, 40, 60]
          for r in [70, 75, 80] if f < s]


def main():
    dfs = {}
    for code in ib.STOCKS:
        df = ib.fetch_history_df(code, 365)
        if df is not None and len(df) >= 60:
            dfs[code] = df
            print(f'{code}: {len(df)} 根K线')
    print(f'\n取到 {len(dfs)} 只股票历史\n')

    # 每只各自最优参数
    per_best = {}
    for code, df in dfs.items():
        best_p = max(PARAMS, key=lambda p: bt.backtest(df, p[0], p[1], p[2])['alpha_vs_buyhold'])
        r = bt.backtest(df, best_p[0], best_p[1], best_p[2])
        per_best[code] = {'params': list(best_p), 'alpha': r['alpha_vs_buyhold'],
                           'win_rate': r['win_rate'], 'trades': r['trade_count']}
        print(f"{code} 各自最优: fast={best_p[0]} slow={best_p[1]} rsi={best_p[2]} "
              f"alpha={r['alpha_vs_buyhold']:+.2f}% 胜率{r['win_rate']}%")

    # 全局最优：一组参数让所有股票平均 alpha 最高
    print(f'\n{"="*50}\n搜索全局最优参数（{len(PARAMS)} 组合 × {len(dfs)} 股票）...')
    global_best, global_best_avg = None, -999
    for p in PARAMS:
        alphas = [bt.backtest(df, p[0], p[1], p[2])['alpha_vs_buyhold'] for df in dfs.values()]
        avg = sum(alphas) / len(alphas)
        if avg > global_best_avg:
            global_best_avg = avg
            global_best = p
    print(f'全局最优: fast={global_best[0]} slow={global_best[1]} rsi={global_best[2]} '
          f'平均alpha={global_best_avg:+.2f}%')

    # 全局最优各股表现
    global_results = []
    for code, df in dfs.items():
        r = bt.backtest(df, global_best[0], global_best[1], global_best[2])
        global_results.append({'code': code, 'alpha': r['alpha_vs_buyhold'],
                               'win_rate': r['win_rate'], 'pnl': r['total_pnl_pct'],
                               'buy_hold': r['buy_hold_pct']})
        print(f"  {code}: alpha={r['alpha_vs_buyhold']:+6.2f}% 胜率{r['win_rate']:5}%")
    pos = sum(1 for r in global_results if r['alpha'] > 0)
    print(f'\n全局最优各股正alpha: {pos}/{len(global_results)}')

    out = {
        'per_stock_best': per_best,
        'global_best': {'params': list(global_best), 'avg_alpha': round(global_best_avg, 2)},
        'global_results': global_results,
        'positive_count': pos, 'total': len(global_results),
        'stocks_tested': len(dfs), 'param_combos': len(PARAMS),
        'timestamp': datetime.now().isoformat(),
        'disclaimer': 'grid search 多股票参数优化，存在严重过拟合风险，最优参数不保证未来有效，不构成投资建议。',
    }
    with open(os.path.join(bt.BASE, 'ifind_grid_result.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'\n结果存 ifind_grid_result.json')


if __name__ == '__main__':
    main()
