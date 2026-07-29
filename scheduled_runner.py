# -*- coding: utf-8 -*-
"""每日定时执行器 scheduled_runner.py
收盘后一键跑：选股研究 + 策略回测 + 参数优化 → 结果进 dashboard
配合 Windows 任务计划/cron 每天收盘后跑。

跑：python scheduled_runner.py
结果：screener_result.json / backtest_result.json / grid_search_result.json
"""
import subprocess
import sys
import os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = ['screener.py', 'backtest_local.py', 'grid_search.py']


def run(script):
    print(f'\n{"="*50}\n▶ {script}\n{"="*50}')
    try:
        r = subprocess.run([sys.executable, script], cwd=BASE,
                           capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=300)
        out = (r.stdout or '')[-600:]
        print(out)
        if r.returncode != 0 and r.stderr:
            print(f'⚠️ {script} 异常: {r.stderr[-300:]}')
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        print(f'⏰ {script} 超时(>300s)')
        return False
    except Exception as e:
        print(f'❌ {script} 错误: {e}')
        return False


if __name__ == '__main__':
    print(f'🚀 每日定时任务启动 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    results = {}
    for s in SCRIPTS:
        results[s] = run(s)
    print(f'\n{"="*50}\n✅ 完成 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    for s, ok in results.items():
        print(f'  {"✓" if ok else "✗"} {s}')
    print('\n结果文件：screener_result.json / backtest_result.json / grid_search_result.json')
    print('dashboard 打开即看最新结果。')
