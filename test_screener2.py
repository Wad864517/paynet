# -*- coding: utf-8 -*-
"""用 gen_token 生成的 token 测 /api/auth/me + /api/screener（不 login，避开 INSERT 卡）"""
import urllib.request, json

TOKEN = open(r'D:\dbtest\paynet\_token.txt').read().strip()
BASE = 'http://127.0.0.1:51888'


def get(path):
    req = urllib.request.Request(BASE + path, headers={'Authorization': 'Bearer ' + TOKEN})
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return r.status, json.loads(r.read().decode('utf-8'))
    except Exception as e:
        return str(e), None


print('=== /api/auth/me (有效token) ===')
print(get('/api/auth/me'))

print('\n=== /api/screener (max tier) ===')
st, s = get('/api/screener')
print('status:', st)
if s:
    print('tier=', s.get('tier'), 'stocks=', len(s.get('stocks', [])),
          'analysis?', bool(s.get('analysis')), 'disclaimer?', bool(s.get('disclaimer')))
    print('前3只:', [(x['code'], x['name'], x['score']) for x in s.get('stocks', [])[:3]])
    print('disclaimer:', (s.get('disclaimer') or '')[:60])
else:
    print('无响应')
