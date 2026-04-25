from flask import Flask, render_template, request, redirect
import csv
import os

app = Flask(__name__)

FILE_NAME = "expenses.csv"

if not os.path.exists(FILE_NAME):
    with open(FILE_NAME, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Title", "Amount", "Category", "Date"])

@app.route("/", methods=["GET", "POST"])
def home():
    edit_index = request.args.get("edit")
    search = request.args.get("search", "").lower()

    expenses = []

    with open(FILE_NAME, "r") as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            expenses.append(row)

    edit_data = None

    if edit_index is not None:
        edit_index = int(edit_index)
        edit_data = expenses[edit_index]

    if request.method == "POST":
        title = request.form["title"]
        amount = request.form["amount"]
        category = request.form["category"]
        date = request.form["date"]
        update_index = request.form["edit_index"]

        if update_index == "":
            with open(FILE_NAME, "a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([title, amount, category, date])
        else:
            update_index = int(update_index)
            expenses[update_index] = [title, amount, category, date]

            with open(FILE_NAME, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["Title", "Amount", "Category", "Date"])
                writer.writerows(expenses)

        return redirect("/")

    total = 0
    for row in expenses:
        total += float(row[1])

    filtered_expenses = []

    for row in expenses:
        if search in row[0].lower() or search in row[2].lower():
            filtered_expenses.append(row)

    return render_template(
        "index.html",
        expenses=filtered_expenses,
        edit_data=edit_data,
        edit_index=edit_index,
        total=total,
        search=search
    )

@app.route("/delete/<int:index>")
def delete(index):
    rows = []

    with open(FILE_NAME, "r") as file:
        reader = csv.reader(file)
        rows = list(reader)

    del rows[index + 1]

    with open(FILE_NAME, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(rows)

    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)