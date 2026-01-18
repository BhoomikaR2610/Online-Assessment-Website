from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
import os, uuid
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import base64

app = Flask(__name__)
app.secret_key = "enterprise_secret_key"

# ---------------- CONFIG ----------------
UPLOAD_FOLDER = "static/uploads/photos"
SNAPSHOT_FOLDER = "static/uploads/snapshots"
DATA_FOLDER = "data"
DATA_FILE = os.path.join(DATA_FOLDER, "students.xlsx")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SNAPSHOT_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- CREATE EXCEL ----------------
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=[
        "name", "email", "password",
        "course", "school", "semester",
        "photo", "reset_token"
    ])
    df.to_excel(DATA_FILE, index=False)

# ---------------- REGISTER ----------------
@app.route("/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        df = pd.read_excel(DATA_FILE)
        email = request.form["email"].lower()
        if email in df["email"].values:
            flash("Email already registered")
            return redirect(url_for("register"))

        photo = request.files["photo"]
        if photo.filename == "" or not allowed_file(photo.filename):
            flash("Upload JPG or PNG photo only")
            return redirect(url_for("register"))

        filename = secure_filename(photo.filename)
        filename = f"{uuid.uuid4()}_{filename}"
        photo.save(os.path.join(UPLOAD_FOLDER, filename))

        df.loc[len(df)] = {
            "name": request.form["name"],
            "email": email,
            "password": generate_password_hash(request.form["password"]),
            "course": request.form["course"],
            "school": request.form["school"],
            "semester": request.form["semester"],
            "photo": filename,
            "reset_token": ""
        }

        df.to_excel(DATA_FILE, index=False)
        flash("Registration successful. Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        df = pd.read_excel(DATA_FILE)
        email = request.form["email"].lower()
        password = request.form["password"]
        user = df[df["email"] == email]
        if not user.empty and check_password_hash(user.iloc[0]["password"], password):
            session["email"] = email
            return redirect(url_for("dashboard"))
        flash("Invalid email or password")
    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "email" not in session:
        return redirect(url_for("login"))
    df = pd.read_excel(DATA_FILE)
    user = df[df["email"] == session["email"]].iloc[0]
    return render_template("dashboard.html", user=user)

# ---------------- CONTINUE ----------------
@app.route("/continue")
def continue_page():
    if "email" not in session:
        return redirect(url_for("login"))
    return render_template("continue.html")

# ---------------- ASSESSMENT ----------------
@app.route("/assessment", methods=["GET", "POST"])
def assessment():
    if "email" not in session:
        return redirect(url_for("login"))

    questions = [
        {"id": "1", "question": "What is Python?", "options": ["Language", "Animal", "Car"], "answer": "Language"},
        {"id": "2", "question": "2 + 2 = ?", "options": ["3", "4", "5"], "answer": "4"},
        {"id": "3", "question": "Flask is a ?", "options": ["Framework", "Library", "IDE"], "answer": "Framework"},
        {"id": "4", "question": "HTML stands for?", "options": ["Hyper Text Markup Language","Hot Mail","Hyperlink"], "answer": "Hyper Text Markup Language"},
        {"id": "5", "question": "CSS is used for?", "options": ["Styling","Programming","Database"], "answer": "Styling"},
        {"id": "6", "question": "JS is used for?", "options": ["Logic","Design","Database"], "answer": "Logic"},
    ]
    session["questions"] = questions

    if request.method == "POST":
        answers = {}
        for q in questions:
            ans = request.form.get(q["id"])
            if ans:
                answers[q["id"]] = ans
        session["answers"] = answers
        return redirect(url_for("result"))  # redirect to result.html

    return render_template("assessment.html", questions=questions)

# ---------------- SAVE SNAPSHOT ----------------
@app.route("/save_snapshot", methods=["POST"])
def save_snapshot():
    data = request.json.get("image")
    if data:
        img_data = data.split(",")[1]
        filename = f"{uuid.uuid4()}.png"
        filepath = os.path.join(SNAPSHOT_FOLDER, filename)
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(img_data))
    return "OK"

# ---------------- RESULTS ----------------
@app.route("/result")
def result():
    if "email" not in session or "answers" not in session or "questions" not in session:
        return redirect(url_for("dashboard"))

    questions = session.get("questions", [])
    answers = session.get("answers", {})

    total = len(questions)
    answered = sum(1 for q in questions if q["id"] in answers)
    unanswered = total - answered
    score = sum(1 for q in questions if answers.get(q["id"]) == q["answer"])

    return render_template("result.html", score=score, total=total, answered=answered, unanswered=unanswered)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
