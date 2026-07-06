from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    url_for,
    jsonify
)

import sqlite3
import os

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
def get_db():

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

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
            WHERE employee_id=?
            AND passcode=?
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
        WHERE employee_id=?
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
# API - AUTO UPLOAD PNG
# ============================
@app.route("/api/upload", methods=["POST"])
def upload_png():

    employee_id = request.form["employee_id"].strip()
    employee_name = request.form["employee_name"].strip()
    month = request.form["month"].strip()

    image = request.files["image"]

    filename = image.filename

    # Physical file location
    save_path = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    image.save(save_path)

    # Ito ang ise-save sa database
    filepath = f"uploads/{filename}"

    conn = get_db()
    cur = conn.cursor()

    # ==========================
    # AUTO CREATE / UPDATE EMPLOYEE
    # ==========================
    cur.execute("""
        SELECT id
        FROM employees
        WHERE employee_id=?
    """, (employee_id,))

    emp = cur.fetchone()

    if emp is None:

        cur.execute("""
            INSERT INTO employees(
                employee_id,
                name,
                passcode
            )
            VALUES(?,?,?)
        """, (
            employee_id,
            employee_name,
            employee_id
        ))

    else:

        cur.execute("""
            UPDATE employees
            SET name=?
            WHERE employee_id=?
        """, (
            employee_name,
            employee_id
        ))

    # ==========================
    # CHECK DTR RECORD
    # ==========================
    cur.execute("""
        SELECT id
        FROM dtr
        WHERE employee_id=?
        AND month=?
    """, (employee_id, month))

    existing = cur.fetchone()

    if existing:

        cur.execute("""
            UPDATE dtr
            SET image=?
            WHERE employee_id=?
            AND month=?
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
            VALUES(?,?,?)
        """, (
            employee_id,
            month,
            filepath
        ))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "employee": employee_name,
        "employee_id": employee_id,
        "month": month,
        "file": filename
    })

# ============================
# RUN SERVER
# ============================
if __name__ == "__main__":
    app.run(debug=True)