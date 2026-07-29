# -*- coding: utf-8 -*-
"""策略参数网格搜索（grid search）
对双均线+RSI 策略的 fast/slow/rsi_ob 参数做网格搜索，找 alpha 最优组合。
数据来了就能跑。跑：python grid_search.py → grid_search_result.json
"""
import backtest_local as bt
import os
import json
from datetime import datetime


def grid_search(df):
    results = []
    for fast in [5, 10, 15, 20]:
        for slow in [20, 30, 40, 60]:
            if fast >= slow:
                continue
            for rsi_ob in [70, 75, 80]:
                r = bt.backtest(df, fast, slow, rsi_ob)
                r['params'] = {'fast': fast, 'slow': slow, 'rsi_ob': rsi_ob}
                results.append(r)
    results.sort(key=lambda x: x.get('alpha_vs_buyhold', -999), reverse=True)
    return results[:5]  # top5


def main():
    csvs = bt.find_stock_csvs()
    if not csvs:
        print('无 stock_*_daily.csv 数据'); return
    all_results = []
    for path in csvs:
        code = os.path.basename(path).replace('stock_', '').replace('_daily.csv', '')
        try:
            df = bt.load_csv(path)
        except Exception as e:
            print(f'{code}: {e}'); continue
        if len(df) < 60:
            print(f'{code}: 数据不足({len(df)}),跳过'); continue
        top = grid_search(df)
        all_results.append({'code': code, 'top': top})
        b = top[0]
        print(f"{code} 最优: fast={b['params']['fast']} slow={b['params']['slow']} "
              f"rsi_ob={b['params']['rsi_ob']} | alpha={b['alpha_vs_buyhold']:+}% "
              f"胜率{b['win_rate']}% 回撤{b['max_drawdown_pct']}%")
    out = {'results': all_results, 'timestamp': datetime.now().isoformat(),
           'disclaimer': '参数优化基于历史数据，存在过拟合风险，不构成投资建议。最优参数不保证未来有效。'}
    with open(os.path.join(bt.BASE, 'grid_search_result.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'\n结果存 grid_search_result.json ({len(all_results)} 只标的)')


if __name__ == '__main__':
    main()
