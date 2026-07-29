"""
Day12 - 每日量化工作流
一键运行所有分析模块，生成综合日报
"""
import subprocess
import json
import time
import sys
from datetime import datetime
import os


def run_module(name, script, args=None):
    """运行一个模块"""
    if args is None:
        args = []
    
    print(f"\n{'='*50}")
    print(f"🔄 运行模块: {name}")
    print(f"{'='*50}")
    
    try:
        cmd = [sys.executable, script] + args
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ {name} 完成")
            if result.stdout:
                print(result.stdout[-800:] if len(result.stdout) > 800 else result.stdout)
        else:
            print(f"❌ {name} 失败")
            if result.stderr:
                print(f"错误信息: {result.stderr[:500]}")
            if result.stdout:
                print(f"输出内容: {result.stdout[-500:] if len(result.stdout) > 500 else result.stdout}")
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except subprocess.TimeoutExpired:
        print(f"⏰ {name} 超时")
        return {'success': False, 'stdout': '', 'stderr': '模块运行超时'}
    except Exception as e:
        print(f"❌ {name} 异常: {e}")
        return {'success': False, 'stdout': '', 'stderr': str(e)}


def generate_daily_summary(results):
    """生成每日综合摘要"""
    summary = f"""
# 📊 量化交易日报
## {datetime.now().strftime('%Y-%m-%d %H:%M')}

### 模块运行状态
"""
    for name, info in results.items():
        status = "✅ 成功" if info['success'] else "❌ 失败"
        summary += f"- {name}: {status}\n"

    summary += """
### 各模块输出摘要
"""
    for name, info in results.items():
        summary += f"\n#### {name}\n"
        if info['success']:
            if info['stdout']:
                output = info['stdout'].strip()
                lines = output.split('\n')
                last_lines = lines[-10:] if len(lines) > 10 else lines
                summary += "```\n" + '\n'.join(last_lines) + "\n```\n"
            else:
                summary += "*无输出*\n"
        else:
            if info['stderr']:
                summary += f"**错误**: {info['stderr'][:300]}\n"

    summary += """
### 今日操作摘要
（在此手动记录你的操作和观察）

### 明日计划
（在此记录明天的关注重点）

---
⚠️ 以上分析仅供参考，不构成投资建议。
"""
    return summary


if __name__ == '__main__':
    print("🚀 每日量化工作流启动")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    results = {}

    # 模块1: 技术面分析（Week1 的 daily_scan）
    results['技术面扫描'] = run_module('技术面扫描', 'daily_scan.py')
    time.sleep(5)

    # 模块2: 资金追踪（Week1 的 money_tracker）
    results['资金追踪'] = run_module('资金追踪', 'money_tracker.py')
    time.sleep(5)

    # 模块3: 市场情绪
    results['市场情绪'] = run_module('市场情绪', 'sentiment_monitor.py')
    time.sleep(5)

    # 模块4: AI 选股
    results['AI选股'] = run_module('AI选股', 'ai_stock_screener.py')
    time.sleep(5)

    # 模块5: AI 财报分析（可选，耗时较长）
    # results['AI财报'] = run_module('AI财报', 'ai_fundamental.py')

    # 模块6: 模拟交易记录
    results['模拟持仓'] = run_module('模拟持仓', 'paper_trading.py', ['positions'])
    time.sleep(3)
    results['交易历史'] = run_module('交易历史', 'paper_trading.py', ['history'])
    time.sleep(3)

    # 生成日报
    summary = generate_daily_summary(results)
    filename = f'daily_report_{datetime.now().strftime("%Y%m%d")}.md'

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(summary)

    print(f"\n{'='*50}")
    print(f"📋 日报已生成: {filename}")
    print(f"{'='*50}")

    # 统计
    success_count = sum(1 for v in results.values() if v['success'])
    print(f"\n📊 模块完成: {success_count}/{len(results)}")