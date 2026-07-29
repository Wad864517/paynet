# -*- coding: utf-8 -*-
"""
选股研究引擎 (screener.py) —— 合法版
不荐股，提供选股研究信号 / 评分 / 分析 + 免责声明。
用 3.11.9 python 跑（akshare / openai / pandas）。
输出 screener_result.json。
"""
import akshare as ak
import json
import os
from datetime import datetime
from openai import OpenAI

config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.quant', 'config.json')
with open(config_path, 'r', encoding='utf-8-sig') as f:
    config = json.load(f)
client = OpenAI(api_key=config['deepseek_api_key'],
                base_url=f"{config.get('deepseek_base_url')}/v1")

DISCLAIMER = ("本结果由模型基于公开行情数据生成的选股研究信号，"
             "仅用于研究参考，不构成任何投资建议或买卖推荐。"
             "股市有风险，投资决策请自主判断，风险自担。")


def fetch_universe():
    # 优先 iFinD（配置了 token 时用 L2 智能选股，真实数据）
    try:
        import ifind_data
        if ifind_data.is_available():
            return fetch_ifind(), None
    except Exception:
        pass
    # fallback: akshare
    try:
        spot = ak.stock_zh_a_spot_em()
        return spot, None
    except Exception as e:
        return None, str(e)


def fetch_ifind():
    """iFinD 智能选股取涨幅靠前，转 akshare 兼容 DataFrame"""
    import ifind_data
    import pandas as pd
    sp, err = ifind_data.smart_pick('涨幅前20')
    if err:
        raise RuntimeError(f'iFinD smart_pick 失败: {err}')
    table = sp['tables'][0]['table']
    codes = table.get('股票代码', [])
    names = table.get('股票简称', [])
    chg_key = [k for k in table if k.startswith('涨跌幅:前复权') and '排名' not in k]
    chgs = table.get(chg_key[0], []) if chg_key else [0] * len(codes)
    df = pd.DataFrame({
        '代码': [str(c).split('.')[0] for c in codes],
        '名称': names,
        '涨跌幅': [float(c) for c in chgs],
        '最新价': [0.0] * len(codes),
        '换手率': [0.0] * len(codes),
        '市盈率-动态': [0.0] * len(codes),
        '总市值': [0.0] * len(codes),
    })
    return df


def score_stock(row):
    """技术面+基本面综合评分 0-100（研究信号强度，非推荐）"""
    try:
        chg = float(row.get('涨跌幅', 0) or 0)
        turnover = float(row.get('换手率', 0) or 0)
        pe = float(row.get('市盈率-动态', 0) or 0)
        s = 50
        s += min(max(chg, -10), 10) * 2
        s += min(max(turnover, 0), 20) * 1.2
        if 0 < pe < 30:
            s += 8
        elif pe <= 0:
            s -= 5
        return round(max(0, min(100, s)), 1)
    except Exception:
        return 50.0


def signals(row):
    tags = []
    chg = float(row.get('涨跌幅', 0) or 0)
    turnover = float(row.get('换手率', 0) or 0)
    pe = float(row.get('市盈率-动态', 0) or 0)
    if chg >= 7:
        tags.append('强势上涨')
    elif chg >= 3:
        tags.append('放量上行')
    if turnover >= 8:
        tags.append('换手活跃')
    if 0 < pe < 15:
        tags.append('低估值')
    if chg <= 0:
        tags.append('回调')
    return tags or ['常规']


def ai_research(df_top):
    """DeepSeek 研究分析（客观研究，严禁荐股措辞）"""
    cols = ['代码', '名称', '最新价', '涨跌幅', '换手率', '市盈率-动态', '总市值']
    data_str = df_top[cols].head(10).to_string(index=False)
    prompt = f"""以下为今日涨幅靠前股票的行情数据，请从研究角度分析其关注价值（基本面/技术面/资金面特征及风险点）。
严禁出现"推荐买入/卖出/建仓"等投资建议措辞，只做客观研究分析。

数据：
{data_str}

请输出：每只股票的研究要点和风险点（表格），以及整体市场情绪观察。结尾加一句免责声明。"""
    try:
        resp = client.chat.completions.create(
            model=config['model'],
            messages=[
                {"role": "system", "content": "你是A股研究分析师，输出客观研究分析，绝不构成投资建议，不出现推荐买卖措辞。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3, max_tokens=1500)
        msg = resp.choices[0].message
        return getattr(msg, 'content', None) or getattr(msg, 'reasoning_content', None) or '(无分析)'
    except Exception as e:
        return f'(AI研究分析失败: {e})'


def run():
    spot, err = fetch_universe()
    if err:
        return {'ok': False, 'error': err, 'disclaimer': DISCLAIMER,
                'timestamp': datetime.now().isoformat()}
    df = spot[spot['涨跌幅'] > 0].sort_values('涨跌幅', ascending=False).head(20)
    stocks = []
    for _, r in df.iterrows():
        pe = r.get('市盈率-动态')
        stocks.append({
            'code': str(r.get('代码', '')),
            'name': str(r.get('名称', '')),
            'price': round(float(r.get('最新价', 0) or 0), 2),
            'change_pct': round(float(r.get('涨跌幅', 0) or 0), 2),
            'turnover': round(float(r.get('换手率', 0) or 0), 2),
            'pe': round(float(pe), 2) if pe not in (None, '') and float(pe or 0) != 0 else None,
            'market_cap_yi': round(float(r.get('总市值', 0) or 0) / 1e8, 1),
            'score': score_stock(r),
            'signals': signals(r),
        })
    analysis = ai_research(df.head(10))
    result = {
        'ok': True,
        'stocks': stocks,
        'analysis': analysis,
        'disclaimer': DISCLAIMER,
        'market_stats': {
            'up': int((spot['涨跌幅'] > 0).sum()),
            'down': int((spot['涨跌幅'] < 0).sum()),
            'limit_up': int((spot['涨跌幅'] >= 9.9).sum()),
            'limit_down': int((spot['涨跌幅'] <= -9.9).sum()),
        },
        'timestamp': datetime.now().isoformat(),
    }
    return result


if __name__ == '__main__':
    print('选股研究引擎启动...')
    r = run()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'screener_result.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(r, f, ensure_ascii=False, indent=2)
    if r.get('ok'):
        print(f"完成: {len(r['stocks'])} 只研究信号, 市场上涨{r['market_stats']['up']}家")
    else:
        print(f"失败: {r.get('error')}")
    print(f"结果存: {out}")
