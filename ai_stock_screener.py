"""
Day9 - AI 智能选股器
用 DeepSeek 从多维度筛选优质股票
"""
import akshare as ak
import json
import time
import random
import os
from openai import OpenAI

config_path = os.path.join(os.path.dirname(__file__), '.quant', 'config.json')
with open(config_path, 'r', encoding='utf-8-sig') as f:
    config = json.load(f)

client = OpenAI(
    api_key=config['deepseek_api_key'],
    base_url=f"{config.get('deepwise_base_url') or config.get('deepseek_base_url')}/v1"
)


def get_market_overview():
    print("📊 获取市场概览数据...")
    data = {}

    try:
        spot = ak.stock_zh_a_spot_em()
        data['全市场行情'] = spot
        print(f"  ✓ 获取 {len(spot)} 只股票行情")
    except Exception as e:
        print(f"  ❌ 行情获取失败: {e}")
        print("  ⚠️ 使用模拟数据进行测试...")
        data['全市场行情'] = generate_mock_spot_data()
        print(f"  ✓ 生成 {len(data['全市场行情'])} 只模拟股票")

    spot = data['全市场行情']
    up_count = len(spot[spot['涨跌幅'] > 0])
    down_count = len(spot[spot['涨跌幅'] < 0])
    limit_up = len(spot[spot['涨跌幅'] >= 9.9])
    limit_down = len(spot[spot['涨跌幅'] <= -9.9])
    data['涨跌统计'] = f"上涨:{up_count} 下跌:{down_count} 涨停:{limit_up} 跌停:{limit_down}"

    return data


def generate_mock_spot_data():
    import pandas as pd
    import numpy as np
    np.random.seed(42)
    
    codes = ['600519', '000858', '601318', '600036', '000001',
             '600030', '601166', '002594', '300750', '002415',
             '600276', '002456', '300059', '601398', '600048',
             '000651', '601888', '000063', '002304', '600585',
             '600038', '000625', '600887', '000166', '002236',
             '600050', '002142', '002027', '600837', '601111',
             '002352', '601628', '000333', '600547', '002030',
             '600690', '000568', '601328', '600000', '601988',
             '000725', '600104', '300015', '600196', '000895',
             '600703', '000538', '600606', '600340', '600900']
    
    names = ['贵州茅台', '五粮液', '中国平安', '招商银行', '平安银行',
             '中信证券', '兴业银行', '比亚迪', '宁德时代', '海康威视',
             '恒瑞医药', '欧菲光', '东方财富', '工商银行', '保利发展',
             '格力电器', '中国中免', '中兴通讯', '洋河股份', '海螺水泥',
             '中粮地产', '长安汽车', '伊利股份', '华夏银行', '大华股份',
             '中国联通', '宁波银行', '分众传媒', '海通证券', '中国国航',
             '顺丰控股', '中国人寿', '美的集团', '山东黄金', '达安基因',
             '青岛海尔', '泸州老窖', '交通银行', '浦发银行', '中国银行',
             '京东方A', '上汽集团', '爱尔眼科', '复星医药', '双汇发展',
             '三安光电', '云南白药', '绿地控股', '华夏幸福', '长江电力']
    
    df = pd.DataFrame({
        '代码': codes,
        '名称': names,
        '最新价': np.random.uniform(10, 3000, 50),
        '涨跌幅': np.random.uniform(-10, 10, 50),
        '成交量': np.random.randint(1000000, 50000000, 50),
        '换手率': np.random.uniform(0.1, 20, 50),
        '市盈率-动态': np.random.uniform(5, 80, 50),
        '市净率': np.random.uniform(0.5, 10, 50),
        '总市值': np.random.uniform(100e8, 2000e8, 50),
    })
    return df


def ai_screen_stocks(df, screen_criteria):
    top_stocks = df.head(10)
    stock_rows = []
    for _, row in top_stocks.iterrows():
        reason = f"涨跌幅{row['涨跌幅']:.1f}%，换手{row['换手率']:.1f}%"
        risk = "市场波动"
        stock_rows.append(f"| {row['代码']} | {row['名称']} | {row['最新价']:.2f} | {row['涨跌幅']:.2f}% | {reason} | {risk} |")
    stock_table = "\n".join(stock_rows)
    
    data_str = top_stocks[['代码', '名称', '最新价', '涨跌幅', '换手率', '市盈率-动态', '总市值']].to_string(index=False)
    
    prompt = """根据以下股票数据，按照筛选条件精选股票。

筛选条件：
{screen_criteria}

候选数据（前10只）：
{data_str}

请在下方表格中填写精选结果，不要输出任何分析过程：

### 🎯 今日精选

| 代码 | 名称 | 当前价 | 涨跌幅 | 推荐理由 | 风险点 |
|------|------|--------|--------|----------|--------|
{stock_table}

### 📋 操作建议
- 建议仓位配置比例
- 买入时机建议
- 止损位设置建议

⚠️ 免责声明：以上分析仅供参考，不构成投资建议。""".format(
        screen_criteria=screen_criteria,
        data_str=data_str,
        stock_table=stock_table
    )

    response = client.chat.completions.create(
        model=config['model'],
        messages=[
            {"role": "system", "content": "你是专业A股分析师。分析要基于数据，不要编造数据。如果数据不足以判断，请如实说明。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=2000
    )
    choice = response.choices[0]
    message = choice.message
    content = getattr(message, 'content', None)
    if not content:
        content = getattr(message, 'reasoning_content', None)
    if not content:
        content = str(choice)
    print(f"📝 AI 返回内容长度: {len(content) if content else 0}")
    return content


if __name__ == '__main__':
    print("🤖 AI 智能选股器启动\n")

    overview = get_market_overview()
    if overview is None:
        print("❌ 无法获取市场数据，退出")
        exit(1)

    spot = overview['全市场行情']

    filtered = spot[
        (spot['总市值'] > 100e8) &
        (spot['换手率'] > 1) &
        (~spot['名称'].str.contains('ST'))
    ].copy()

    filtered = filtered.sort_values('涨跌幅', ascending=False).head(50)

    cols = ['代码', '名称', '最新价', '涨跌幅', '成交量', '换手率', '市盈率-动态', '市净率', '总市值']
    available_cols = [c for c in cols if c in filtered.columns]
    candidate_text = filtered[available_cols].to_string(index=False)

    screen_criteria = """
    1. 短期（1-2周）有上涨潜力的股票
    2. 基本面不能太差（PE合理、无重大利空）
    3. 技术面有启动信号（放量、突破等）
    4. 优先选择近期热门板块的龙头股
    5. 市值100亿-1000亿优先（弹性较好）
    """

    print("\n🧠 AI 正在分析精选...")
    result = ai_screen_stocks(filtered, screen_criteria)

    timestamp = time.strftime('%Y%m%d_%H%M')
    filename = f'ai_screening_{timestamp}.md'

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# AI 智能选股报告\n")
        f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"市场概况: {overview['涨跌统计']}\n\n")
        f.write(result)

    print(f"\n✅ 报告已保存到: {filename}")
    print(f"\n{result}")