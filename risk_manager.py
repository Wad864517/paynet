# -*- coding: utf-8 -*-
"""风控模块 risk_manager.py —— 仓位管理 + 止损 + 回撤限制
给信号+资金 → 输出仓位/止损价/风险评估。
可接入回测（加止损）和实盘（仓位控制）。
"""
import json
from datetime import datetime


def position_size(capital, entry_price, stop_price, risk_pct=0.02):
    """单笔风险仓位：风险资金=capital*risk_pct，股数=风险资金/单股风险，整手"""
    risk_amount = capital * risk_pct
    per_share_risk = abs(entry_price - stop_price)
    if per_share_risk == 0:
        return 0
    shares = int(risk_amount / per_share_risk / 100) * 100  # A股整手100股
    return max(shares, 0)


def stop_loss_price(entry, pct=0.05, direction='long'):
    """止损价：多头 entry*(1-pct)，空头 entry*(1+pct)"""
    if direction == 'long':
        return round(entry * (1 - pct), 2)
    return round(entry * (1 + pct), 2)


def check_drawdown(equity_curve, max_dd_limit=0.15):
    """检查回撤是否超限（默认15%）"""
    if not equity_curve:
        return {'drawdown': 0, 'exceeded': False}
    peak = max(equity_curve)
    cur = equity_curve[-1]
    dd = (cur / peak - 1) if peak > 0 else 0
    return {'drawdown_pct': round(dd * 100, 2), 'exceeded': dd < -max_dd_limit, 'limit_pct': max_dd_limit * 100}


def portfolio_allocation(capital, stocks_count, max_per_stock=0.15):
    """组合仓位分配：单票上限 max_per_stock，均分"""
    per_stock_cap = capital * max_per_stock
    if stocks_count == 0:
        return {'per_stock_capital': 0, 'max_stocks': 0}
    return {
        'per_stock_capital': round(per_stock_cap, 2),
        'max_stocks': min(stocks_count, int(1 / max_per_stock)),
        'max_per_stock_pct': max_per_stock * 100,
        'total_capital': capital,
    }


def assess(capital, entry, stop_pct=0.05, risk_pct=0.02, direction='long'):
    """单笔交易综合风险评估"""
    stop = stop_loss_price(entry, stop_pct, direction)
    shares = position_size(capital, entry, stop, risk_pct)
    pos_value = shares * entry
    return {
        'capital': capital, 'entry_price': entry, 'direction': direction,
        'stop_price': stop, 'stop_pct': stop_pct * 100,
        'shares': shares, 'position_value': round(pos_value, 2),
        'risk_amount': round(capital * risk_pct, 2), 'risk_pct': risk_pct * 100,
        'position_ratio_pct': round(pos_value / capital * 100, 2) if capital else 0,
        'max_loss': round(shares * abs(entry - stop), 2),
        'timestamp': datetime.now().isoformat(),
    }


if __name__ == '__main__':
    print('=== 风控评估示例 ===')
    print('场景：资金10万，买入价25元，止损5%，单笔风险2%')
    r = assess(100000, 25, 0.05, 0.02, 'long')
    print(json.dumps(r, ensure_ascii=False, indent=2))
    print('\n=== 组合分配（10万，5只股票，单票上限15%）===')
    p = portfolio_allocation(100000, 5, 0.15)
    print(json.dumps(p, ensure_ascii=False, indent=2))
    print('\n=== 回撤检查（净值曲线）===')
    eq = [100, 105, 108, 102, 98, 95]
    d = check_drawdown(eq, 0.10)
    print(json.dumps(d, ensure_ascii=False, indent=2))
