import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL)

cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS employees(

    id SERIAL PRIMARY KEY,

    employee_id VARCHAR(100) UNIQUE,

    name VARCHAR(200),

    passcode VARCHAR(100)

)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS dtr(

    id SERIAL PRIMARY KEY,

    employee_id VARCHAR(100),

    month VARCHAR(20),

    image TEXT

)
""")

conn.commit()
conn.close()

print("PostgreSQL Database Ready")