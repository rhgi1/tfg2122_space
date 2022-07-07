# Borramos e inicializamos la Base de Datos

import sqlite3

space_db = sqlite3.connect(r"db/space.db")

cursor = space_db.cursor()
cursor.execute("SELECT * FROM locations ORDER BY date DESC LIMIT 1")
rows = cursor.fetchone()

print(rows)