"""
Day7 - 复合技术策略回测
综合 Week1 的 MACD + KDJ + RSI + 量比信号
运行方式：
  默认回测: python backtest_advanced.py
  参数优化: python backtest_advanced.py --optimize
  生成报告: python backtest_advanced.py --report
"""
import backtrader as bt
import akshare as ak
import pandas as pd
import numpy as np
import time
import random
import sys
import os
from datetime import datetime, timedelta
import logging

# ===== 日志配置 =====
log = logging.getLogger("backtest_advanced")
log.setLevel(logging.DEBUG)
log.handlers = []
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter('%(message)s'))
log.addHandler(ch)

# ===== 安全获取数据函数（带重试） =====
def safe_fetch(symbol, start_date, end_date, max_retries=3):
    for attempt in range(max_retries):
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol, period="daily",
                start_date=start_date, end_date=end_date, adjust="qfq"
            )
            if not df.empty:
                return df
            raise ValueError("数据为空")
        except Exception as e:
            if attempt < max_retries - 1:
                delay = random.uniform(3, 6)
                log.warning(f"  重试 {attempt+1}/{max_retries}，等待 {delay:.1f}s...")
                time.sleep(delay)
            else:
                log.error(f"  ❌ 获取 {symbol} 失败: {e}")
                return None

# ===== 生成模拟数据 =====
def generate_sample_data(symbol, start_date, end_date):
    log.warning(f"  ⚠️ 使用模拟数据（{symbol}）进行回测...")
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    dates = pd.date_range(start, end, freq='B')

    np.random.seed(42)
    n = len(dates)
    base_price = 1500.0
    returns = np.random.normal(0.0003, 0.015, n)
    close = base_price * np.cumprod(1 + returns)

    df = pd.DataFrame({
        '日期': dates.strftime('%Y-%m-%d'),
        '开盘': close * (1 + np.random.uniform(-0.005, 0.005, n)),
        '最高': close * (1 + np.random.uniform(0, 0.02, n)),
        '最低': close * (1 - np.random.uniform(0, 0.02, n)),
        '收盘': close,
        '成交量': np.random.randint(50000, 200000, n),
    })
    return df

# ===== 综合技术面策略 =====
class CompositeStrategy(bt.Strategy):
    """综合技术面策略：MACD + KDJ + RSI + 量比"""
    params = (
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        ('kdj_period', 9),
        ('rsi_period', 14),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
        ('vol_ratio_threshold', 2.0),
        ('stop_loss_pct', 0.05),
        ('min_buy_score', 2),
        ('printlog', True),
    )

    def __init__(self):
        # MACD
        self.macd = bt.ind.MACD(
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal
        )
        self.macd_cross = bt.ind.CrossOver(self.macd.macd, self.macd.signal)

        # KDJ（用 Stochastic 近似）
        self.stoch = bt.ind.Stochastic(
            period=self.p.kdj_period,
            period_dfast=3, period_dslow=3
        )

        # RSI
        self.rsi = bt.ind.RSI(period=self.p.rsi_period)

        # 量比（当日成交量 / 5日均量）
        self.sma_vol = bt.ind.SMA(self.data.volume, period=5)
        self.vol_ratio = self.data.volume / self.sma_vol

        self.order = None
        self.trade_log = []
        self.equity_curve = []
        self.entry_price = 0
        self.trade_count = 0

    def log(self, txt, dt=None):
        dt = dt or self.data.datetime.date(0)
        print(f'[{dt}] {txt}')

    def next(self):
        if self.order:
            return

        price = self.data.close[0]
        date = self.data.datetime.date(0)
        equity = self.broker.getvalue()
        self.equity_curve.append({'date': date, 'equity': equity})

        # ===== 止损检查 =====
        if self.position and self.entry_price > 0:
            loss_pct = (self.entry_price - price) / self.entry_price
            if loss_pct >= self.p.stop_loss_pct:
                size = self.position.size
                self.log(f'🛑 止损触发 | 成本=¥{self.entry_price:.2f} | 当前=¥{price:.2f} | 亏损={loss_pct*100:.2f}%')
                self.order = self.sell()
                return

        # ===== 买入条件 =====
        macd_gold = self.macd_cross > 0
        kdj_low = self.stoch.percK[0] < 30
        rsi_oversold = self.rsi[0] < self.p.rsi_oversold
        vol_active = self.vol_ratio[0] > self.p.vol_ratio_threshold

        buy_score = sum([macd_gold, kdj_low or rsi_oversold, vol_active])

        if not self.position and buy_score >= self.p.min_buy_score:
            size = self.broker.getcash() / price * 0.9
            self.log(f'📈 买入信号 | 评分={buy_score}/{self.p.min_buy_score}')
            self.log(f'   ├─ MACD金叉: {"✅" if macd_gold else "❌"}')
            self.log(f'   ├─ KDJ低位/K值={self.stoch.percK[0]:.1f}: {"✅" if kdj_low else "❌"}')
            self.log(f'   ├─ RSI超卖/RSI={self.rsi[0]:.1f}: {"✅" if rsi_oversold else "❌"}')
            self.log(f'   ├─ 放量/量比={self.vol_ratio[0]:.1f}: {"✅" if vol_active else "❌"}')
            self.log(f'   └─ 价格=¥{price:.2f} | 预估买入={size:.0f}股')
            self.order = self.buy()
            self.trade_log.append({
                'date': date.isoformat(),
                'action': 'BUY',
                'price': price,
                'score': buy_score,
                'macd_gold': macd_gold,
                'kdj_low': kdj_low,
                'rsi_oversold': rsi_oversold,
                'vol_active': vol_active,
            })

        # ===== 卖出条件 =====
        macd_dead = self.macd_cross < 0
        rsi_overbought = self.rsi[0] > self.p.rsi_overbought
        kdj_high = self.stoch.percK[0] > 80

        if self.position:
            cost = self.entry_price
            current = price
            profit_pct = (current - cost) / cost * 100

            sell_conditions = []
            if profit_pct < -5:
                sell_conditions.append(f"止损(-{profit_pct:.1f}%)")
            if macd_dead:
                sell_conditions.append("MACD死叉")
            if rsi_overbought:
                sell_conditions.append(f"RSI超买({self.rsi[0]:.1f})")
            if kdj_high:
                sell_conditions.append(f"KDJ超买(K={self.stoch.percK[0]:.1f})")

            if sell_conditions:
                self.log(f'📉 卖出信号 | 持仓成本=¥{cost:.2f} | 当前=¥{current:.2f} | 盈亏={profit_pct:+.2f}%')
                self.log(f'   ├─ 卖出原因: {", ".join(sell_conditions)}')
                self.log(f'   ├─ MACD死叉: {"✅" if macd_dead else "❌"}')
                self.log(f'   ├─ RSI超买/RSI={self.rsi[0]:.1f}: {"✅" if rsi_overbought else "❌"}')
                self.log(f'   └─ KDJ超买/K值={self.stoch.percK[0]:.1f}: {"✅" if kdj_high else "❌"}')
                self.order = self.sell()
                self.trade_log.append({
                    'date': date.isoformat(),
                    'action': 'SELL',
                    'price': current,
                    'pnl_pct': profit_pct,
                    'macd_dead': macd_dead,
                    'rsi_overbought': rsi_overbought,
                    'kdj_high': kdj_high,
                })

    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.trade_count += 1
            date = self.data.datetime.date(0)
            if order.isbuy():
                self.entry_price = order.executed.price
                stop_price = order.executed.price * (1 - self.p.stop_loss_pct)
                self.log(f'   ✅ 买入成交 #{self.trade_count} | 价格=¥{order.executed.price:.2f} | 数量={order.executed.size:.0f}股 | 止损价=¥{stop_price:.2f}')
            else:
                self.entry_price = 0
                self.log(f'   ✅ 卖出成交 #{self.trade_count} | 价格=¥{order.executed.price:.2f} | 数量={order.executed.size:.0f}股')
            self.order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            pnl = trade.pnlcomm
            pnl_pct = pnl / trade.price / abs(trade.size) * 100 if trade.size != 0 else 0
            self.log(f'   💰 交易完成 | 净利润=¥{pnl:.2f} ({pnl_pct:+.2f}%) | 持仓天数={trade.barlen}天')

# ===== 参数优化 =====
def run_optimization():
    log.info("🔧 开始参数优化...")

    df = safe_fetch('600519', '20230101', '20260101')
    if df is None:
        log.warning("⚠️ 使用模拟数据进行参数优化...")
        df = generate_sample_data('600519', '20230101', '20260101')

    df = df[['日期', '开盘', '最高', '最低', '收盘', '成交量']]
    df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)

    cerebro = bt.Cerebro()
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)

    cerebro.optstrategy(
        CompositeStrategy,
        macd_fast=[10, 12, 15],
        macd_slow=[20, 26, 30],
        rsi_oversold=[25, 30, 35],
    )

    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=90)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

    results = cerebro.run()

    log.info(f"\n{'='*60}")
    log.info(f"{'快线':>6} {'慢线':>6} {'RSI超卖':>8} {'收益率':>10} {'夏普':>8}")
    log.info(f"{'='*60}")

    best_return = -999
    best_params = None

    for run in results:
        strat = run[0]
        params = strat.params
        ret = strat.analyzers.returns.get_analysis()
        sharpe_data = strat.analyzers.sharpe.get_analysis()

        rnorm = ret.get('rtot', 0) * 100
        sharpe = sharpe_data.get('sharperatio', 0) or 0

        log.info(f"{params.macd_fast:>6} {params.macd_slow:>6} "
              f"{params.rsi_oversold:>8} {rnorm:>9.1f}% {sharpe:>8.2f}")

        if rnorm > best_return:
            best_return = rnorm
            best_params = params

    if best_params:
        log.info(f"\n🏆 最优参数: 快线={best_params.macd_fast}, "
              f"慢线={best_params.macd_slow}, RSI超卖={best_params.rsi_oversold}")
        log.info(f"   总收益率: {best_return:.1f}%")

# ===== 生成HTML报告 =====
def generate_full_report(strat, df, params, initial_cash=100000.0):
    reports_dir = os.path.join(os.path.dirname(__file__), 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = os.path.join(reports_dir, f"backtest_report_{timestamp}.html")

    sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', None)
    dd = strat.analyzers.drawdown.get_analysis()
    ret = strat.analyzers.returns.get_analysis()['rtot'] * 100

    final_cash = strat.broker.getvalue()
    total_return = (final_cash - initial_cash) / initial_cash * 100
    total_comm = sum(t.get('commission', 0) for t in strat.trade_log)

    equity_df = pd.DataFrame(strat.equity_curve)
    equity_df['date'] = pd.to_datetime(equity_df['date'])
    equity_df.set_index('date', inplace=True)

    trades_df = pd.DataFrame(strat.trade_log)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>综合技术策略回测报告（最优参数）</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; background: #f5f7fa; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ text-align: center; color: #2c3e50; margin-bottom: 30px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
        .stat-card h3 {{ color: #7f8c8d; font-size: 14px; margin-bottom: 10px; }}
        .stat-card p {{ font-size: 28px; font-weight: bold; }}
        .stat-card.profit p {{ color: #27ae60; }}
        .stat-card.loss p {{ color: #e74c3c; }}
        .stat-card.warning p {{ color: #f39c12; }}
        .chart-container {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 30px; }}
        .chart-container h2 {{ color: #2c3e50; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        th, td {{ padding: 14px; text-align: left; border-bottom: 1px solid #ecf0f1; }}
        th {{ background: #3498db; color: white; font-weight: bold; }}
        tr:hover {{ background: #f8f9fa; }}
        .buy {{ color: #27ae60; font-weight: bold; }}
        .sell {{ color: #e74c3c; font-weight: bold; }}
        .summary {{ margin-top: 20px; padding: 25px; background: #ecf0f1; border-radius: 10px; }}
        .summary h2 {{ color: #2c3e50; margin-bottom: 20px; }}
        .params-table {{ margin-top: 15px; }}
        .params-table td {{ padding: 8px 15px; }}
        .params-table tr:nth-child(even) {{ background: #e8ecef; }}
        .timestamp {{ text-align: center; color: #95a5a6; font-size: 12px; margin-top: 20px; }}
        .highlight {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <h1>📊 综合技术策略回测报告（MACD+KDJ+RSI+量比）</h1>
        <p class="timestamp">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 股票: 600519 贵州茅台 | 数据周期: 2023-2026</p>

        <div class="highlight">
            <strong>🏆 最优参数组合:</strong> MACD快线={params['macd_fast']}, MACD慢线={params['macd_slow']}, RSI超卖={params['rsi_oversold']}
        </div>

        <div class="stats-grid">
            <div class="stat-card {'profit' if total_return > 0 else 'loss'}">
                <h3>总收益率</h3>
                <p>{total_return:+.2f}%</p>
            </div>
            <div class="stat-card">
                <h3>最终资金</h3>
                <p>¥{final_cash:,.2f}</p>
            </div>
            <div class="stat-card">
                <h3>交易次数</h3>
                <p>{len(strat.trade_log)}笔</p>
            </div>
            <div class="stat-card">
                <h3>总佣金</h3>
                <p>¥{total_comm:.2f}</p>
            </div>
            <div class="stat-card {'profit' if sharpe and sharpe > 0 else 'warning'}">
                <h3>夏普比率</h3>
                <p>{sharpe:.2f}</p>
            </div>
            <div class="stat-card {'profit' if dd.max.drawdown < 10 else 'warning'}">
                <h3>最大回撤</h3>
                <p>{dd.max.drawdown:.2f}%</p>
            </div>
            <div class="stat-card">
                <h3>初始资金</h3>
                <p>¥{initial_cash:,.2f}</p>
            </div>
            <div class="stat-card">
                <h3>策略评分</h3>
                <p>{params.get('min_buy_score', 2)}分</p>
            </div>
        </div>

        <div class="chart-container">
            <h2>💰 资金曲线图</h2>
            <canvas id="equityChart" width="100%" height="350"></canvas>
        </div>

        <div class="chart-container">
            <h2>📈 每日收益变化</h2>
            <canvas id="returnChart" width="100%" height="250"></canvas>
        </div>

        <div>
            <h2>📋 交易明细</h2>
            <table>
                <tr>
                    <th>序号</th><th>日期</th><th>操作</th><th>价格</th><th>数量</th><th>评分/盈亏</th>
                    <th>MACD</th><th>KDJ</th><th>RSI</th><th>量比</th>
                </tr>
"""

    for i, t in enumerate(strat.trade_log, 1):
        macd = "金叉" if t.get('macd_gold') else ("死叉" if t.get('macd_dead') else "-")
        kdj_val = f"K={t.get('kdj_low', '')}{t.get('kdj_high', '')}" if any(k in t for k in ['kdj_low', 'kdj_high']) else "-"
        rsi_val = f"{t.get('rsi_oversold', '')}{t.get('rsi_overbought', '')}" if any(k in t for k in ['rsi_oversold', 'rsi_overbought']) else "-"
        vol_val = "✅" if t.get('vol_active') else "-"
        score_or_pnl = f"评分={t.get('score', '')}" if t.get('score') else f"{t.get('pnl_pct', '')}%"

        html_content += f"""                <tr>
                    <td>{i}</td>
                    <td>{t['date']}</td>
                    <td class="{t['action'].lower()}">{t['action']}</td>
                    <td>¥{t['price']:.2f}</td>
                    <td>{t.get('size', '')}</td>
                    <td>{score_or_pnl}</td>
                    <td>{macd}</td>
                    <td>{kdj_val}</td>
                    <td>{rsi_val}</td>
                    <td>{vol_val}</td>
                </tr>
"""

    html_content += f"""            </table>
        </div>

        <div class="summary">
            <h2>📝 策略参数配置</h2>
            <table class="params-table">
                <tr><td><strong>MACD参数:</strong></td><td>快线={params['macd_fast']}, 慢线={params['macd_slow']}, 信号=9</td></tr>
                <tr><td><strong>KDJ参数:</strong></td><td>周期=9, D=3, K=3</td></tr>
                <tr><td><strong>RSI参数:</strong></td><td>周期=14, 超卖线={params['rsi_oversold']}, 超买线=70</td></tr>
                <tr><td><strong>量比阈值:</strong></td><td>2.0</td></tr>
                <tr><td><strong>止损比例:</strong></td><td>5%</td></tr>
                <tr><td><strong>最低买入评分:</strong></td><td>2分</td></tr>
                <tr><td><strong>初始资金:</strong></td><td>¥{initial_cash:,.2f}</td></tr>
                <tr><td><strong>持仓比例:</strong></td><td>90%</td></tr>
                <tr><td><strong>佣金费率:</strong></td><td>0.1%</td></tr>
            </table>
        </div>
    </div>

    <script>
        var ctx1 = document.getElementById('equityChart').getContext('2d');
        new Chart(ctx1, {{
            type: 'line',
            data: {{
                labels: {equity_df.index.strftime('%Y-%m-%d').tolist()},
                datasets: [{{
                    label: '账户净值',
                    data: {equity_df['equity'].tolist()},
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                interaction: {{ intersect: false, mode: 'index' }},
                scales: {{
                    y: {{
                        beginAtZero: false,
                        ticks: {{ callback: v => '¥' + v.toLocaleString() }}
                    }}
                }},
                plugins: {{
                    legend: {{ display: true, position: 'top' }}
                }}
            }}
        }});

        var returns = {equity_df['equity'].pct_change().fillna(0).tolist()};
        var colors = returns.map(v => v >= 0 ? '#27ae60' : '#e74c3c');
        var ctx2 = document.getElementById('returnChart').getContext('2d');
        new Chart(ctx2, {{
            type: 'bar',
            data: {{
                labels: {equity_df.index.strftime('%Y-%m-%d').tolist()},
                datasets: [{{
                    label: '每日收益率',
                    data: returns,
                    backgroundColor: colors,
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        ticks: {{ callback: v => (v * 100).toFixed(1) + '%' }}
                    }}
                }},
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f'\n📄 完整回测报告已生成: {report_file}')
    return report_file

def generate_report(strat, df, initial_cash=100000.0):
    from data_manager import get_date_folder

    report_dir = get_date_folder()
    report_file = os.path.join(report_dir, f"advanced_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")

    sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', None)
    dd = strat.analyzers.drawdown.get_analysis()

    final_cash = strat.broker.getvalue()
    total_return = (final_cash - initial_cash) / initial_cash * 100

    equity_df = pd.DataFrame(strat.equity_curve)
    equity_df['date'] = pd.to_datetime(equity_df['date'])
    equity_df.set_index('date', inplace=True)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>复合技术策略回测报告</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; background: #f5f7fa; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ text-align: center; color: #2c3e50; margin-bottom: 30px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
        .stat-card h3 {{ color: #7f8c8d; font-size: 14px; margin-bottom: 10px; }}
        .stat-card p {{ font-size: 24px; font-weight: bold; }}
        .stat-card.profit p {{ color: #27ae60; }}
        .stat-card.loss p {{ color: #e74c3c; }}
        .chart-container {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 30px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ecf0f1; }}
        th {{ background: #3498db; color: white; }}
        .buy {{ color: #27ae60; font-weight: bold; }}
        .sell {{ color: #e74c3c; font-weight: bold; }}
        .summary {{ margin-top: 20px; padding: 20px; background: #ecf0f1; border-radius: 10px; }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <h1>📊 复合技术策略回测报告（MACD+KDJ+RSI+量比）</h1>

        <div class="stats-grid">
            <div class="stat-card {'profit' if total_return > 0 else 'loss'}">
                <h3>总收益率</h3>
                <p>{total_return:+.2f}%</p>
            </div>
            <div class="stat-card">
                <h3>最终资金</h3>
                <p>¥{final_cash:,.2f}</p>
            </div>
            <div class="stat-card">
                <h3>交易次数</h3>
                <p>{strat.trade_count}笔</p>
            </div>
            <div class="stat-card">
                <h3>夏普比率</h3>
                <p>{sharpe:.2f}</p>
            </div>
            <div class="stat-card">
                <h3>最大回撤</h3>
                <p>{dd.max.drawdown:.2f}%</p>
            </div>
            <div class="stat-card">
                <h3>信号评分阈值</h3>
                <p>{strat.p.min_buy_score}分</p>
            </div>
        </div>

        <div class="chart-container">
            <h2>💰 资金曲线图</h2>
            <canvas id="equityChart" width="100%" height="300"></canvas>
        </div>

        <div>
            <h2>📋 交易记录</h2>
            <table>
                <tr><th>日期</th><th>操作</th><th>价格</th><th>评分/盈亏</th><th>MACD</th><th>KDJ</th><th>RSI</th><th>量比</th></tr>
"""

    for t in strat.trade_log:
        macd = "金叉" if t.get('macd_gold') else ("死叉" if t.get('macd_dead') else "-")
        kdj = f"K={strat.stoch.percK[0]:.0f}" if 'kdj_low' in t or 'kdj_high' in t else "-"
        rsi = f"{strat.rsi[0]:.0f}" if 'rsi_oversold' in t or 'rsi_overbought' in t else "-"
        vol = f"{strat.vol_ratio[0]:.1f}" if t.get('vol_active') else "-"

        html_content += f"""                <tr>
                    <td>{t['date']}</td>
                    <td class="{t['action'].lower()}">{t['action']}</td>
                    <td>¥{t['price']:.2f}</td>
                    <td>{t.get('score', '')}{t.get('pnl_pct', '')}%</td>
                    <td>{macd}</td>
                    <td>{kdj}</td>
                    <td>{rsi}</td>
                    <td>{vol}</td>
                </tr>
"""

    html_content += f"""            </table>
        </div>

        <div class="summary">
            <h2>📝 策略参数</h2>
            <p><strong>MACD参数:</strong> 快线={strat.p.macd_fast}, 慢线={strat.p.macd_slow}, 信号={strat.p.macd_signal}</p>
            <p><strong>KDJ参数:</strong> 周期={strat.p.kdj_period}</p>
            <p><strong>RSI参数:</strong> 周期={strat.p.rsi_period}, 超卖线={strat.p.rsi_oversold}, 超买线={strat.p.rsi_overbought}</p>
            <p><strong>量比阈值:</strong> {strat.p.vol_ratio_threshold}</p>
            <p><strong>止损比例:</strong> {strat.p.stop_loss_pct*100}%</p>
            <p><strong>最低买入评分:</strong> {strat.p.min_buy_score}</p>
        </div>
    </div>

    <script>
        var ctx = document.getElementById('equityChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {equity_df.index.strftime('%Y-%m-%d').tolist()},
                datasets: [{{
                    label: '账户净值',
                    data: {equity_df['equity'].tolist()},
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{ ticks: {{ callback: v => '¥' + v.toLocaleString() }} }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    log.info(f'\n📄 报告已生成: {report_file}')
    return report_file

# ===== 主程序 =====
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--optimize':
        run_optimization()
    else:
        log.info("运行方式:")
        log.info("  默认回测: python backtest_advanced.py")
        log.info("  参数优化: python backtest_advanced.py --optimize")
        log.info("  生成报告: python backtest_advanced.py --report")

        log.info(f"\n🕐 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log.info("📊 策略: MACD + KDJ + RSI + 量比 综合策略")

        log.info("\n📥 正在获取数据...")
        df = safe_fetch('600519', '20230101', '20260101')
        if df is None:
            log.warning("⚠️ 网络不可用，使用模拟数据进行回测验证...")
            df = generate_sample_data('600519', '20230101', '20260101')

        df = df[['日期', '开盘', '最高', '最低', '收盘', '成交量']]
        df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        cerebro = bt.Cerebro()
        cerebro.adddata(bt.feeds.PandasData(dataname=df))

        best_params = {
            'macd_fast': 15,
            'macd_slow': 30,
            'rsi_oversold': 35,
        }
        print(f'🏆 使用最优参数: MACD快线={best_params["macd_fast"]}, MACD慢线={best_params["macd_slow"]}, RSI超卖={best_params["rsi_oversold"]}')
        cerebro.addstrategy(CompositeStrategy, **best_params)

        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=0.001)
        cerebro.addsizer(bt.sizers.PercentSizer, percents=90)
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

        print(f'初始资金: ¥{cerebro.broker.getvalue():,.2f}')
        results = cerebro.run()
        print(f'最终资金: ¥{cerebro.broker.getvalue():,.2f}')

        strat = results[0]
        ret = strat.analyzers.returns.get_analysis()['rtot'] * 100
        sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
        dd = strat.analyzers.drawdown.get_analysis()
        print(f'\n📊 回测报告:')
        print(f'  总收益率: {ret:.1f}%')
        print(f'  夏普比率: {sharpe:.2f}' if sharpe else '  夏普比率: N/A')
        print(f'  最大回撤: {dd.max.drawdown:.2f}%')

        generate_full_report(strat, df, best_params)
