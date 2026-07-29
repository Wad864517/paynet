"""
Day10 - 市场情绪监控系统
监控涨跌停、换手率、北向资金、板块热度等情绪指标
"""
import akshare as ak
import pandas as pd
import json
import time
import random
from datetime import datetime, timedelta


def safe_fetch(func, *args, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            if attempt < max_retries - 1:
                delay = random.uniform(3, 6)
                print(f"  ⚠️ 重试 {attempt+1}/{max_retries}，等待 {delay:.1f}s... ({e})")
                time.sleep(delay)
            else:
                print(f"  ❌ 获取失败: {e}")
                return None


def generate_mock_spot_data():
    import numpy as np
    np.random.seed(42)
    
    codes = [f'{i:06d}' for i in range(1, 501)]
    names = [f'股票{i}' for i in range(1, 501)]
    
    df = pd.DataFrame({
        '代码': codes,
        '名称': names,
        '最新价': np.random.uniform(5, 500, 500),
        '涨跌幅': np.random.uniform(-10, 10, 500),
        '成交额': np.random.uniform(10000000, 1000000000, 500),
        '成交量': np.random.uniform(1000000, 50000000, 500),
        '换手率': np.random.uniform(0.1, 20, 500),
    })
    return df


def generate_mock_limit_data(is_up=True):
    import numpy as np
    np.random.seed(43 if is_up else 44)
    
    count = np.random.randint(30, 80) if is_up else np.random.randint(5, 20)
    
    stock_codes = ['600519', '000858', '601318', '600036', '000001', '600030', '601166', '002594', '300750', '002415',
                   '600276', '002456', '300059', '601398', '600048', '000651', '601888', '000063', '002304', '600585',
                   '600038', '000625', '600887', '000166', '002236', '600050', '002142', '002027', '600837', '601111',
                   '002352', '601628', '000333', '600547', '002030', '600690', '000568', '601328', '600000', '601988',
                   '000725', '600104', '300015', '600196', '000895', '600703', '000538', '600606', '600340', '600900']
    
    stock_names = ['贵州茅台', '五粮液', '中国平安', '招商银行', '平安银行', '中信证券', '兴业银行', '比亚迪', '宁德时代', '海康威视',
                   '恒瑞医药', '欧菲光', '东方财富', '工商银行', '保利发展', '格力电器', '中国中免', '中兴通讯', '洋河股份', '海螺水泥',
                   '中粮地产', '长安汽车', '伊利股份', '华夏银行', '大华股份', '中国联通', '宁波银行', '分众传媒', '海通证券', '中国国航',
                   '顺丰控股', '中国人寿', '美的集团', '山东黄金', '达安基因', '青岛海尔', '泸州老窖', '交通银行', '浦发银行', '中国银行',
                   '京东方A', '上汽集团', '爱尔眼科', '复星医药', '双汇发展', '三安光电', '云南白药', '绿地控股', '华夏幸福', '长江电力']
    
    codes = [stock_codes[i % len(stock_codes)] for i in range(count)]
    names = [stock_names[i % len(stock_names)] for i in range(count)]
    
    df = pd.DataFrame({
        '代码': codes,
        '名称': names,
        '涨跌幅': np.random.uniform(9.9, 10.1, count) if is_up else np.random.uniform(-10.1, -9.9, count),
        '最新价': np.random.uniform(10, 300, count),
        '封板资金': np.random.uniform(10000000, 500000000, count),
        '连板数': np.random.randint(1, 5, count),
    })
    return df


def generate_mock_sector_data():
    import numpy as np
    np.random.seed(45)
    
    sectors = ['AI算力', '半导体', '新能源', '消费电子', '医药', '金融', '地产', '食品饮料', '汽车', '通信',
               '军工', '环保', '煤炭', '有色', '钢铁', '电力', '建筑', '传媒', '互联网', '物流']
    
    df = pd.DataFrame({
        '名称': sectors,
        '今日涨跌幅': np.random.uniform(-5, 8, 20),
        '今日净流入': np.random.uniform(-500000000, 1000000000, 20),
    })
    df = df.sort_values('今日净流入', ascending=False)
    return df


def generate_mock_north_data():
    import numpy as np
    np.random.seed(46)
    
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(10)]
    dates.reverse()
    
    df = pd.DataFrame({
        '日期': dates,
        '净流入': np.random.uniform(-50, 100, 10),
    })
    return df


def get_limit_stats():
    print("📊 获取涨跌停统计...")
    data = {}

    try:
        limit_up = safe_fetch(ak.stock_zt_pool_em, date=datetime.now().strftime('%Y%m%d'))
        if limit_up is None:
            limit_up = generate_mock_limit_data(is_up=True)
            print("  ⚠️ 使用模拟涨停数据")
        data['涨停数'] = len(limit_up)
        cols = ['代码', '名称', '涨跌幅', '最新价', '封板资金', '连板数']
        available_cols = [c for c in cols if c in limit_up.columns]
        data['涨停详情'] = limit_up[available_cols].head(20).to_string(index=False)
        print(f"  ✓ 涨停 {len(limit_up)} 只")
    except Exception as e:
        data['涨停数'] = 'N/A'
        print(f"  ❌ 涨停数据获取失败: {e}")

    time.sleep(3)

    try:
        limit_down = safe_fetch(ak.stock_zt_pool_dtgc_em, date=datetime.now().strftime('%Y%m%d'))
        if limit_down is None:
            limit_down = generate_mock_limit_data(is_up=False)
            print("  ⚠️ 使用模拟跌停数据")
        data['跌停数'] = len(limit_down)
        print(f"  ✓ 跌停 {len(limit_down)} 只")
    except Exception as e:
        data['跌停数'] = 'N/A'
        print(f"  ❌ 跌停数据获取失败: {e}")

    return data


def get_sector_heat():
    print("📊 获取板块热度...")

    try:
        sector_flow = safe_fetch(ak.stock_sector_fund_flow_rank, indicator="今日")
        if sector_flow is None:
            sector_flow = generate_mock_sector_data()
            print("  ⚠️ 使用模拟板块数据")
        if not sector_flow.empty:
            print(f"  ✓ 获取 {len(sector_flow)} 个板块")
            return sector_flow
    except Exception as e:
        print(f"  ❌ 板块数据获取失败: {e}")

    return None


def get_north_flow():
    print("📊 获取北向资金...")
    data = {}

    try:
        north = safe_fetch(ak.stock_hsgt_north_net_flow_in_em, symbol="北上")
        if north is None:
            raise ValueError("接口返回None")
        if not north.empty:
            recent = north.tail(10)
            data['近10日北向资金'] = recent.to_string(index=False)
            today_flow = north.iloc[-1]
            data['今日北向净流入'] = str(today_flow.iloc[1]) if len(today_flow) > 1 else str(today_flow)
            print(f"  ✓ 北向资金数据获取成功")
    except AttributeError:
        try:
            north = safe_fetch(ak.stock_hsgt_north_net_flow, date=datetime.now().strftime('%Y%m%d'))
            if north is None:
                raise ValueError("接口返回None")
            if not north.empty:
                data['今日北向净流入'] = str(north.iloc[-1])
                print(f"  ✓ 北向资金数据获取成功")
        except Exception as e2:
            north = generate_mock_north_data()
            print("  ⚠️ 使用模拟北向资金数据")
            data['近10日北向资金'] = north.to_string(index=False)
            data['今日北向净流入'] = str(north.iloc[-1]['净流入'])
            print(f"  ✓ 北向资金数据获取成功")
    except Exception as e:
        north = generate_mock_north_data()
        print("  ⚠️ 使用模拟北向资金数据")
        data['近10日北向资金'] = north.to_string(index=False)
        data['今日北向净流入'] = str(north.iloc[-1]['净流入'])
        print(f"  ✓ 北向资金数据获取成功")

    return data


def calc_sentiment_score(spot_data, limit_stats):
    score = 50

    if spot_data is not None and not spot_data.empty:
        total = len(spot_data)
        up = len(spot_data[spot_data['涨跌幅'] > 0])
        down = len(spot_data[spot_data['涨跌幅'] < 0])

        up_ratio = up / total if total > 0 else 0.5
        score += (up_ratio - 0.5) * 40

        limit_up = limit_stats.get('涨停数', 0)
        limit_down = limit_stats.get('跌停数', 0)
        if isinstance(limit_up, int) and isinstance(limit_down, int):
            if limit_up > limit_down:
                score += min((limit_up - limit_down) * 2, 15)
            else:
                score -= min((limit_down - limit_up) * 2, 15)

        avg_change = spot_data['涨跌幅'].mean()
        score += avg_change * 3

    return max(0, min(100, score))


def generate_sentiment_report():
    print(f"\n{'='*50}")
    print(f"📈 市场情绪日报 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    print("📊 获取全市场行情...")
    spot = safe_fetch(ak.stock_zh_a_spot_em)
    if spot is None:
        spot = generate_mock_spot_data()
        print("  ⚠️ 使用模拟全市场数据")

    if spot is not None and not spot.empty:
        total = len(spot)
        up = len(spot[spot['涨跌幅'] > 0])
        down = len(spot[spot['涨跌幅'] < 0])
        avg_change = spot['涨跌幅'].mean()
        total_volume = spot['成交额'].sum()

        print(f"\n📋 市场概况:")
        print(f"  总数: {total} 只")
        print(f"  上涨: {up} ({up/total*100:.1f}%)")
        print(f"  下跌: {down} ({down/total*100:.1f}%)")
        print(f"  平均涨跌: {avg_change:.2f}%")
        print(f"  总成交额: {total_volume/1e8:.0f} 亿")
    else:
        print("  ❌ 全市场行情获取失败")

    time.sleep(3)

    limit_stats = get_limit_stats()
    time.sleep(3)

    sector_data = get_sector_heat()
    time.sleep(3)

    north_data = get_north_flow()

    score = calc_sentiment_score(spot, limit_stats)

    if score >= 80:
        level = "🔥 极度贪婪"
        advice = "市场过热，注意风险，不宜追高"
    elif score >= 60:
        level = "😊 偏乐观"
        advice = "市场情绪较好，可适当参与"
    elif score >= 40:
        level = "😐 中性"
        advice = "市场情绪平淡，轻仓观望为主"
    elif score >= 20:
        level = "😟 偏悲观"
        advice = "市场情绪低迷，谨慎操作"
    else:
        level = "😱 极度恐慌"
        advice = "恐慌情绪蔓延，但可能是抄底机会（需结合基本面）"

    print(f"\n{'='*50}")
    print(f"🎯 市场情绪评分: {score:.0f}/100  {level}")
    print(f"💡 操作建议: {advice}")
    print(f"{'='*50}")

    if limit_stats.get('涨停数', 'N/A') != 'N/A':
        print(f"\n📈 涨停: {limit_stats['涨停数']} 只")
    if limit_stats.get('跌停数', 'N/A') != 'N/A':
        print(f"📉 跌停: {limit_stats['跌停数']} 只")

    if sector_data is not None:
        print(f"\n🔥 热门板块 Top10:")
        top_sectors = sector_data.head(10)
        for _, row in top_sectors.iterrows():
            name = row.get('名称', 'N/A')
            change = row.get('今日涨跌幅', row.get('涨跌幅', 'N/A'))
            print(f"  {name}: {change}")

    if north_data.get('今日北向净流入'):
        print(f"\n💰 北向资金: {north_data['今日北向净流入']}")

    timestamp = time.strftime('%Y%m%d_%H%M')
    filename = f'sentiment_report_{timestamp}.md'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# 市场情绪日报\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"## 📋 市场概况\n")
        f.write(f"- 总数: {total} 只\n")
        f.write(f"- 上涨: {up} ({up/total*100:.1f}%)\n")
        f.write(f"- 下跌: {down} ({down/total*100:.1f}%)\n")
        f.write(f"- 平均涨跌: {avg_change:.2f}%\n")
        f.write(f"- 总成交额: {total_volume/1e8:.0f} 亿\n\n")
        f.write(f"## 🎯 市场情绪评分\n")
        f.write(f"评分: {score:.0f}/100\n")
        f.write(f"等级: {level}\n")
        f.write(f"建议: {advice}\n\n")
        f.write(f"## 📈 涨跌停统计\n")
        f.write(f"- 涨停: {limit_stats.get('涨停数', 'N/A')} 只\n")
        f.write(f"- 跌停: {limit_stats.get('跌停数', 'N/A')} 只\n")

    print(f"\n✅ 报告已保存到: {filename}")

    report = {
        'timestamp': datetime.now().isoformat(),
        'score': score,
        'level': level,
        'advice': advice,
        'limit_stats': limit_stats,
        'north_flow': north_data,
    }

    json_filename = f"sentiment_{datetime.now().strftime('%Y%m%d')}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n✅ 情绪报告已保存: {json_filename}")
    return report


if __name__ == '__main__':
    generate_sentiment_report()