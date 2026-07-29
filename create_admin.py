# -*- coding: utf-8 -*-
"""创建/重置 admin 管理员账号（username=admin, tier=max）
跑：python create_admin.py  → admin/admin123
admin 账号可访问 /api/admin/* 管理用户/发license/改tier
"""
import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime

db = sqlite3.connect(r'D:\dbtest\paynet\users.db')
h = generate_password_hash('admin123', method='pbkdf2:sha256', salt_length=16)
try:
    db.execute("INSERT INTO users(username,password_hash,tier,license_activated_at,created_at) VALUES(?,?,?,?,?)",
               ('admin', h, 'max', datetime.now().isoformat(), datetime.now().isoformat()))
    db.commit()
    print('admin 用户创建成功: admin / admin123 (tier=max)')
except sqlite3.IntegrityError:
    db.execute("UPDATE users SET password_hash=?, tier='max', license_activated_at=? WHERE username='admin'",
               (h, datetime.now().isoformat()))
    db.commit()
    print('admin 用户已存在，已重置: admin / admin123 (tier=max)')
db.close()
