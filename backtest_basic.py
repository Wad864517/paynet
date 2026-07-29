"""
Day6 - Backtrader 基础回测：双均线交叉策略
运行方式：python backtest_basic.py
"""
import backtrader as bt
import akshare as ak
import pandas as pd
import numpy as np
import time
import random


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
                print(f"  重试 {attempt+1}/{max_retries}，等待 {delay:.1f}s...")
                time.sleep(delay)
            else:
                print(f"  ❌ 获取 {symbol} 失败: {e}")
                return None


class DoubleMA(bt.Strategy):
    """双均线交叉策略 + RSI过滤"""
    params = (
        ('fast_period', 10),
        ('slow_period', 30),
        ('rsi_period', 14),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
        ('printlog', True),
    )

    def __init__(self):
        self.sma_fast = bt.ind.SMA(period=self.p.fast_period)
        self.sma_slow = bt.ind.SMA(period=self.p.slow_period)
        self.crossover = bt.ind.CrossOver(self.sma_fast, self.sma_slow)
        self.rsi = bt.ind.RSI(period=self.p.rsi_period)
        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            if self.crossover > 0 and self.rsi[0] < self.p.rsi_overbought:
                self.order = self.buy()
                if self.p.printlog:
                    print(f'📈 买入 @ {self.data.close[0]:.2f} | RSI={self.rsi[0]:.1f}')
        else:
            if self.crossover < 0 and self.rsi[0] > self.p.rsi_oversold:
                self.order = self.sell()
                if self.p.printlog:
                    print(f'📉 卖出 @ {self.data.close[0]:.2f} | RSI={self.rsi[0]:.1f}')

    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None


def generate_mock_data(symbol='600519', start_date='20230101', end_date='20260101'):
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    base_price = 1800
    price_changes = np.random.normal(0, 20, len(dates))
    prices = base_price + np.cumsum(price_changes)
    
    df = pd.DataFrame({
        '日期': dates.strftime('%Y-%m-%d'),
        '开盘': prices * (1 + np.random.uniform(-0.01, 0.01, len(dates))),
        '最高': prices * (1 + np.random.uniform(0, 0.02, len(dates))),
        '最低': prices * (1 + np.random.uniform(-0.02, 0, len(dates))),
        '收盘': prices,
        '成交量': np.random.randint(1000000, 5000000, len(dates)),
    })
    return df


if __name__ == '__main__':
    print("📊 正在获取数据...")
    df = safe_fetch('600519', '20230101', '20260101')
    if df is None:
        print("⚠️ 网络不可用，使用模拟数据进行回测验证...")
        df = generate_mock_data()

    df = df[['日期', '开盘', '最高', '最低', '收盘', '成交量']]
    df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    df = df.sort_index()

    cerebro = bt.Cerebro()
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.addstrategy(DoubleMA)
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=90)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

    print(f'\n💰 初始资金: ¥{cerebro.broker.getvalue():,.2f}')
    results = cerebro.run()
    print(f'💰 最终资金: ¥{cerebro.broker.getvalue():,.2f}')

    strat = results[0]
    ret = strat.analyzers.returns.get_analysis()['rtot'] * 100
    sharpe_data = strat.analyzers.sharpe.get_analysis()
    sharpe = sharpe_data.get('sharperatio', 0) or 0
    dd = strat.analyzers.drawdown.get_analysis()
    print(f'\n📊 回测报告:')
    print(f'  总收益率: {ret:.1f}%')
    print(f'  夏普比率: {sharpe:.2f}' if sharpe else '  夏普比率: N/A')
    print(f'  最大回撤: {dd.max.drawdown:.2f}%')

    print('\n📈 正在生成图表...')
    cerebro.plot(style='candle', volume=False)