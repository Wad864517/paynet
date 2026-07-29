# -*- coding: utf-8 -*-
"""商业版 server.py 接口冒烟测试"""
import urllib.request, urllib.error, json

BASE = 'http://127.0.0.1:51888'


def post(path, data):
    req = urllib.request.Request(BASE + path,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}, method='POST')
    try:
        r = urllib.request.urlopen(req, timeout=10)
        return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))


def get(path, token=None):
    h = {'Authorization': 'Bearer ' + token} if token else {}
    req = urllib.request.Request(BASE + path, headers=h)
    try:
        r = urllib.request.urlopen(req, timeout=10)
        return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))


def main():
    print('=== 1. 注册 demo/demo123 ===')
    print(post('/api/auth/register', {'username': 'demo', 'password': 'demo123'}))

    print('\n=== 2. 登录(未激活) ===')
    st, j = post('/api/auth/login', {'username': 'demo', 'password': 'demo123'})
    print(st, 'licensed=', j.get('licensed'), 'token?', 'token' in j)

    print('\n=== 3. overview 无 token → 应401 ===')
    print(get('/api/overview'))

    print('\n=== 4. overview 用未激活token → 应403 ===')
    print(get('/api/overview', j.get('token', '')))

    print('\n=== 5. 激活(正确授权码) ===')
    print(post('/api/auth/activate', {'username': 'demo', 'password': 'demo123',
                                        'license_key': 'PAYNET-DEMO-2026'}))

    print('\n=== 6. 激活后登录拿 token ===')
    st, j = post('/api/auth/login', {'username': 'demo', 'password': 'demo123'})
    token = j.get('token', '')
    print(st, 'licensed=', j.get('licensed'))

    print('\n=== 7. overview 带授权 token → 应200 + 数据 ===')
    st, o = get('/api/overview', token)
    print(st, 'data_date=', o.get('data_date'), 'user=', o.get('user'),
          'sentiment=', o.get('sentiment_score'), 'pnl=', o.get('total_pnl'))

    print('\n=== 8. positions 带授权 → 应200 ===')
    st, p = get('/api/positions', token)
    print(st, 'history=', len(p.get('history', [])), 'positions=', p.get('count'))

    print('\n=== 9. 登录页 / → 200 ===')
    req = urllib.request.Request(BASE + '/')
    print(urllib.request.urlopen(req, timeout=10).status)

    print('\n全部通过 ✓' if st == 200 else '\n有问题 ✗')


if __name__ == '__main__':
    main()
