# -*- coding: utf-8 -*-
"""
paynet 商业版 SaaS 后端 (server.py)
面向个人散户 · 一次性买断 · 云端多用户
- 用户体系：注册 / 登录 / 买断激活
- 授权：token + license 校验，未激活不可用
- 仪表盘 API：复用结果文件读取，多用户共享数据（后续可分用户策略/持仓）
"""
import os, sys, json, csv, glob, subprocess, threading, uuid, sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, jsonify, request, send_from_directory, abort, g
from werkzeug.security import generate_password_hash, check_password_hash


def _resolve_base_dir():
    if getattr(sys, 'frozen', False):
        d = os.path.dirname(sys.executable)
        for _ in range(4):
            if os.path.isdir(os.path.join(d, 'data')):
                return d
            p = os.path.dirname(d)
            if p == d:
                break
            d = p
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


if getattr(sys, 'frozen', False):
    BASE_DIR = _resolve_base_dir()
    RESOURCE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = BASE_DIR

DB_PATH = os.path.join(BASE_DIR, 'users.db')
PREF_FILE = os.path.join(BASE_DIR, '.quant', 'dashboard_prefs.json')
DEFAULT_PY = r"C:\Users\sendy322\AppData\Local\Programs\Python\Python311\python.exe"

MODULES = {
    'daily_scan': 'daily_scan.py', 'money_tracker': 'money_tracker.py',
    'sentiment': 'sentiment_monitor.py', 'ai_screening': 'ai_stock_screener.py',
    'news_sentiment': 'news_sentiment.py', 'daily_workflow': 'daily_workflow.py',
    'screener': 'screener.py',
    'backtest': 'backtest_local.py',
}

app = Flask(__name__, static_folder=None)
STATE = {'python_exe': DEFAULT_PY, 'running': {}, 'last_refresh': {}, 'last_log': {}}


# ---------------- DB ----------------
def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()
    db.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        license_key TEXT,
        license_activated_at TEXT,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL
    );
    ''')
    # 兼容已存在表：加 tier 列(订阅分层 free/pro/max)
    try:
        db.execute("ALTER TABLE users ADD COLUMN tier TEXT DEFAULT 'free'")
    except Exception:
        pass
    db.commit()
    db.close()


init_db()


def load_prefs():
    try:
        with open(PREF_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


STATE['python_exe'] = load_prefs().get('python_exe', DEFAULT_PY)


def create_token(user_id):
    t = uuid.uuid4().hex
    db = get_db()
    db.execute('INSERT INTO sessions(token,user_id,created_at) VALUES(?,?,?)',
               (t, user_id, datetime.now().isoformat()))
    db.commit()
    db.close()
    return t


def get_user_by_token(token):
    db = get_db()
    r = db.execute('SELECT u.* FROM sessions s JOIN users u ON s.user_id=u.id WHERE s.token=?',
                   (token,)).fetchone()
    db.close()
    return r


def auth_required(f):
    @wraps(f)
    def w(*a, **kw):
        tok = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
        if not tok:
            return jsonify({'error': '未登录'}), 401
        u = get_user_by_token(tok)
        if not u:
            return jsonify({'error': 'token 无效或已过期'}), 401
        if not u['license_activated_at']:
            return jsonify({'error': '未授权，请先激活'}), 403
        g.user = u
        return f(*a, **kw)
    return w


# ---------------- 读结果（复用 app.py 逻辑） ----------------
def latest_file(pat):
    fs = glob.glob(os.path.join(BASE_DIR, pat))
    if not fs:
        return None
    fs.sort(key=os.path.getmtime, reverse=True)
    return fs[0]


def read_text(p):
    if not p:
        return None
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f'(读取失败:{e})'


def read_json(p):
    if not p:
        return None
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def latest_data_dir():
    sub = [d for d in glob.glob(os.path.join(BASE_DIR, 'data', '*')) if os.path.isdir(d)]
    if not sub:
        return None
    sub.sort(key=os.path.getmtime, reverse=True)
    return sub[0]


def read_csv_rows(p, max_rows=300):
    if not p or not os.path.isfile(p):
        return [], []
    try:
        with open(p, 'r', encoding='utf-8-sig') as f:
            rd = csv.reader(f)
            h, rows = [], []
            for i, row in enumerate(rd):
                if i == 0:
                    h = row
                    continue
                if i > max_rows:
                    break
                rows.append(row)
            return h, rows
    except Exception:
        return [], []


def mtime_str(p):
    if not p:
        return None
    try:
        return datetime.fromtimestamp(os.path.getmtime(p)).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return None


def compute_positions():
    trades = read_json(os.path.join(BASE_DIR, 'paper_trades.json')) or []
    pos = {}
    for t in trades:
        c = t.get('code', '')
        p = pos.setdefault(c, {'code': c, 'name': t.get('name', ''), 'qty': 0, 'cost': 0.0, 'last': 0.0})
        if t.get('name'):
            p['name'] = t['name']
        a, q, pr = t.get('action'), t.get('shares', 0) or 0, t.get('price', 0) or 0
        if a == 'BUY':
            p['cost'] += q * pr
            p['qty'] += q
            p['last'] = pr
        elif a == 'SELL':
            p['qty'] -= q
            p['last'] = pr
    positions = []
    for c, p in pos.items():
        if p['qty'] > 0:
            avg = p['cost'] / p['qty'] if p['qty'] else 0
            last = p['last'] or avg
            positions.append({'code': c, 'name': p['name'], 'qty': p['qty'],
                              'avg_cost': round(avg, 2), 'last_price': round(last, 2),
                              'market_value': round(last * p['qty'], 2),
                              'pnl': round((last - avg) * p['qty'], 2),
                              'pnl_pct': round((last - avg) / avg * 100, 2) if avg else 0})
    history = sorted(trades, key=lambda x: x.get('time', ''), reverse=True)
    return {'positions': positions, 'history': history,
            'total_market_value': round(sum(x['market_value'] for x in positions), 2),
            'total_pnl': round(sum(x['pnl'] for x in positions), 2), 'count': len(positions)}


def run_refresh(module):
    script = MODULES.get(module)
    STATE['running'][module] = True
    STATE['last_log'][module] = '运行中...'
    try:
        proc = subprocess.run([STATE['python_exe'], script], cwd=BASE_DIR,
                              capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=600)
        log = (proc.stdout or '') + ('\n[stderr]\n' + proc.stderr if proc.stderr else '')
        STATE['last_log'][module] = log[-5000:] or '(无输出)'
        STATE['last_refresh'][module] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    except subprocess.TimeoutExpired:
        STATE['last_log'][module] = '超时(>600s)'
    except Exception as e:
        STATE['last_log'][module] = f'错误:{e}'
    finally:
        STATE['running'][module] = False


# ---------------- 前端页面 ----------------
@app.route('/')
def index():
    return send_from_directory(RESOURCE_DIR, 'login.html')


@app.route('/app')
def dashboard_page():
    # 页面本身公开，由前端 JS 校验 token；所有 API 需 token
    return send_from_directory(RESOURCE_DIR, 'dashboard.html')


# ---------------- auth API ----------------
@app.route('/api/auth/register', methods=['POST'])
def register():
    d = request.get_json(silent=True) or {}
    u, p = d.get('username', '').strip(), d.get('password', '')
    if not u or not p or len(p) < 6:
        return jsonify({'ok': False, 'error': '用户名必填，密码至少6位'}), 400
    db = get_db()
    try:
        db.execute('INSERT INTO users(username,password_hash,created_at) VALUES(?,?,?)',
                   (u, generate_password_hash(p, method='pbkdf2:sha256', salt_length=16), datetime.now().isoformat()))
        db.commit()
    except sqlite3.IntegrityError:
        db.close()
        return jsonify({'ok': False, 'error': '用户名已存在'}), 400
    db.close()
    return jsonify({'ok': True, 'message': '注册成功，请登录'})


@app.route('/api/auth/login', methods=['POST'])
def login():
    import sys as _s
    d = request.get_json(silent=True) or {}
    u, p = d.get('username', '').strip(), d.get('password', '')
    print(f'[login] {u} start', file=_s.stderr, flush=True)
    db = get_db()
    print('[login] db opened', file=_s.stderr, flush=True)
    r = db.execute('SELECT * FROM users WHERE username=?', (u,)).fetchone()
    db.close()
    print(f'[login] fetched user={r is not None}', file=_s.stderr, flush=True)
    if not r or not check_password_hash(r['password_hash'], p):
        print('[login] password fail', file=_s.stderr, flush=True)
        return jsonify({'ok': False, 'error': '用户名或密码错误'}), 401
    print('[login] pw ok, creating token', file=_s.stderr, flush=True)
    token = create_token(r['id'])
    print('[login] token done', file=_s.stderr, flush=True)
    return jsonify({'ok': True, 'token': token, 'licensed': bool(r['license_activated_at'])})


@app.route('/api/auth/activate', methods=['POST'])
def activate():
    d = request.get_json(silent=True) or {}
    u, p, key = d.get('username', '').strip(), d.get('password', ''), d.get('license_key', '').strip()
    db = get_db()
    r = db.execute('SELECT * FROM users WHERE username=?', (u,)).fetchone()
    db.close()
    if not r or not check_password_hash(r['password_hash'], p):
        return jsonify({'ok': False, 'error': '用户名或密码错误'}), 401
    expected = 'PAYNET-' + u.upper() + '-2026'  # 演示授权码规则，实际由管理员发放
    if key != expected:
        return jsonify({'ok': False, 'error': '授权码无效'}), 400
    db = get_db()
    db.execute('UPDATE users SET license_key=?, license_activated_at=?, tier=? WHERE id=?',
               (key, datetime.now().isoformat(), 'max', r['id']))
    db.commit()
    db.close()
    return jsonify({'ok': True, 'token': create_token(r['id']), 'message': '激活成功'})


@app.route('/api/auth/status')
@auth_required
def auth_status():
    return jsonify({'ok': True, 'user': g.user['username'], 'licensed': True})


# ---------------- 仪表盘 API（均需授权） ----------------
@app.route('/api/overview')
@auth_required
def overview():
    dd = latest_data_dir()
    sent = read_json(latest_file('sentiment_*.json')) or {}
    pos = compute_positions()
    return jsonify({
        'data_date': os.path.basename(dd) if dd else None,
        'data_dir_mtime': mtime_str(dd) if dd else None,
        'daily_report_time': mtime_str(latest_file('daily_report_*.md')),
        'ai_screening_time': mtime_str(latest_file('ai_screening_*.md')),
        'news_sentiment_time': mtime_str(latest_file('news_sentiment_*.md')),
        'sentiment_time': mtime_str(latest_file('sentiment_*.json')),
        'sentiment_score': sent.get('score'),
        'sentiment_level': sent.get('level'),
        'sentiment_advice': sent.get('advice'),
        'positions_count': pos['count'],
        'total_market_value': pos['total_market_value'],
        'total_pnl': pos['total_pnl'],
        'python_exe': STATE['python_exe'],
        'running': STATE['running'],
        'user': g.user['username'],
    })


@app.route('/api/daily_report')
@auth_required
def daily_report():
    f = latest_file('daily_report_*.md')
    return jsonify({'content': read_text(f), 'time': mtime_str(f)})


@app.route('/api/ai_screening')
@auth_required
def ai_screening():
    f = latest_file('ai_screening_*.md')
    return jsonify({'content': read_text(f), 'time': mtime_str(f)})


@app.route('/api/news_sentiment')
@auth_required
def news_sentiment():
    f = latest_file('news_sentiment_*.md')
    return jsonify({'content': read_text(f), 'time': mtime_str(f)})


@app.route('/api/sentiment')
@auth_required
def sentiment():
    return jsonify(read_json(latest_file('sentiment_*.json')) or {})


@app.route('/api/sentiment_report')
@auth_required
def sentiment_report():
    f = latest_file('sentiment_report_*.md')
    return jsonify({'content': read_text(f), 'time': mtime_str(f)})


@app.route('/api/positions')
@auth_required
def positions():
    return jsonify(compute_positions())


@app.route('/api/scan')
@auth_required
def scan():
    dd = latest_data_dir()
    p = os.path.join(dd, 'daily_scan_results.csv') if dd else None
    h, r = read_csv_rows(p)
    return jsonify({'header': h, 'rows': r, 'time': mtime_str(p)})


@app.route('/api/north')
@auth_required
def north():
    dd = latest_data_dir()
    p = os.path.join(dd, 'north_flow_summary.csv') if dd else None
    h, r = read_csv_rows(p)
    hp = os.path.join(dd, 'north_flow_hist.csv') if dd else None
    hh, hr = read_csv_rows(hp, 60)
    return jsonify({'summary_header': h, 'summary_rows': r, 'hist_header': hh, 'hist_rows': hr, 'time': mtime_str(p)})


@app.route('/api/lhb')
@auth_required
def lhb():
    dd = latest_data_dir()
    p = os.path.join(dd, 'lhb_data.csv') if dd else None
    h, r = read_csv_rows(p)
    return jsonify({'header': h, 'rows': r, 'time': mtime_str(p)})


@app.route('/api/reports')
@auth_required
def reports():
    files = []
    for pat in ['reports/*.html', 'data/*/*.html']:
        for f in glob.glob(os.path.join(BASE_DIR, pat)):
            try:
                files.append({'name': os.path.basename(f),
                              'path': os.path.relpath(f, BASE_DIR).replace('\\', '/'),
                              'time': mtime_str(f), 'size': os.path.getsize(f)})
            except Exception:
                pass
    files.sort(key=lambda x: x.get('time') or '', reverse=True)
    return jsonify({'files': files})


@app.route('/api/report')
@auth_required
def report():
    rel = request.args.get('p', '')
    full = os.path.normpath(os.path.join(BASE_DIR, rel))
    bn = os.path.normpath(BASE_DIR)
    if not full.startswith(bn + os.sep) and full != bn:
        abort(403)
    if not os.path.isfile(full):
        abort(404)
    return send_from_directory(os.path.dirname(full), os.path.basename(full))


@app.route('/api/modules')
@auth_required
def modules():
    return jsonify({'modules': dict(MODULES), 'running': STATE['running'],
                    'last_refresh': STATE['last_refresh'], 'python_exe': STATE['python_exe']})


@app.route('/api/config', methods=['GET', 'POST'])
@auth_required
def config():
    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        if 'python_exe' in d:
            STATE['python_exe'] = d['python_exe']
            try:
                os.makedirs(os.path.dirname(PREF_FILE), exist_ok=True)
                with open(PREF_FILE, 'w', encoding='utf-8') as f:
                    json.dump({'python_exe': d['python_exe']}, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        return jsonify({'ok': True, 'python_exe': STATE['python_exe']})
    return jsonify({'python_exe': STATE['python_exe']})


@app.route('/api/refresh/<module>', methods=['POST'])
@auth_required
def refresh(module):
    if module not in MODULES:
        return jsonify({'ok': False, 'error': '未知模块'}), 400
    if STATE['running'].get(module):
        return jsonify({'ok': False, 'error': '正在运行中'}), 409
    if not os.path.isfile(STATE['python_exe']):
        return jsonify({'ok': False, 'error': f'python 未找到:{STATE["python_exe"]}'}), 400
    threading.Thread(target=run_refresh, args=(module,), daemon=True).start()
    return jsonify({'ok': True, 'message': f'{module} 开始运行'})


@app.route('/api/refresh_status')
@auth_required
def refresh_status():
    return jsonify({'running': STATE['running'], 'last_refresh': STATE['last_refresh'], 'logs': STATE['last_log']})


@app.route('/api/screener')
@auth_required
def screener():
    path = os.path.join(BASE_DIR, 'screener_result.json')
    data = read_json(path) or {'ok': False, 'error': '暂无选股研究数据，请先点「刷新选股研究」生成'}
    tier = g.user['tier'] or 'free'
    if data.get('ok'):
        stocks = data.get('stocks', [])
        if tier == 'free':
            data['stocks'] = stocks[:3]        # 免费版：仅前3只，无AI分析
            data['analysis'] = None
        elif tier == 'pro':
            data['stocks'] = stocks[:10]       # Pro：前10只+分析
        # max：全部+分析+市场统计
    data['tier'] = tier
    data['user'] = g.user['username']
    return jsonify(data)


@app.route('/api/screener/pick', methods=['POST'])
@auth_required
def screener_pick():
    d = request.get_json(silent=True) or {}
    q = d.get('query', '').strip()
    if not q:
        return jsonify({'ok': False, 'error': '请输入选股研究条件'}), 400
    try:
        import ifind_data
        if ifind_data.is_available():
            result, err = ifind_data.smart_pick(q)
            if err:
                return jsonify({'ok': False, 'error': f'iFinD 调用失败: {err}'}), 500
            return jsonify({'ok': True, 'result': result, 'query': q,
                            'disclaimer': '研究参考，不构成投资建议或买卖推荐。'})
        return jsonify({'ok': False, 'error': 'iFinD 未配置（需填 ifind_refresh_token）'}), 503
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/backtest')
@auth_required
def backtest():
    data = read_json(os.path.join(BASE_DIR, 'backtest_result.json')) or {'ok': False, 'error': '暂无回测结果，请先跑 backtest_local.py'}
    return jsonify(data)


@app.route('/api/auth/me')
@auth_required
def auth_me():
    return jsonify({'ok': True, 'user': g.user['username'],
                    'tier': g.user['tier'] or 'free', 'licensed': True})


def admin_required(f):
    @wraps(f)
    def w(*a, **kw):
        tok = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
        if not tok:
            return jsonify({'error': '未登录'}), 401
        u = get_user_by_token(tok)
        if not u:
            return jsonify({'error': 'token 无效'}), 401
        if not u['license_activated_at']:
            return jsonify({'error': '未授权'}), 403
        if u['username'] != 'admin':
            return jsonify({'error': '仅管理员可访问'}), 403
        g.user = u
        return f(*a, **kw)
    return w


@app.route('/api/admin/users')
@admin_required
def admin_users():
    db = get_db()
    users = [dict(u) for u in db.execute(
        'SELECT id,username,license_key,license_activated_at,tier,created_at FROM users ORDER BY id').fetchall()]
    db.close()
    return jsonify({'users': users, 'count': len(users)})


@app.route('/api/admin/license', methods=['POST'])
@admin_required
def admin_license():
    d = request.get_json(silent=True) or {}
    username = d.get('username', '').strip()
    if not username:
        return jsonify({'ok': False, 'error': '需 username'}), 400
    license_key = 'PAYNET-' + username.upper() + '-2026'
    return jsonify({'ok': True, 'license_key': license_key, 'username': username,
                    'instruction': '把此授权码给客户，客户登录后在激活页输入'})


@app.route('/api/admin/tier', methods=['POST'])
@admin_required
def admin_tier():
    d = request.get_json(silent=True) or {}
    uid = d.get('user_id')
    tier = d.get('tier', 'free')
    if tier not in ('free', 'pro', 'max'):
        return jsonify({'ok': False, 'error': 'tier 无效（free/pro/max）'}), 400
    db = get_db()
    db.execute('UPDATE users SET tier=? WHERE id=?', (tier, uid))
    db.commit(); db.close()
    return jsonify({'ok': True, 'user_id': uid, 'tier': tier})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=51888, debug=False)
