# -*- coding: utf-8 -*-
"""重设 demo 密码为 pbkdf2（scrypt 在 sandbox 下 verify 极慢）"""
import sqlite3
from werkzeug.security import generate_password_hash
db = sqlite3.connect(r'D:\dbtest\paynet\users.db')
h = generate_password_hash('demo123', method='pbkdf2:sha256', salt_length=16)
db.execute("UPDATE users SET password_hash=? WHERE username='demo'", (h,))
db.commit()
db.close()
print('demo password reset to pbkdf2 (fast verify)')
