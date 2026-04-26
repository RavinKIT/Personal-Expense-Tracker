from flask import Flask, render_template, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"


def init_db():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
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


@app.route("/")
def home():
    if "user_id" in session:
        return redirect("/dashboard")
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    error = ""

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO users(username,email,password) VALUES(?,?,?)",
                (username, email, password)
            )
            conn.commit()
            conn.close()
            return redirect("/login")
        except:
            conn.close()
            error = "This email is already registered."

        return render_template(
            "register.html",
            error=error,
            old_name=username,
            old_email=email
        )

    return render_template(
        "register.html",
        error="",
        old_name="",
        old_email=""
    )


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

        if user:
            if check_password_hash(user[3], password):
                session["user_id"] = user[0]
                session["username"] = user[1]
                return redirect("/dashboard")
            else:
                error = "Incorrect password. Try again."
        else:
            error = "No account found with this email."

        return render_template(
            "login.html",
            error=error,
            old_email=email
        )

    return render_template(
        "login.html",
        error="",
        old_email=""
    )


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    message = ""
    error = ""

    if request.method == "POST":
        email = request.form["email"]
        username = request.form["username"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            error = "Passwords do not match."

        else:
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
                message = "Password updated successfully."
            else:
                error = "Email and username do not match records."

            conn.close()

    return render_template(
        "forgot_password.html",
        message=message,
        error=error
    )


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    if request.method == "POST":
        title = request.form["title"]
        amount = request.form["amount"]
        category = request.form["category"]
        date = request.form["date"]

        cur.execute("""
        INSERT INTO expenses(user_id,title,amount,category,date)
        VALUES(?,?,?,?,?)
        """, (session["user_id"], title, amount, category, date))

        conn.commit()

    search = request.args.get("search", "").strip()
    sort = request.args.get("sort", "latest")

    query = """
    SELECT * FROM expenses
    WHERE user_id=? AND
    (
        title LIKE ?
        OR category LIKE ?
        OR date LIKE ?
    )
    """

    if sort == "amount":
        query += " ORDER BY amount DESC"
    elif sort == "category":
        query += " ORDER BY category ASC"
    else:
        query += " ORDER BY id DESC"

    keyword = "%" + search + "%"

    cur.execute(
        query,
        (
            session["user_id"],
            keyword,
            keyword,
            keyword
        )
    )

    expenses = cur.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        expenses=expenses,
        username=session["username"],
        search=search,
        sort=sort
    )


@app.route("/delete/<int:expense_id>")
def delete(expense_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM expenses WHERE id=? AND user_id=?",
        (expense_id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)