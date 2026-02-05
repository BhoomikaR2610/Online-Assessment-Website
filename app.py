from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
import os, uuid
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "enterprise_secret_key"

# ---------------- CONFIG ----------------
UPLOAD_FOLDER = "static/uploads/photos"
DATA_FOLDER = "data"
DATA_FILE = os.path.join(DATA_FOLDER, "students.xlsx")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- CREATE EXCEL ----------------
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=[
        "name","email","password",
        "course","school","semester",
        "roll_no","photo",
        "assessment_status","score","answers"
    ])
    df.to_excel(DATA_FILE, index=False)

# ---------------- REGISTER ----------------
@app.route("/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        df = pd.read_excel(DATA_FILE)

        email = request.form["email"].lower()
        roll_no_raw = request.form["roll_no"]

        if not roll_no_raw.isdigit():
            flash("Code must be a number")
            return redirect(url_for("register"))

        roll_no = int(roll_no_raw)

        if roll_no < 100 or roll_no > 110:
            flash("Code must be between 100 and 110")
            return redirect(url_for("register"))

        if roll_no in df["roll_no"].values:
            flash("This code is already used")
            return redirect(url_for("register"))

        if email in df["email"].values:
            flash("Email already registered")
            return redirect(url_for("register"))

        photo = request.files["photo"]
        if photo.filename == "" or not allowed_file(photo.filename):
            flash("Upload JPG or PNG photo only")
            return redirect(url_for("register"))

        filename = f"{uuid.uuid4()}_{secure_filename(photo.filename)}"
        photo.save(os.path.join(UPLOAD_FOLDER, filename))

        df.loc[len(df)] = {
            "name": request.form["name"],
            "email": email,
            "password": generate_password_hash(request.form["password"]),
            "course": request.form["course"],
            "school": request.form["school"],
            "semester": request.form["semester"],
            "roll_no": roll_no,
            "photo": filename,
            "assessment_status": "NOT_STARTED",
            "score": 0,
            "answers": "{}"
        }

        df.to_excel(DATA_FILE, index=False)
        flash("Registration successful. Login now.")
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
            session.clear()
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

    return render_template("dashboard.html",
                           user=user,
                           status=user["assessment_status"])

# ---------------- ASSESSMENT ----------------
@app.route("/assessment", methods=["GET", "POST"])
def assessment():
    if "email" not in session:
        return redirect(url_for("login"))

    df = pd.read_excel(DATA_FILE)
    idx = df[df["email"] == session["email"]].index[0]

    if df.at[idx, "assessment_status"] == "COMPLETED":
        return redirect(url_for("result"))

    questions = [
        {"id":"1","question":"What is Python?","options":["Language","Animal","Car"],"answer":"Language"},
        {"id":"2","question":"2 + 2 = ?","options":["3","4","5"],"answer":"4"},
        {"id":"3","question":"Flask is a ?","options":["Framework","Library","IDE"],"answer":"Framework"},
        {"id":"4","question":"HTML stands for?","options":["Hyper Text Markup Language","Hot Mail","Hyperlink"],"answer":"Hyper Text Markup Language"},
        {"id":"5","question":"CSS is used for?","options":["Styling","Programming","Database"],"answer":"Styling"},
        {"id":"6","question":"JS is used for?","options":["Logic","Design","Database"],"answer":"Logic"},
    ]

    if request.method == "GET":
        df.at[idx, "assessment_status"] = "IN_PROGRESS"
        df.to_excel(DATA_FILE, index=False)
        session["questions"] = questions

        # Load previous answers if exist
        answers = eval(df.at[idx, "answers"]) if df.at[idx, "answers"] != "{}" else {}
        session["answers"] = answers

        return render_template("assessment.html", questions=questions, answers=answers)

    # POST - user submitted
    answers = {}
    for q in questions:
        ans = request.form.get(q["id"])
        if ans:
            answers[q["id"]] = ans

    # calculate score
    score = 0
    for q in questions:
        if answers.get(q["id"]) == q["answer"]:
            score += 1

    df.at[idx, "assessment_status"] = "COMPLETED"
    df.at[idx, "score"] = score
    df.at[idx, "answers"] = str(answers)
    df.to_excel(DATA_FILE, index=False)

    return redirect(url_for("result"))

# ---------------- RESULT ----------------
@app.route("/result")
def result():
    if "email" not in session:
        return redirect(url_for("login"))

    df = pd.read_excel(DATA_FILE)
    user = df[df["email"] == session["email"]].iloc[0]

    if user["assessment_status"] != "COMPLETED":
        return redirect(url_for("dashboard"))

    answers = eval(user.get("answers", "{}"))
    total_questions = 6
    answered = len(answers)
    unanswered = total_questions - answered

    return render_template("result.html",
                           score=user["score"],
                           total=total_questions,
                           answered=answered,
                           unanswered=unanswered,
                           flagged=0)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
