import sqlite3
conn = sqlite3.connect('aegisvoice.db')
cur = conn.cursor()
cur.execute('SELECT id, name FROM beneficiaries')
rows = cur.fetchall()
for r in rows:
  print(r[0], type(r[0]))
