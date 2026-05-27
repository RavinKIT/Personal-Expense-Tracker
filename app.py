from flask import Flask, render_template, request, redirect, session, send_file, flash
import sqlite3
import io
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "supersecretkey"


# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT UNIQUE,
        password TEXT,
        monthly_budget REAL DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        amount REAL,
        category TEXT,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()
@app.route("/set_budget", methods=["POST"])
def set_budget():

    if "user_id" not in session:
        return redirect("/login")

    budget = request.form["budget"]

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute(
        "UPDATE users SET monthly_budget=? WHERE id=?",
        (budget, session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")


# ---------- HOME ----------
@app.route("/")
def home():
    if "user_id" in session:
        return redirect("/dashboard")
    return redirect("/login")


# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    error = ""

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        if len(password) < 4:
            error = "Password must be at least 4 characters"
            return render_template("register.html", error=error)

        hashed = generate_password_hash(password)

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO users(username,email,password) VALUES(?,?,?)",
                (username, email, hashed)
            )
            conn.commit()
            conn.close()
            return redirect("/login")
        except:
            conn.close()
            error = "Email already exists"

    return render_template("register.html", error=error)


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session["user_id"] = user[0]
            session["username"] = user[1]
            return redirect("/dashboard")
        else:
            error = "Invalid login details"

    return render_template("login.html", error=error)


# ---------- FORGOT PASSWORD ----------
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    error = ""
    message = ""

    if request.method == "POST":
        email = request.form["email"]
        username = request.form["username"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            return render_template("forgot_password.html", error="Passwords do not match")

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE email=? AND username=?",
            (email, username)
        )

        user = cur.fetchone()

        if user:
            hashed = generate_password_hash(new_password)

            cur.execute(
                "UPDATE users SET password=? WHERE id=?",
                (hashed, user[0])
            )

            conn.commit()
            conn.close()

            message = "Password updated successfully"
        else:
            conn.close()
            error = "Invalid email or username"

    return render_template("forgot_password.html", error=error, message=message)


# ---------- DASHBOARD ----------
# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    # TOTAL SPENT
    cur.execute(
        "SELECT IFNULL(SUM(amount),0) FROM expenses WHERE user_id=?",
        (session["user_id"],)
    )
    total_spent = cur.fetchone()[0]

    # MONTHLY TOTAL
    cur.execute("""
        SELECT IFNULL(SUM(amount),0)
        FROM expenses
        WHERE user_id=?
        AND strftime('%Y-%m', date)=strftime('%Y-%m','now')
    """, (session["user_id"],))

    monthly_total = cur.fetchone()[0]

    # TOP CATEGORY
    cur.execute("""
        SELECT category, SUM(amount)
        FROM expenses
        WHERE user_id=?
        GROUP BY category
        ORDER BY SUM(amount) DESC
        LIMIT 1
    """, (session["user_id"],))

    top = cur.fetchone()
    top_category = top[0] if top else "None"

    # RECENT TRANSACTIONS
    cur.execute("""
        SELECT title, amount, category
        FROM expenses
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 5
    """, (session["user_id"],))

    recent_expenses = cur.fetchall()

    # STATUS
    if monthly_total <= 2000:
        status = "Good"

    elif monthly_total <= 5000:
        status = "Average"

    else:
        status = "High Spend"

    # BUDGET
    cur.execute(
        "SELECT monthly_budget FROM users WHERE id=?",
        (session["user_id"],)
    )

    budget_row = cur.fetchone()

    if budget_row:
        monthly_budget = budget_row[0]
    else:
        monthly_budget = 0

    remaining_budget = monthly_budget - monthly_total

    # BUDGET %
    budget_percent = 0

    if monthly_budget > 0:
        budget_percent = int((monthly_total / monthly_budget) * 100)

    if budget_percent > 100:
        budget_percent = 100

    conn.close()

    return render_template(
        "dashboard.html",
        username=session["username"],
        total_spent=total_spent,
        monthly_total=monthly_total,
        top_category=top_category,
        status=status,
        monthly_budget=monthly_budget,
        remaining_budget=remaining_budget,
        budget_percent=budget_percent,
        recent_expenses=recent_expenses
    )
# ---------- RECORDS ----------
@app.route("/records")
def records():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM expenses WHERE user_id=? ORDER BY id DESC", (session["user_id"],))
    expenses = cur.fetchall()

    conn.close()

    return render_template("records.html", expenses=expenses)


# ---------- ADD ----------
@app.route("/add", methods=["GET", "POST"])
def add():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO expenses(user_id,title,amount,category,date)
        VALUES(?,?,?,?,?)
        """, (
            session["user_id"],
            request.form["title"],
            request.form["amount"],
            request.form["category"],
            request.form["date"]
        ))

        conn.commit()
        conn.close()

        return redirect("/records")

    return render_template("add.html")


# ---------- EDIT ----------
@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
def edit(expense_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    if request.method == "POST":
        cur.execute("""
        UPDATE expenses
        SET title=?, amount=?, category=?, date=?
        WHERE id=? AND user_id=?
        """, (
            request.form["title"],
            request.form["amount"],
            request.form["category"],
            request.form["date"],
            expense_id,
            session["user_id"]
        ))
        conn.commit()
        conn.close()
        return redirect("/records")

    cur.execute("SELECT * FROM expenses WHERE id=? AND user_id=?", (expense_id, session["user_id"]))
    expense = cur.fetchone()
    conn.close()

    return render_template("edit.html", expense=expense)


# ---------- DELETE ----------
@app.route("/delete/<int:expense_id>")
def delete(expense_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (expense_id, session["user_id"]))
    conn.commit()
    conn.close()

    return redirect("/records")


# ---------- PDF ----------
@app.route("/download-pdf")
def download_pdf():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT title, amount, category, date FROM expenses WHERE user_id=?", (session["user_id"],))
    expenses = cur.fetchall()
    conn.close()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)

    y = 800
    for row in expenses:
        pdf.drawString(40, y, f"{row[0]} | {row[1]} | {row[2]} | {row[3]}")
        y -= 20

    pdf.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="report.pdf", mimetype="application/pdf")


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
# ---------- ANALYSIS ----------
@app.route("/analysis")
def analysis():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT category, SUM(amount)
    FROM expenses
    WHERE user_id=?
    GROUP BY category
    """, (session["user_id"],))
    category_data = cur.fetchall()

    cur.execute("""
    SELECT strftime('%Y-%m', date), SUM(amount)
    FROM expenses
    WHERE user_id=?
    GROUP BY strftime('%Y-%m', date)
    ORDER BY strftime('%Y-%m', date)
    """, (session["user_id"],))
    monthly_data = cur.fetchall()

    conn.close()

    return render_template(
        "analysis.html",
        category_data=category_data,
        monthly_data=monthly_data
    )

if __name__ == "__main__":
    app.run(debug=True)