"""
模拟交易日志
记录每次模拟买卖，跟踪策略表现
"""
import json
import os
from datetime import datetime

TRADE_LOG = 'paper_trades.json'

def load_trades():
    if os.path.exists(TRADE_LOG):
        with open(TRADE_LOG, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_trades(trades):
    with open(TRADE_LOG, 'w', encoding='utf-8') as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)

def record_trade(action, code, name, price, shares, reason=""):
    """记录一笔交易"""
    trades = load_trades()
    trade = {
        'time': datetime.now().isoformat(),
        'action': action,
        'code': code,
        'name': name,
        'price': price,
        'shares': shares,
        'amount': price * shares,
        'reason': reason,
    }
    trades.append(trade)
    save_trades(trades)
    print(f"✅ 记录{('买入' if action=='BUY' else '卖出')}: "
          f"{code} {name} {shares}股 @ ¥{price:.2f}")
    return trade

def show_positions():
    """显示当前持仓"""
    trades = load_trades()
    positions = {}

    for t in trades:
        code = t['code']
        if code not in positions:
            positions[code] = {
                'name': t['name'],
                'shares': 0,
                'cost': 0,
            }
        if t['action'] == 'BUY':
            positions[code]['shares'] += t['shares']
            positions[code]['cost'] += t['amount']
        elif t['action'] == 'SELL':
            positions[code]['shares'] -= t['shares']
            positions[code]['cost'] -= t['amount']

    positions = {k: v for k, v in positions.items() if v['shares'] > 0}

    print(f"\n📋 当前模拟持仓 ({len(positions)} 只):")
    total_cost = 0
    for code, pos in positions.items():
        avg_cost = pos['cost'] / pos['shares'] if pos['shares'] > 0 else 0
        total_cost += pos['cost']
        print(f"  {code} {pos['name']}: {pos['shares']}股, "
              f"成本¥{avg_cost:.2f}, 总额¥{pos['cost']:.0f}")
    print(f"  总投入: ¥{total_cost:,.0f}")

    return positions

def show_trade_history(days=7):
    """显示最近交易记录"""
    trades = load_trades()
    print(f"\n📋 最近交易记录:")
    for t in trades[-20:]:
        action_emoji = "📈" if t['action'] == 'BUY' else "📉"
        print(f"  {action_emoji} {t['time'][:10]} {t['code']} {t['name']} "
              f"{t['shares']}股 @ ¥{t['price']:.2f} | {t['reason']}")

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  查看持仓: python paper_trading.py positions")
        print("  记录买入: python paper_trading.py buy 600519 贵州茅台 1800 100 'MACD金叉'")
        print("  记录卖出: python paper_trading.py sell 600519 贵州茅台 1850 100 '止损'")
        print("  交易历史: python paper_trading.py history")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'positions':
        show_positions()
    elif cmd == 'history':
        show_trade_history()
    elif cmd == 'buy' and len(sys.argv) >= 7:
        record_trade('BUY', sys.argv[2], sys.argv[3],
                     float(sys.argv[4]), int(sys.argv[5]),
                     sys.argv[6] if len(sys.argv) > 6 else '')
    elif cmd == 'sell' and len(sys.argv) >= 7:
        record_trade('SELL', sys.argv[2], sys.argv[3],
                     float(sys.argv[4]), int(sys.argv[5]),
                     sys.argv[6] if len(sys.argv) > 6 else '')
    else:
        print("参数错误，请检查用法")