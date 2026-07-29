# -*- coding: utf-8 -*-
"""
paynet 量化仪表盘后端
聚合所有分析结果，提供统一 API 与一键刷新能力。
- 读缓存：纯标准库读取各结果文件，零外部依赖，打开即看。
- 刷新：subprocess 调用老板机器上的 3.11.9 python 跑现有脚本（需 akshare/openai）。
"""
import os, sys, json, csv, glob, subprocess, threading
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, abort

def _resolve_base_dir():
    """打包后：优先 exe 同目录；若没有 data/，向上找含 data/ 的目录。"""
    if getattr(sys, 'frozen', False):
        d = os.path.dirname(sys.executable)
        for _ in range(4):
            if os.path.isdir(os.path.join(d, 'data')):
                return d
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# 运行模式：源码运行 / PyInstaller 打包运行
if getattr(sys, 'frozen', False):
    BASE_DIR = _resolve_base_dir()                     # 项目数据目录(含 data/)
    RESOURCE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))  # 打包资源(dashboard.html)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = BASE_DIR

CONFIG_FILE = os.path.join(BASE_DIR, '.quant', 'config.json')
PREF_FILE = os.path.join(BASE_DIR, '.quant', 'dashboard_prefs.json')
DEFAULT_PY = r"C:\Users\sendy322\AppData\Local\Programs\Python\Python311\python.exe"

# 可刷新模块 -> 对应脚本
MODULES = {
    'daily_scan': 'daily_scan.py',
    'money_tracker': 'money_tracker.py',
    'sentiment': 'sentiment_monitor.py',
    'ai_screening': 'ai_stock_screener.py',
    'news_sentiment': 'news_sentiment.py',
    'daily_workflow': 'daily_workflow.py',
}

app = Flask(__name__, static_folder=None)
STATE = {'python_exe': DEFAULT_PY, 'running': {}, 'last_refresh': {}, 'last_log': {}}


def load_prefs():
    try:
        with open(PREF_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_prefs(d):
    try:
        os.makedirs(os.path.dirname(PREF_FILE), exist_ok=True)
        with open(PREF_FILE, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


STATE['python_exe'] = load_prefs().get('python_exe', DEFAULT_PY)


def latest_file(pattern):
    files = glob.glob(os.path.join(BASE_DIR, pattern))
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def read_text(path):
    if not path:
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f'(读取失败: {e})'


def read_json(path):
    if not path:
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def latest_data_dir():
    sub = [d for d in glob.glob(os.path.join(BASE_DIR, 'data', '*')) if os.path.isdir(d)]
    if not sub:
        return None
    sub.sort(key=os.path.getmtime, reverse=True)
    return sub[0]


def read_csv_rows(path, max_rows=300):
    if not path or not os.path.isfile(path):
        return [], []
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header, rows = [], []
            for i, row in enumerate(reader):
                if i == 0:
                    header = row
                    continue
                if i > max_rows:
                    break
                rows.append(row)
            return header, rows
    except Exception:
        return [], []


def mtime_str(path):
    if not path:
        return None
    try:
        return datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return None


def compute_positions():
    trades = read_json(os.path.join(BASE_DIR, 'paper_trades.json')) or []
    pos = {}
    for t in trades:
        code = t.get('code', '')
        p = pos.setdefault(code, {'code': code, 'name': t.get('name', ''),
                                  'qty': 0, 'cost_total': 0.0, 'last_price': 0.0})
        if t.get('name'):
            p['name'] = t['name']
        action = t.get('action')
        qty = t.get('shares', 0) or 0
        price = t.get('price', 0) or 0
        if action == 'BUY':
            p['cost_total'] += qty * price
            p['qty'] += qty
            p['last_price'] = price
        elif action == 'SELL':
            p['qty'] -= qty
            p['last_price'] = price  # 用最近一次成交价作参考价
    positions = []
    for code, p in pos.items():
        if p['qty'] > 0:
            avg = p['cost_total'] / p['qty'] if p['qty'] else 0
            last = p['last_price'] or avg
            pnl = (last - avg) * p['qty']
            pct = (last - avg) / avg * 100 if avg else 0
            positions.append({
                'code': code, 'name': p['name'], 'qty': p['qty'],
                'avg_cost': round(avg, 2), 'last_price': round(last, 2),
                'market_value': round(last * p['qty'], 2),
                'pnl': round(pnl, 2), 'pnl_pct': round(pct, 2),
            })
    history = sorted(trades, key=lambda x: x.get('time', ''), reverse=True)
    total_mv = sum(x['market_value'] for x in positions)
    total_pnl = sum(x['pnl'] for x in positions)
    return {'positions': positions, 'history': history,
            'total_market_value': round(total_mv, 2),
            'total_pnl': round(total_pnl, 2), 'count': len(positions)}


# ---------------- routes ----------------
@app.route('/')
def index():
    return send_from_directory(RESOURCE_DIR, 'dashboard.html')


@app.route('/api/overview')
def overview():
    dd = latest_data_dir()
    sent = read_json(latest_file('sentiment_*.json')) or {}
    positions = compute_positions()
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
        'positions_count': positions['count'],
        'total_market_value': positions['total_market_value'],
        'total_pnl': positions['total_pnl'],
        'python_exe': STATE['python_exe'],
        'running': STATE['running'],
    })


@app.route('/api/daily_report')
def daily_report():
    f = latest_file('daily_report_*.md')
    return jsonify({'content': read_text(f), 'time': mtime_str(f)})


@app.route('/api/ai_screening')
def ai_screening():
    f = latest_file('ai_screening_*.md')
    return jsonify({'content': read_text(f), 'time': mtime_str(f)})


@app.route('/api/news_sentiment')
def news_sentiment():
    f = latest_file('news_sentiment_*.md')
    return jsonify({'content': read_text(f), 'time': mtime_str(f)})


@app.route('/api/sentiment')
def sentiment():
    return jsonify(read_json(latest_file('sentiment_*.json')) or {})


@app.route('/api/sentiment_report')
def sentiment_report():
    f = latest_file('sentiment_report_*.md')
    return jsonify({'content': read_text(f), 'time': mtime_str(f)})


@app.route('/api/positions')
def positions():
    return jsonify(compute_positions())


@app.route('/api/scan')
def scan():
    dd = latest_data_dir()
    p = os.path.join(dd, 'daily_scan_results.csv') if dd else None
    h, r = read_csv_rows(p)
    return jsonify({'header': h, 'rows': r, 'time': mtime_str(p)})


@app.route('/api/north')
def north():
    dd = latest_data_dir()
    p = os.path.join(dd, 'north_flow_summary.csv') if dd else None
    h, r = read_csv_rows(p)
    hp = os.path.join(dd, 'north_flow_hist.csv') if dd else None
    hh, hr = read_csv_rows(hp, max_rows=60)
    return jsonify({'summary_header': h, 'summary_rows': r,
                    'hist_header': hh, 'hist_rows': hr, 'time': mtime_str(p)})


@app.route('/api/lhb')
def lhb():
    dd = latest_data_dir()
    p = os.path.join(dd, 'lhb_data.csv') if dd else None
    h, r = read_csv_rows(p)
    return jsonify({'header': h, 'rows': r, 'time': mtime_str(p)})


@app.route('/api/reports')
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
def report():
    rel = request.args.get('p', '')
    full = os.path.normpath(os.path.join(BASE_DIR, rel))
    base_n = os.path.normpath(BASE_DIR)
    if not full.startswith(base_n + os.sep) and full != base_n:
        abort(403)
    if not os.path.isfile(full):
        abort(404)
    return send_from_directory(os.path.dirname(full), os.path.basename(full))


@app.route('/api/modules')
def modules():
    return jsonify({'modules': dict(MODULES), 'running': STATE['running'],
                    'last_refresh': STATE['last_refresh'], 'python_exe': STATE['python_exe']})


@app.route('/api/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        if 'python_exe' in data:
            STATE['python_exe'] = data['python_exe']
            save_prefs({'python_exe': data['python_exe']})
        return jsonify({'ok': True, 'python_exe': STATE['python_exe']})
    cand = []
    for py in [STATE['python_exe'], DEFAULT_PY]:
        if py and os.path.isfile(py) and py not in cand:
            cand.append(py)
    info = {}
    for py in cand:
        ver, ok = '', False
        try:
            r = subprocess.run([py, '--version'], capture_output=True, text=True, timeout=10)
            ver = (r.stdout or r.stderr).strip()
            r2 = subprocess.run([py, '-c', 'import akshare,openai,pandas; print("ok")'],
                                 capture_output=True, text=True, timeout=25)
            ok = 'ok' in (r2.stdout or '')
        except Exception:
            ok = False
        info[py] = {'version': ver, 'has_akshare': ok}
    return jsonify({'python_exe': STATE['python_exe'], 'candidates': info})


def run_refresh(module):
    script = MODULES.get(module)
    STATE['running'][module] = True
    STATE['last_log'][module] = '运行中...\n'
    try:
        proc = subprocess.run([STATE['python_exe'], script], cwd=BASE_DIR,
                              capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=600)
        log = (proc.stdout or '') + (('\n[stderr]\n' + proc.stderr) if proc.stderr else '')
        STATE['last_log'][module] = log[-5000:] or '(无输出)'
        STATE['last_refresh'][module] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    except subprocess.TimeoutExpired:
        STATE['last_log'][module] = '超时(>600s)'
    except FileNotFoundError as e:
        STATE['last_log'][module] = f'python 未找到: {e}'
    except Exception as e:
        STATE['last_log'][module] = f'错误: {e}'
    finally:
        STATE['running'][module] = False


@app.route('/api/refresh/<module>', methods=['POST'])
def refresh(module):
    if module not in MODULES:
        return jsonify({'ok': False, 'error': '未知模块'}), 400
    if STATE['running'].get(module):
        return jsonify({'ok': False, 'error': '正在运行中'}), 409
    if not os.path.isfile(STATE['python_exe']):
        return jsonify({'ok': False, 'error': f'python 未找到: {STATE["python_exe"]}, 请到设置配置正确路径'}), 400
    threading.Thread(target=run_refresh, args=(module,), daemon=True).start()
    return jsonify({'ok': True, 'message': f'{module} 开始运行'})


@app.route('/api/refresh_status')
def refresh_status():
    return jsonify({'running': STATE['running'],
                    'last_refresh': STATE['last_refresh'],
                    'logs': STATE['last_log']})


@app.route('/api/debug')
def debug_api():
    import os as _o
    pt = os.path.join(BASE_DIR, 'paper_trades.json')
    return jsonify({
        'BASE_DIR': BASE_DIR, 'RESOURCE_DIR': RESOURCE_DIR, 'cwd': _o.getcwd(),
        'frozen': getattr(sys, 'frozen', False),
        'base_listing': _o.listdir(BASE_DIR)[:25],
        'sentiment_glob': glob.glob(os.path.join(BASE_DIR, 'sentiment_*.json')),
        'paper_trades_exists': os.path.isfile(pt),
        'data_exists': os.path.isdir(os.path.join(BASE_DIR, 'data')),
    })


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=False)
