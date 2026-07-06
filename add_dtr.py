import sqlite3

conn = sqlite3.connect("database.db")

cursor = conn.cursor()

cursor.execute("""

INSERT INTO dtr(

employee_id,

month,

image

)

VALUES(

?,

?,

?

)

""",

(

"1001",

"June 2026",

"uploads/1001_JUNE2026.png"

)

)

conn.commit()

conn.close()

print("DTR Added.")