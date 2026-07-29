# -*- coding: utf-8 -*-
"""独立进程生成 demo token（绕过 server 进程 sqlite 写卡），写 _token.txt"""
import sqlite3, uuid
from datetime import datetime
db = sqlite3.connect(r'D:\dbtest\paynet\users.db')
token = uuid.uuid4().hex
uid = db.execute("SELECT id FROM users WHERE username='demo'").fetchone()[0]
db.execute("INSERT INTO sessions(token,user_id,created_at) VALUES(?,?,?)",
           (token, uid, datetime.now().isoformat()))
db.commit()
db.close()
with open(r'D:\dbtest\paynet\_token.txt', 'w') as f:
    f.write(token)
print('token:', token)
