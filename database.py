import sqlite3

conn = sqlite3.connect("database.db")

cursor = conn.cursor()

# ==========================
# EMPLOYEES TABLE
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS employees(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    employee_id TEXT UNIQUE,

    name TEXT,

    passcode TEXT

)
""")

# ==========================
# DTR TABLE
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS dtr(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    employee_id TEXT,

    month TEXT,

    image TEXT

)
""")

conn.commit()

conn.close()

print("Database Created Successfully.")