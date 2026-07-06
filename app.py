from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    url_for,
    jsonify
)
import os
import psycopg2
from psycopg2.extras import RealDictCursor

import database

from flask import send_from_directory
UPLOAD_FOLDER = "uploads"

app = Flask(__name__)
app.secret_key = "TMENHS_SECRET_2026"

UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ============================
# DATABASE CONNECTION
# ============================
DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db():

    conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )

    return conn
# ============================
# HOME
# ============================
@app.route("/")
def home():
    return render_template("index.html")


# ============================
# EMPLOYEE LOGIN
# ============================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        employee_id = request.form["employee_id"].strip()
        passcode = request.form["passcode"].strip()

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM employees
            WHERE employee_id=%s
            AND passcode=%s
        """, (employee_id, passcode))

        employee = cur.fetchone()

        conn.close()

        if employee:

            session["employee"] = employee["employee_id"]
            session["name"] = employee["name"]

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid Employee ID or Passcode."
        )

    return render_template("login.html")


# ============================
# DASHBOARD
# ============================
@app.route("/dashboard")
def dashboard():

    if "employee" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM dtr
        WHERE employee_id=%s
        ORDER BY month DESC
    """, (session["employee"],))

    dtrs = cur.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        employee_id=session["employee"],
        name=session["name"],
        dtrs=dtrs
    )

# ============================
# LOGOUT
# ============================
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))
# ============================
@app.route("/check_db")
def check_db():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""

    SELECT table_name

    FROM information_schema.tables

    WHERE table_schema='public'

    """)

    tables = cur.fetchall()

    conn.close()

    return jsonify(tables)

# ============================
# API - AUTO UPLOAD PNG
# ============================
@app.route("/api/upload", methods=["POST"])
def upload_png():

    try:

        employee_id = request.form["employee_id"].strip()
        employee_name = request.form["employee_name"].strip()
        month = request.form["month"].strip()

        image = request.files["image"]

        filename = image.filename

        save_path = os.path.join(UPLOAD_FOLDER, filename)
        image.save(save_path)

        filepath = f"uploads/{filename}"

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT id
            FROM employees
            WHERE employee_id=%s
        """, (employee_id,))

        emp = cur.fetchone()

        if emp is None:

            cur.execute("""
                INSERT INTO employees(
                    employee_id,
                    name,
                    passcode
                )
                VALUES(%s,%s,%s)
            """, (
                employee_id,
                employee_name,
                employee_id
            ))

        else:

            cur.execute("""
                UPDATE employees
                SET name=%s
                WHERE employee_id=%s
            """, (
                employee_name,
                employee_id
            ))

        cur.execute("""
            SELECT id
            FROM dtr
            WHERE employee_id=%s
            AND month=%s
        """, (employee_id, month))

        existing = cur.fetchone()

        if existing:

            cur.execute("""
                UPDATE dtr
                SET image=%s
                WHERE employee_id=%s
                AND month=%s
            """, (
                filepath,
                employee_id,
                month
            ))

        else:

            cur.execute("""
                INSERT INTO dtr(
                    employee_id,
                    month,
                    image
                )
                VALUES(%s,%s,%s)
            """, (
                employee_id,
                month,
                filepath
            ))

        conn.commit()
        conn.close()

        return jsonify({"status":"success"})

    except Exception as e:

        import traceback

        traceback.print_exc()

        return jsonify({
            "status":"error",
            "message":str(e)
        }),500

# ============================
# RUN SERVER
# ============================
if __name__ == "__main__":
    app.run(debug=True)