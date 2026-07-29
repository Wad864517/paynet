# -*- coding: utf-8 -*-
"""选股研究 API + 订阅分层测试"""
import urllib.request, urllib.error, json

BASE = 'http://127.0.0.1:51888'


def post(path, data):
    req = urllib.request.Request(BASE + path, data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}, method='POST')
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))


def get(path, token=None):
    h = {'Authorization': 'Bearer ' + token} if token else {}
    req = urllib.request.Request(BASE + path, headers=h)
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))


print('=== 1. demo 登录(tier已设max) ===')
st, j = post('/api/auth/login', {'username': 'demo', 'password': 'demo123'})
token = j.get('token')
print('login:', st, 'token?', bool(token))

print('\n=== 2. /api/auth/me (tier) ===')
st, m = get('/api/auth/me', token)
print(st, 'user=', m.get('user'), 'tier=', m.get('tier'))

print('\n=== 3. /api/screener (max: 应返回10只+分析+免责) ===')
st, s = get('/api/screener', token)
print(st, 'stocks=', len(s.get('stocks', [])), 'tier=', s.get('tier'),
      'analysis?', bool(s.get('analysis')), 'disclaimer?', bool(s.get('disclaimer')))
print('前3只:', [(x['code'], x['name'], x['score']) for x in s.get('stocks', [])[:3]])

print('\n=== 4. 未激活用户 screener → 应403 ===')
post('/api/auth/register', {'username': 'freeu', 'password': 'free123'})
st, j = post('/api/auth/login', {'username': 'freeu', 'password': 'free123'})
print(get('/api/screener', j.get('token')))

ok = (st == 403) and (len(s.get('stocks', [])) == 10) and (m.get('tier') == 'max')
print('\n全部通过 ✓' if ok else '\n有问题 ✗')
