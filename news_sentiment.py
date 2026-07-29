"""
Day11 - 财经新闻舆情分析
用 AKShare 获取新闻 + DeepSeek 分析情绪
"""
import akshare as ak
import json
import time
import random
import os
from openai import OpenAI
from datetime import datetime

config_path = os.path.join(os.path.dirname(__file__), '.quant', 'config.json')
with open(config_path, 'r', encoding='utf-8-sig') as f:
    config = json.load(f)

client = OpenAI(
    api_key=config['deepseek_api_key'],
    base_url=f"{config.get('deepwise_base_url') or config.get('deepseek_base_url')}/v1"
)


def safe_fetch(func, *args, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries - 1:
                delay = random.uniform(3, 6)
                print(f"  ⚠️ 重试 {attempt+1}/{max_retries}，等待 {delay:.1f}s...")
                time.sleep(delay)
            else:
                print(f"  ❌ 获取失败: {e}")
                return None


def generate_mock_news(count=30):
    mock_news = [
        {"source": "东方财富", "title": "央行宣布下调存款准备金率0.25个百分点", "time": "10:30"},
        {"source": "财联社", "title": "发改委出台新能源汽车补贴政策延续方案", "time": "10:25"},
        {"source": "东方财富", "title": "AI芯片板块爆发，多股涨停", "time": "10:20"},
        {"source": "财联社", "title": "北向资金今日净流入超50亿元", "time": "10:15"},
        {"source": "东方财富", "title": "房地产市场回暖，销售数据环比增长20%", "time": "10:10"},
        {"source": "财联社", "title": "半导体行业景气度回升，订单量明显增加", "time": "10:05"},
        {"source": "东方财富", "title": "医药集采政策落地，创新药企业迎来利好", "time": "09:55"},
        {"source": "财联社", "title": "消费复苏势头强劲，零售数据超预期", "time": "09:50"},
        {"source": "东方财富", "title": "科技股领涨，创业板指突破2500点", "time": "09:45"},
        {"source": "财联社", "title": "央行逆回购操作1000亿元，流动性充裕", "time": "09:40"},
        {"source": "东方财富", "title": "光伏行业迎来政策利好，装机量预期上调", "time": "09:35"},
        {"source": "财联社", "title": "银行板块全线上涨，金融股表现亮眼", "time": "09:30"},
        {"source": "东方财富", "title": "工信部发布人工智能产业发展规划", "time": "09:25"},
        {"source": "财联社", "title": "新能源电池价格企稳，产业链受益", "time": "09:20"},
        {"source": "东方财富", "title": "港股高开，恒生指数涨超1%", "time": "09:15"},
        {"source": "财联社", "title": "保险资金加大权益投资，市场信心提振", "time": "09:10"},
        {"source": "东方财富", "title": "券商股异动，市场交投活跃度提升", "time": "09:05"},
        {"source": "财联社", "title": "5G商用加速推进，通信设备需求增长", "time": "09:00"},
        {"source": "东方财富", "title": "汽车出口创新高，整车企业业绩向好", "time": "08:55"},
        {"source": "财联社", "title": "煤炭价格企稳，能源板块迎来转机", "time": "08:50"},
        {"source": "东方财富", "title": "钢铁行业去产能成效显著，供给端改善", "time": "08:45"},
        {"source": "财联社", "title": "有色金属需求回暖，铜铝价格上涨", "time": "08:40"},
        {"source": "东方财富", "title": "传媒板块热点频现，游戏公司业绩增长", "time": "08:35"},
        {"source": "财联社", "title": "军工订单增长，国防军工板块受关注", "time": "08:30"},
        {"source": "东方财富", "title": "旅游行业复苏，酒店餐饮股集体上涨", "time": "08:25"},
        {"source": "财联社", "title": "电力改革深化，新能源发电占比提升", "time": "08:20"},
        {"source": "东方财富", "title": "环保政策加码，绿色产业迎来机遇", "time": "08:15"},
        {"source": "财联社", "title": "物流行业效率提升，快递企业盈利改善", "time": "08:10"},
        {"source": "东方财富", "title": "农业现代化推进，种业板块获关注", "time": "08:05"},
        {"source": "财联社", "title": "跨境电商政策利好，出口企业受益", "time": "08:00"},
    ]
    return mock_news[:count]


def get_financial_news(count=30):
    print(f"📰 获取最新 {count} 条财经新闻...")

    all_news = []

    try:
        news_em = safe_fetch(ak.stock_info_global_em)
        if news_em is None:
            raise ValueError("接口返回None")
        if not news_em.empty:
            for _, row in news_em.head(count).iterrows():
                all_news.append({
                    'source': '东方财富',
                    'title': str(row.get('标题', row.get('内容', ''))),
                    'time': str(row.get('发布时间', '')),
                })
            print(f"  ✓ 东方财富: {min(count, len(news_em))} 条")
    except Exception as e:
        print(f"  ⚠️ 东方财富新闻: {e}")

    time.sleep(3)

    try:
        news_cls = safe_fetch(ak.stock_info_global_cls)
        if news_cls is None:
            raise ValueError("接口返回None")
        if not news_cls.empty:
            for _, row in news_cls.head(count).iterrows():
                all_news.append({
                    'source': '财联社',
                    'title': str(row.get('标题', row.get('内容', ''))),
                    'time': str(row.get('发布时间', '')),
                })
            print(f"  ✓ 财联社: {min(count, len(news_cls))} 条")
    except Exception as e:
        print(f"  ⚠️ 财联社新闻: {e}")

    if not all_news:
        print("  ⚠️ 未获取到新闻，使用模拟数据")
        all_news = generate_mock_news(count)

    return all_news


def ai_analyze_sentiment(news_list):
    if not news_list:
        return {"score": 50, "summary": "无新闻数据"}

    news_text = "\n".join([
        f"[{n['source']}] {n['title']}"
        for n in news_list[:50]
    ])

    prompt = f"""请分析以下最新财经新闻的市场情绪。

## 最新新闻
{news_text}

请输出：

### 1. 市场情绪评分（0-100分）
- 0-20: 极度悲观
- 20-40: 偏悲观
- 40-60: 中性
- 60-80: 偏乐观
- 80-100: 极度乐观

评分: XX分

### 2. 情绪概要（3句话以内）

### 3. 关键主题（列出3-5个新闻聚焦的主题）

### 4. 对A股的潜在影响
- 利好板块：
- 利空板块：
- 需关注事件："""

    response = client.chat.completions.create(
        model=config['model'],
        messages=[
            {"role": "system", "content": "你是财经新闻分析师，擅长从新闻中提炼市场情绪信号。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=1000
    )

    choice = response.choices[0]
    message = choice.message
    content = getattr(message, 'content', None)
    if not content:
        content = getattr(message, 'reasoning_content', None)
    if not content:
        content = str(choice)

    return content


if __name__ == '__main__':
    print("📰 财经舆情分析系统启动\n")

    news = get_financial_news(30)
    print(f"\n共获取 {len(news)} 条新闻")

    if news:
        print("\n🧠 AI 正在分析舆情...")
        result = ai_analyze_sentiment(news)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f'news_sentiment_{timestamp}.md'

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# 财经舆情分析报告\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"新闻数量: {len(news)} 条\n\n")
            f.write(result)

        print(f"\n✅ 报告已保存到: {filename}")
        print(f"\n{result}")
    else:
        print("❌ 未获取到新闻数据")