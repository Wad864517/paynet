# -*- coding: utf-8 -*-
"""直接设 demo 用户 tier=max（绕过 activate 卡顿测试）"""
import sqlite3
db = sqlite3.connect(r'D:\dbtest\paynet\users.db')
db.execute("UPDATE users SET tier='max', license_activated_at='2026-07-26T21:00:00' WHERE username='demo'")
db.commit()
row = db.execute("SELECT username, tier, license_activated_at FROM users WHERE username='demo'").fetchone()
db.close()
print('demo:', row)
