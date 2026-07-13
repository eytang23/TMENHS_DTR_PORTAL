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

import cloudinary
import cloudinary.uploader

from flask import send_file
import requests
from io import BytesIO

import database
from dotenv import load_dotenv
from flask import flash

load_dotenv()

from flask import send_from_directory
UPLOAD_FOLDER = "uploads"

app = Flask(__name__)
app.secret_key = "TMENHS_SECRET_2026"

# ============================
# LIVE UPLOAD STATUS
# ============================
upload_status = {
    "running": False,
    "current_employee": "",
    "completed": 0,
    "total": 0,
    "progress": 0,
    "finished": False
}

# ============================
# API - LIVE UPLOAD STATUS
# ============================
@app.route("/api/upload-status")
def get_upload_status():

    return jsonify(upload_status)

# ============================
# API - UPDATE LIVE STATUS
# ============================
@app.route("/api/update-upload-status", methods=["POST"])
def update_upload_status():

    data = request.get_json()

    upload_status["running"] = data.get("running", False)
    upload_status["current_employee"] = data.get("current_employee", "")
    upload_status["completed"] = data.get("completed", 0)
    upload_status["total"] = data.get("total", 0)
    upload_status["progress"] = data.get("progress", 0)
    upload_status["finished"] = data.get("finished", False)
    upload_status["month"] = data.get("month", "")

    return jsonify({
        "status": "success"
    })

UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

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

        filepath = request.form["image_url"].strip()

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
    
@app.route("/download/<int:dtr_id>")
def download_dtr(dtr_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT image
        FROM dtr
        WHERE id=%s
    """, (dtr_id,))

    dtr = cur.fetchone()
    conn.close()

    if not dtr:
        return "File not found", 404

    response = requests.get(dtr["image"])

    return send_file(
        BytesIO(response.content),
        as_attachment=True,
        download_name="DTR.png",
        mimetype="image/png"
    )

@app.route("/admin/dashboard")
def admin_dashboard():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM employees")
    total_employees = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(DISTINCT month) FROM dtr")
    total_months = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) FROM dtr")
    total_dtr = cur.fetchone()["count"]

    conn.close()

    return render_template(
        "admin/dashboard.html",
        total_employees=total_employees,
        total_months=total_months,
        total_dtr=total_dtr
    )

# ============================
# DTR MANAGEMENT
# ============================
@app.route("/admin/dtr-management")
def dtr_management():

    # Optional: protect admin pages
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            month,
            COUNT(*) AS total_records
        FROM dtr
        GROUP BY month
        ORDER BY month DESC
    """)

    months = cur.fetchall()

    conn.close()

    return render_template(
        "admin/dtr_management.html",
        months=months
    )

# ============================
# ADMIN LOGIN
# ============================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"].strip()

        # Temporary hardcoded admin account
        if username == "admin" and password == "TMENHS2026":

            session["admin"] = username

            return redirect(url_for("admin_dashboard"))

        return render_template(
            "admin/login.html",
            error="Invalid username or password."
        )

    return render_template("admin/login.html")

# ============================
# MANAGE MONTH
# ============================
@app.route("/admin/manage/<month>")
def manage_month(month):

    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) AS total_records
        FROM dtr
        WHERE month=%s
    """, (month,))

    result = cur.fetchone()

    conn.close()

    return render_template(
        "admin/manage_month.html",
        month=month,
        total_records=result["total_records"]
    )

@app.route("/admin/delete-month/<month>", methods=["POST"])
def delete_month(month):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM dtr
        WHERE month=%s
    """, (month,))

    conn.commit()
    conn.close()

    flash(f"{month} deleted successfully.", "success")

    return redirect(url_for("dtr_management"))

# ============================
# RUN SERVER
# ============================
if __name__ == "__main__":
    app.run(debug=True)