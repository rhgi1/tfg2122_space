# Borramos e inicializamos la Base de Datos

import sqlite3

space_db = sqlite3.connect(r"db/space.db")

# Limpiamos la base de datos
print("Eliminando las tablas ... ", end="")
cursor = space_db.cursor()
cursor.execute("DROP TABLE IF EXISTS locations;")
cursor.execute("DROP TABLE IF EXISTS events;")
print("[OK]")

print("Creando la tabla 'locations' ... ", end="")
cursor.execute(""" CREATE TABLE IF NOT EXISTS locations (
                        mac_address text NOT NULL,
                        date text DEFAULT '2000-01-01 00:00:00' NOT NULL,
                        x text,
                        y text,
                        PRIMARY KEY(mac_address, date)
                    ); """)
print("[OK]")

print("Creando la tabla 'events' ... ", end="")
cursor.execute(""" CREATE TABLE IF NOT EXISTS events (
                        mac_address text NOT NULL,
                        date text DEFAULT '2000-01-01 00:00:00' NOT NULL,
                        message text,
                        priority integer DEFAULT 0,
                        PRIMARY KEY(mac_address, date)
); """)
print("[OK]")

cursor.execute(""" CREATE TABLE IF NOT EXISTS bands (
    id text PRIMARY KEY,
    mac_address text,
    extra1 text
); """)

locations = [
    ('FF:FF:FF:FF:FF:FF','2022-01-01 00:00:00','45', '135'),
    ('FF:FF:FF:FF:FF:FF','2022-01-01 00:01:00','45', '135'),
    ('FF:FF:FF:FF:FF:FF','2022-01-01 00:02:00','45', '135'),
    ('FF:FF:FF:FF:FF:FF','2022-01-01 00:03:00','45', '135'),
    ('00:00:00:00:00:00','2022-01-01 00:04:00','45', '135'),
    ('FF:FF:FF:FF:FF:FF','2022-01-01 00:05:00','45', '135'),
    ('00:00:00:00:00:00','2022-01-01 00:06:00','45', '135'),
    ('FF:FF:FF:FF:FF:FF','2022-01-01 00:06:00','45', '135'),
    ('00:00:00:00:00:00','2022-01-01 00:07:00','45', '135'),
    ('FF:FF:FF:FF:FF:FF','2022-01-01 00:08:00','45', '135'),
    ('FF:FF:FF:FF:FF:FF','2022-01-01 00:09:00','45', '135')]

cursor.executemany("INSERT INTO locations VALUES (?, ?, ?, ?)", locations)


events = [
    ('FF:FF:FF:FF:FF:FF','2022-01-01 00:00:00','Caída', 2),
    ('FF:FF:FF:FF:FF:FF','2022-01-01 00:01:00','Entrada', 0),
    ('FF:FF:FF:FF:FF:FF','2022-01-01 00:02:00','Salida', 1),
    ('FF:FF:FF:FF:FF:FF','2022-01-01 00:03:00','BPM inusual', 2),
    ('FF:FF:FF:FF:FF:FF','2022-01-01 00:04:00','Inactivo', 1)]

cursor.executemany("INSERT INTO events VALUES (?, ?, ?, ?)", events)

space_db.commit()

space_db.close()
