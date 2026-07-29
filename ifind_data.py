# -*- coding: utf-8 -*-
"""iFinD 数据源（同花顺 L2）—— 纯 HTTP API（requests）
refresh_token → access_token(缓存6天) → 实时行情/历史K线/智能选股。
"""
import json
import os
import time
import requests

config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.quant', 'config.json')
with open(config_path, 'r', encoding='utf-8-sig') as f:
    config = json.load(f)
REFRESH_TOKEN = config.get('ifind_refresh_token', '')

BASE_URL = 'https://quantapi.51ifind.com/api/v1'
_access_token = None
_access_token_expire = 0

DISCLAIMER = "本结果由模型基于公开行情数据生成的选股研究信号，仅用于研究参考，不构成任何投资建议或买卖推荐。"


def is_available():
    return bool(REFRESH_TOKEN)


def get_access_token():
    global _access_token, _access_token_expire
    if _access_token and time.time() < _access_token_expire:
        return _access_token, None
    try:
        r = requests.post(f'{BASE_URL}/get_access_token',
                          headers={'Content-Type': 'application/json',
                                   'refresh_token': REFRESH_TOKEN},
                          timeout=15)
        d = r.json()
        if d.get('errcode') not in (0, None):
            return None, f"errcode={d.get('errcode')} {d.get('errmsg', '')}"
        token = d.get('data', {}).get('access_token') or d.get('access_token')
        if not token:
            return None, f'未找到 access_token: {str(d)[:200]}'
        _access_token = token
        _access_token_expire = time.time() + 6 * 24 * 3600
        return token, None
    except Exception as e:
        return None, str(e)


def to_ifind_code(code):
    code = str(code).zfill(6)
    if code.startswith(('60', '68', '90')):
        return code + '.SH'
    return code + '.SZ'


def get_realtime(codes):
    """实时行情。codes: ['600519',...] → (json, error)"""
    token, err = get_access_token()
    if err:
        return None, err
    try:
        ifind_codes = [to_ifind_code(c) for c in codes]
        r = requests.post(f'{BASE_URL}/real_time_quotation',
            headers={'access_token': token, 'Content-Type': 'application/json'},
            json={'codes': ','.join(ifind_codes),
                  'indicators': 'latest,open,high,low,preClose,change,changeRatio,volume,amount,turnOver,pe_ttm,totalMktCap'},
            timeout=30)
        return r.json(), None
    except Exception as e:
        return None, str(e)


def get_history(code, start_date, end_date):
    """历史日K线。code:'600519', 日期'YYYY-MM-DD' → (json, error)"""
    token, err = get_access_token()
    if err:
        return None, err
    try:
        r = requests.post(f'{BASE_URL}/cmd_history_quotation',
            headers={'access_token': token, 'Content-Type': 'application/json'},
            json={'codes': to_ifind_code(code),
                  'indicators': 'open,high,low,close,volume,amount,turnOver,change,changeRatio',
                  'startdate': start_date,
                  'enddate': end_date,
                  'functionpara': {'Fill': 'Blank'}},
            timeout=30)
        return r.json(), None
    except Exception as e:
        return None, str(e)


def smart_pick(query):
    """智能选股"""
    token, err = get_access_token()
    if err:
        return None, err
    try:
        r = requests.post(f'{BASE_URL}/smart_stock_picking',
            headers={'Content-Type': 'application/json', 'access_token': token},
            json={'searchstring': query, 'searchtype': 'stock'},
            timeout=30)
        return r.json(), None
    except Exception as e:
        return None, str(e)


if __name__ == '__main__':
    print('iFinD 可用:', is_available())
    if is_available():
        t, e = get_access_token()
        print('access_token:', 'OK' if t else 'FAIL', e or '')
        if t:
            print('\n=== 实时行情(茅台/平安/宁德) ===')
            r, err = get_realtime(['600519', '601318', '300750'])
            print('err:', err)
            print(json.dumps(r, ensure_ascii=False, indent=2)[:800] if r else '无返回')
            print('\n=== 历史K线(茅台 近1年) ===')
            h, herr = get_history('600519', '2025-07-29', '2026-07-29')
            print('err:', herr)
            print(json.dumps(h, ensure_ascii=False, indent=2)[:600] if h else '无返回')
