"""Website giao bài tập lớp học. Chạy bằng: py app.py"""

import csv
import html
import io
import json
import os
import re
import secrets
import socket
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from flask import (
    Flask, Response, abort, flash, g, redirect, render_template, request,
    send_from_directory, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from quiz import config_for, decode_answers, legacy_config, score_quiz, total_points, validate_quiz, parse_points
from PIL import Image, UnidentifiedImageError


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
UPLOADS = ROOT / "uploads"
QUESTIONS = ROOT / "questions"
QUESTION_IMAGES = UPLOADS / "question-images"
DATA.mkdir(exist_ok=True)
UPLOADS.mkdir(exist_ok=True)
QUESTIONS.mkdir(exist_ok=True)
QUESTION_IMAGES.mkdir(exist_ok=True)
SECRET_FILE = DATA / "secret.key"
if not SECRET_FILE.exists():
    SECRET_FILE.write_text(secrets.token_hex(32), encoding="ascii")

app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static"))
app.secret_key = SECRET_FILE.read_text(encoding="ascii").strip()
app.config.update(
    MAX_CONTENT_LENGTH=20 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

VN = timezone(timedelta(hours=7))
DATABASE = DATA / "homework.sqlite3"
SEED_ANSWERS = "B B D A C A D B D D C A B C A C B C A C C A A C A A B A A B"


def now():
    return datetime.now(VN).replace(microsecond=0).isoformat(timespec="seconds")


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db():
    with closing(sqlite3.connect(DATABASE)) as connection:
        with connection:
            connection.executescript("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                filename TEXT NOT NULL,
                question_file TEXT NOT NULL DEFAULT '',
                question_count INTEGER NOT NULL,
                answer_key TEXT NOT NULL DEFAULT '',
                duration_minutes INTEGER NOT NULL DEFAULT 30,
                due_at TEXT NOT NULL DEFAULT '',
                is_open INTEGER NOT NULL DEFAULT 1,
                show_score INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL REFERENCES assignments(id),
                student_name TEXT NOT NULL,
                class_name TEXT NOT NULL,
                answers TEXT NOT NULL,
                score INTEGER,
                receipt TEXT NOT NULL UNIQUE,
                submitted_at TEXT NOT NULL,
                UNIQUE(assignment_id, student_name, class_name)
            );
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL REFERENCES assignments(id),
                student_name TEXT NOT NULL,
                class_name TEXT NOT NULL,
                token TEXT NOT NULL UNIQUE,
                started_at TEXT NOT NULL,
                ends_at TEXT NOT NULL,
                draft TEXT NOT NULL DEFAULT '',
                receipt TEXT NOT NULL DEFAULT '',
                UNIQUE(assignment_id, student_name, class_name)
            );
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, group_id INTEGER NOT NULL REFERENCES groups(id),
                code_hash TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL
            );
            """)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(assignments)")}
            if "question_file" not in columns:
                connection.execute("ALTER TABLE assignments ADD COLUMN question_file TEXT NOT NULL DEFAULT ''")
            if "duration_minutes" not in columns:
                connection.execute("ALTER TABLE assignments ADD COLUMN duration_minutes INTEGER NOT NULL DEFAULT 30")
            for column, definition in (("group_id", "INTEGER REFERENCES groups(id)"),
                                       ("grading_json", "TEXT NOT NULL DEFAULT ''")):
                if column not in columns:
                    connection.execute(f"ALTER TABLE assignments ADD COLUMN {column} {definition}")
            attempt_columns = {row[1] for row in connection.execute("PRAGMA table_info(attempts)")}
            if "draft" not in attempt_columns:
                connection.execute("ALTER TABLE attempts ADD COLUMN draft TEXT NOT NULL DEFAULT ''")
            for table in ("attempts", "submissions"):
                table_columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
                if "student_id" not in table_columns:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN student_id INTEGER REFERENCES students(id)")
            if "auth_version" not in {row[1] for row in connection.execute("PRAGMA table_info(students)")}:
                connection.execute("ALTER TABLE students ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 0")
            # Only bootstrap the default group and sample once. Deleting either must persist.
            first_start = not connection.execute(
                "SELECT 1 FROM settings WHERE key='sample_initialized'").fetchone()
            if first_start:
                connection.execute("INSERT OR IGNORE INTO groups(name) VALUES ('Chung')")
            if connection.execute("SELECT 1 FROM assignments WHERE group_id IS NULL").fetchone():
                connection.execute("INSERT OR IGNORE INTO groups(name) VALUES ('Chung')")
                default_group = connection.execute("SELECT id FROM groups WHERE name='Chung'").fetchone()[0]
                connection.execute("UPDATE assignments SET group_id=? WHERE group_id IS NULL", (default_group,))
            connection.execute("""UPDATE assignments SET question_file='btap1.json'
                                  WHERE filename='btap1.pdf' AND question_file=''""")
            connection.execute("UPDATE assignments SET show_score=1 WHERE answer_key<>''")
            count = connection.execute("SELECT COUNT(*) FROM assignments").fetchone()[0]
            if first_start and count == 0 and (UPLOADS / "btap1.pdf").exists():
                default_group = connection.execute("SELECT id FROM groups WHERE name='Chung'").fetchone()[0]
                connection.execute(
                    """INSERT INTO assignments
                       (title, description, filename, question_file, question_count,
                        answer_key, duration_minutes, show_score, created_at, group_id)
                        VALUES (?, ?, ?, 'btap1.json', ?, ?, 30, 1, ?, ?)""",
                    ("Bài tập 1: Giải hệ phương trình", "Toán 9 · 30 câu trắc nghiệm",
                     "btap1.pdf", 30, SEED_ANSWERS.replace(" ", ""), now(), default_group),
                )
            connection.execute("INSERT OR IGNORE INTO settings(key, value) VALUES ('sample_initialized', '1')")


init_db()


def configured():
    row = db().execute("SELECT value FROM settings WHERE key='teacher_password'").fetchone()
    return row is not None


def teacher_only(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not configured():
            return redirect(url_for("setup"))
        if not session.get("teacher"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


@app.context_processor
def template_helpers():
    return {"csrf_token": csrf_token, "teacher_logged_in": bool(session.get("teacher")),
            "student_logged_in": bool(student()) if not session.get("teacher") else False}


def check_csrf():
    if not secrets.compare_digest(request.form.get("csrf", ""), session.get("csrf", "!")):
        abort(400, "Biểu mẫu không hợp lệ. Vui lòng tải lại trang.")


def assignment_or_404(assignment_id):
    row = db().execute("SELECT * FROM assignments WHERE id=?", (assignment_id,)).fetchone()
    if row is None:
        abort(404)
    return row


def student():
    if not session.get("student_id"):
        return None
    record = db().execute("SELECT * FROM students WHERE id=?", (session["student_id"],)).fetchone()
    return record if record and record["auth_version"] == session.get("student_version") else None


def student_can_access(assignment):
    current = student()
    return bool(session.get("teacher") or (current and current["group_id"] == assignment["group_id"]))


def require_assignment_access(assignment):
    if not student_can_access(assignment):
        abort(403)


def is_available(assignment):
    if not assignment["is_open"]:
        return False
    if assignment["due_at"]:
        return now() <= assignment["due_at"]
    return True


def parse_due(value):
    value = value.strip()
    if not value:
        return ""
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M").replace(tzinfo=VN).isoformat(timespec="seconds")
    except ValueError:
        raise ValueError("Ngày hết hạn không hợp lệ.")


def parse_answer_key(value, question_count):
    value = value.strip().upper()
    if not value:
        return ""
    # Chấp nhận "B B D A", "B,B,D,A" hoặc "BBDA".
    letters = re.sub(r"[\s,;]+", "", value)
    if len(letters) != question_count or re.search(r"[^ABCD]", letters):
        raise ValueError(f"Cần đúng {question_count} đáp án A, B, C hoặc D.")
    return letters


def parse_duration(value):
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        raise ValueError("Vui lòng nhập thời gian làm bài bằng phút.")
    if not 1 <= minutes <= 180:
        raise ValueError("Thời gian làm bài phải từ 1 đến 180 phút.")
    return minutes


def parse_questions(value, question_count):
    """Mỗi dòng: Câu hỏi | phương án A | phương án B | phương án C | phương án D."""
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if len(lines) != question_count:
        raise ValueError(f"Cần đúng {question_count} dòng câu hỏi và bốn phương án.")
    result = []
    for number, line in enumerate(lines, 1):
        fields = [part.strip() for part in line.split("|")]
        if len(fields) != 5 or any(not part for part in fields):
            raise ValueError(f"Dòng {number}: cần nội dung câu hỏi | A | B | C | D.")
        result.append({"number": number, "content": html.escape(fields[0]),
                       "options": [{"key": key, "content": html.escape(content)}
                                   for key, content in zip("ABCD", fields[1:])]})
    return result


def load_questions(assignment):
    if not assignment["question_file"]:
        return None
    question_file = QUESTIONS / Path(assignment["question_file"]).name
    if not question_file.is_file():
        return None
    return json.loads(question_file.read_text(encoding="utf-8"))


def attempt_or_404(token):
    attempt = db().execute("SELECT * FROM attempts WHERE token=?", (token,)).fetchone()
    if attempt is None:
        abort(404)
    # Liên kết ngẫu nhiên trong phiên học sinh, không chỉ dựa vào họ tên.
    if not session.get("teacher") and not (
        (attempt["student_id"] is not None and student() and attempt["student_id"] == student()["id"]) or
        (attempt["student_id"] is None and token in session.get("attempt_tokens", []))
    ):
        abort(403)
    return attempt


def finalize_attempt(attempt, assignment, answers):
    """Chỉ ghi một bài nộp; dấu chấm là câu chưa trả lời."""
    connection = db()
    connection.execute("BEGIN IMMEDIATE")
    existing = connection.execute("SELECT receipt FROM attempts WHERE id=?", (attempt["id"],)).fetchone()
    if existing["receipt"]:
        connection.commit()
        return existing["receipt"]
    config = config_for(assignment)
    score = score_quiz(answers, config)[0] if config else None
    if isinstance(answers, list):
        answers = stored_answers(attempt, answers)
    receipt = secrets.token_urlsafe(24)
    connection.execute("""INSERT INTO submissions
        (assignment_id, student_name, class_name, answers, score, receipt, submitted_at, student_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (assignment["id"], attempt["student_name"], attempt["class_name"],
         answers, score, receipt, now(), attempt["student_id"]),
    )
    connection.execute("UPDATE attempts SET receipt=? WHERE id=?", (receipt, attempt["id"]))
    connection.commit()
    return receipt


def saved_answers(attempt, count, config=None):
    draft = attempt["draft"]
    if config and attempt["student_id"] is not None:
        return decode_answers(draft, config)
    return draft if len(draft) == count and all(a in "ABCD." for a in draft) else "." * count


def form_answers(config):
    values = []
    for index, item in enumerate(config, 1):
        if item["type"] == "true_false":
            values.append([request.form.get(f"q{index}_{j}", "") for j in range(len(item["correct"]))])
        else:
            values.append(request.form.get(f"q{index}", "")[:200])
    return decode_answers(values, config)


def encode_answers(answers):
    return json.dumps(answers, ensure_ascii=False)


def stored_answers(attempt, answers):
    if attempt["student_id"] is None:
        return "".join(a if a else "." for a in answers)
    return encode_answers(answers)


@app.get("/")
def home():
    if not configured():
        return redirect(url_for("setup"))
    current = student()
    if not session.get("teacher") and not current:
        return redirect(url_for("student_login"))
    if current and not session.get("teacher"):
        assignments = db().execute("SELECT * FROM assignments WHERE group_id=? ORDER BY id DESC", (current["group_id"],)).fetchall()
    else:
        assignments = db().execute("SELECT * FROM assignments ORDER BY id DESC").fetchall()
    return render_template("home.html", assignments=assignments, is_available=is_available)


@app.route("/giao-vien/khoi-tao", methods=["GET", "POST"])
def setup():
    if configured():
        return redirect(url_for("dashboard") if session.get("teacher") else url_for("login"))
    host = request.host.split("]")[0] + "]" if request.host.startswith("[") else request.host.split(":")[0]
    if (request.remote_addr not in ("127.0.0.1", "::1") or
        host not in ("127.0.0.1", "localhost", "[::1]") or
        request.headers.get("CF-Connecting-IP")):
        abort(403, "Hãy tạo mật khẩu giáo viên trực tiếp trên máy chủ qua 127.0.0.1.")
    if request.method == "POST":
        check_csrf()
        password = request.form.get("password", "")
        if len(password) < 10:
            flash("Mật khẩu giáo viên cần ít nhất 10 ký tự.", "error")
        elif password != request.form.get("confirm", ""):
            flash("Hai mật khẩu không khớp.", "error")
        else:
            db().execute(
                "INSERT INTO settings (key, value) VALUES ('teacher_password', ?)",
                (generate_password_hash(password),),
            )
            db().commit()
            session.clear()
            session["teacher"] = True
            flash("Đã tạo tài khoản giáo viên.", "success")
            return redirect(url_for("dashboard"))
    return render_template("auth.html", initial=True)


@app.route("/giao-vien/dang-nhap", methods=["GET", "POST"])
def login():
    if not configured():
        return redirect(url_for("setup"))
    if request.method == "POST":
        check_csrf()
        row = db().execute("SELECT value FROM settings WHERE key='teacher_password'").fetchone()
        if check_password_hash(row["value"], request.form.get("password", "")):
            session.clear()
            session["teacher"] = True
            return redirect(url_for("dashboard"))
        flash("Mật khẩu không đúng.", "error")
    return render_template("auth.html", initial=False)


@app.post("/giao-vien/dang-xuat")
@teacher_only
def logout():
    check_csrf()
    session.clear()
    return redirect(url_for("home"))


@app.route("/hoc-sinh/dang-nhap", methods=["GET", "POST"])
def student_login():
    if not configured():
        return redirect(url_for("setup"))
    if request.method == "POST":
        check_csrf()
        code = request.form.get("code", "").strip().upper()
        # Lookup by digest; raw codes are only shown when the teacher creates them.
        import hashlib
        digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
        match = db().execute("SELECT id, auth_version FROM students WHERE code_hash=?", (digest,)).fetchone()
        if match:
            session.clear()
            session["student_id"] = match["id"]
            session["student_version"] = match["auth_version"]
            session.permanent = True
            return redirect(url_for("home"))
        flash("Mã học sinh không đúng. Hãy liên hệ giáo viên.", "error")
    return render_template("student_login.html")


@app.post("/hoc-sinh/dang-xuat")
def student_logout():
    check_csrf()
    session.clear()
    return redirect(url_for("student_login"))


@app.get("/giao-vien")
@teacher_only
def dashboard():
    assignments = db().execute("""
        SELECT a.*, gr.name AS group_name, COUNT(s.id) AS submission_count FROM assignments a
        JOIN groups gr ON gr.id=a.group_id
        LEFT JOIN submissions s ON s.assignment_id=a.id
        GROUP BY a.id ORDER BY a.id DESC
    """).fetchall()
    groups = db().execute("SELECT gr.*, COUNT(st.id) AS student_count FROM groups gr LEFT JOIN students st ON st.group_id=gr.id GROUP BY gr.id ORDER BY gr.name").fetchall()
    return render_template("dashboard.html", assignments=assignments, groups=groups, is_available=is_available)


@app.post("/giao-vien/nhom/tao")
@teacher_only
def create_group():
    check_csrf()
    name = request.form.get("name", "").strip()
    if not 1 <= len(name) <= 60:
        flash("Tên nhóm môn/lớp phải có từ 1 đến 60 ký tự.", "error")
    else:
        try:
            db().execute("INSERT INTO groups(name) VALUES (?)", (name,))
            db().commit()
            flash("Đã tạo nhóm môn/lớp.", "success")
        except sqlite3.IntegrityError:
            flash("Nhóm này đã tồn tại.", "error")
    return redirect(url_for("dashboard"))


@app.get("/giao-vien/nhom/<int:group_id>")
@teacher_only
def group_detail(group_id):
    group = db().execute("SELECT * FROM groups WHERE id=?", (group_id,)).fetchone()
    if not group:
        abort(404)
    roster_rows = db().execute("""SELECT st.*, COUNT(DISTINCT s.assignment_id) AS completed FROM students st
        LEFT JOIN submissions s ON s.student_id=st.id
        WHERE st.group_id=? GROUP BY st.id ORDER BY st.name""", (group_id,)).fetchall()
    roster = []
    for item in roster_rows:
        entries = db().execute("""SELECT s.score, a.question_count, a.answer_key, a.grading_json
            FROM submissions s JOIN assignments a ON a.id=s.assignment_id WHERE s.student_id=?""",
            (item["id"],)).fetchall()
        ratios = [100 * entry["score"] / total_points(config_for(entry)) for entry in entries
                  if entry["score"] is not None and total_points(config_for(entry))]
        roster.append({**dict(item), "average_percent": round(sum(ratios) / len(ratios), 1) if ratios else None})
    assignments = db().execute("SELECT * FROM assignments WHERE group_id=? ORDER BY id DESC", (group_id,)).fetchall()
    return render_template("group.html", group=group, roster=roster, assignments=assignments,
                           new_code=session.pop("new_student_code", None))


def delete_assignment_data(connection, assignment):
    """Remove a quiz and its attempts/results inside the caller's transaction."""
    connection.execute("DELETE FROM submissions WHERE assignment_id=?", (assignment["id"],))
    connection.execute("DELETE FROM attempts WHERE assignment_id=?", (assignment["id"],))
    connection.execute("DELETE FROM assignments WHERE id=?", (assignment["id"],))


def remove_orphaned_files(assignments):
    """Delete only local files that are no longer referenced by any assignment."""
    for assignment in assignments:
        for folder, column, extension in ((QUESTIONS, "question_file", ".json"),
                                          (UPLOADS, "filename", ".pdf")):
            name = assignment[column]
            if not name or Path(name).name != name or not name.lower().endswith(extension):
                continue
            if db().execute(f"SELECT 1 FROM assignments WHERE {column}=? LIMIT 1", (name,)).fetchone():
                continue
            try:
                if column == "question_file" and (folder / name).is_file():
                    for question in json.loads((folder / name).read_text(encoding="utf-8")):
                        for image in question.get("images", []):
                            if Path(image).name == image and image.lower().endswith((".png", ".jpg", ".webp", ".gif")):
                                (QUESTION_IMAGES / image).unlink(missing_ok=True)
                (folder / name).unlink(missing_ok=True)
            except (OSError, ValueError, TypeError):
                flash(f"Đã xóa bài tập nhưng chưa xóa được tệp {name}; hãy kiểm tra thư mục {folder.name}.", "error")


@app.post("/giao-vien/nhom/<int:group_id>/xoa")
@teacher_only
def delete_group(group_id):
    check_csrf()
    connection = db()
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        group = connection.execute("SELECT * FROM groups WHERE id=?", (group_id,)).fetchone()
        if not group:
            abort(404)
        assignments = connection.execute("SELECT * FROM assignments WHERE group_id=?", (group_id,)).fetchall()
        for assignment in assignments:
            delete_assignment_data(connection, assignment)
        # A student's attempts can also belong to an assignment moved to another group.
        connection.execute("DELETE FROM submissions WHERE student_id IN (SELECT id FROM students WHERE group_id=?)", (group_id,))
        connection.execute("DELETE FROM attempts WHERE student_id IN (SELECT id FROM students WHERE group_id=?)", (group_id,))
        connection.execute("DELETE FROM students WHERE group_id=?", (group_id,))
        connection.execute("DELETE FROM groups WHERE id=?", (group_id,))
    session.pop("new_student_code", None)
    remove_orphaned_files(assignments)
    flash(f"Đã xóa nhóm {group['name']} cùng học sinh, bài tập và kết quả liên quan.", "success")
    return redirect(url_for("dashboard"))


@app.post("/giao-vien/nhom/<int:group_id>/hoc-sinh")
@teacher_only
def add_student(group_id):
    check_csrf()
    if not db().execute("SELECT id FROM groups WHERE id=?", (group_id,)).fetchone():
        abort(404)
    name = request.form.get("name", "").strip()
    if not 2 <= len(name) <= 100:
        flash("Họ tên học sinh phải có từ 2 đến 100 ký tự.", "error")
    else:
        import hashlib
        code = "HS-" + secrets.token_hex(6).upper()
        db().execute("INSERT INTO students(name, group_id, code_hash, created_at) VALUES (?, ?, ?, ?)",
                     (name, group_id, hashlib.sha256(code.encode()).hexdigest(), now()))
        db().commit()
        session["new_student_code"] = {"name": name, "code": code}
        flash("Đã cấp mã học sinh. Hãy sao chép trước khi rời trang.", "success")
    return redirect(url_for("group_detail", group_id=group_id))


@app.post("/giao-vien/hoc-sinh/<int:student_id>/doi-ma")
@teacher_only
def rotate_student_code(student_id):
    check_csrf()
    record = db().execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
    if not record:
        abort(404)
    import hashlib
    code = "HS-" + secrets.token_hex(6).upper()
    db().execute("UPDATE students SET code_hash=?, auth_version=auth_version+1 WHERE id=?",
                 (hashlib.sha256(code.encode()).hexdigest(), student_id))
    db().commit()
    session["new_student_code"] = {"name": record["name"], "code": code}
    flash("Mã cũ đã hết hiệu lực; hãy gửi mã mới cho học sinh.", "success")
    return redirect(url_for("group_detail", group_id=record["group_id"]))


@app.post("/giao-vien/hoc-sinh/<int:student_id>/xoa")
@teacher_only
def delete_student(student_id):
    check_csrf()
    connection = db()
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        record = connection.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
        if not record:
            abort(404)
        connection.execute("DELETE FROM submissions WHERE student_id=?", (student_id,))
        connection.execute("DELETE FROM attempts WHERE student_id=?", (student_id,))
        connection.execute("DELETE FROM students WHERE id=?", (student_id,))
    session.pop("new_student_code", None)
    flash(f"Đã xóa học sinh {record['name']} và lịch sử làm bài của em.", "success")
    return redirect(url_for("group_detail", group_id=record["group_id"]))


@app.get("/giao-vien/hoc-sinh/<int:student_id>")
@teacher_only
def student_progress(student_id):
    record = db().execute("""SELECT st.*, gr.name AS group_name FROM students st
        JOIN groups gr ON gr.id=st.group_id WHERE st.id=?""", (student_id,)).fetchone()
    if not record:
        abort(404)
    progress = db().execute("""SELECT a.title, a.id AS assignment_id, a.question_count,
        a.grading_json, a.answer_key, s.score, s.submitted_at, s.receipt, t.started_at, t.ends_at
        FROM assignments a LEFT JOIN submissions s ON s.assignment_id=a.id AND s.student_id=?
        LEFT JOIN attempts t ON t.assignment_id=a.id AND t.student_id=?
        WHERE a.group_id=? ORDER BY a.id DESC""",
        (student_id, student_id, record["group_id"])).fetchall()
    return render_template("student_progress.html", record=record, progress=progress,
                           total_points=total_points, config_for=config_for)


@app.route("/giao-vien/tao-bai", methods=["GET", "POST"])
@teacher_only
def create_assignment():
    if request.method == "POST":
        check_csrf()
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        upload = request.files.get("pdf")
        try:
            questions, grading = validate_quiz(request.form.get("quiz_json", ""))
            count = len(questions)
            group_id = int(request.form.get("group_id", ""))
            if not db().execute("SELECT id FROM groups WHERE id=?", (group_id,)).fetchone():
                raise ValueError("Vui lòng chọn nhóm môn/lớp hợp lệ.")
            if not title or len(title) > 150:
                raise ValueError("Tên bài tập phải có từ 1 đến 150 ký tự.")
            if len(description) > 1000:
                raise ValueError("Mô tả quá dài.")
            if upload and upload.filename:
                if not upload.filename.lower().endswith(".pdf") or upload.stream.read(5) != b"%PDF-":
                    raise ValueError("File được chọn không phải PDF hợp lệ.")
                upload.stream.seek(0)
            images = []
            extensions = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp", "GIF": ".gif"}
            for index in range(1, count + 1):
                files = [file for file in request.files.getlist(f"image_{index}") if file.filename]
                if len(files) > 3:
                    raise ValueError(f"Câu {index}: tối đa 3 hình ảnh.")
                question_images = []
                for file in files:
                    data = file.read(3 * 1024 * 1024 + 1)
                    if not data or len(data) > 3 * 1024 * 1024:
                        raise ValueError(f"Câu {index}: mỗi ảnh tối đa 3 MB.")
                    try:
                        with Image.open(io.BytesIO(data)) as image:
                            image_format = image.format
                            if image_format not in extensions or image.width * image.height > 10_000_000:
                                raise ValueError("định dạng/kích thước ảnh không hợp lệ")
                            image.verify()
                    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
                        raise ValueError(f"Câu {index}: chỉ nhận ảnh PNG, JPG, WebP hoặc GIF hợp lệ (tối đa 10 triệu pixel).")
                    question_images.append((uuid.uuid4().hex + extensions[image_format], data))
                images.append(question_images)
            due = parse_due(request.form.get("due_at", ""))
            duration = parse_duration(request.form.get("duration_minutes"))
        except (ValueError, TypeError) as error:
            flash(str(error), "error")
        else:
            identifier = uuid.uuid4().hex
            filename = f"{identifier}.pdf" if upload and upload.filename else ""
            question_file = f"{identifier}.json"
            written = []
            try:
                if filename:
                    upload.save(UPLOADS / filename)
                    written.append(UPLOADS / filename)
                for question, files in zip(questions, images):
                    question["images"] = [name for name, _ in files]
                    for name, data in files:
                        path = QUESTION_IMAGES / name
                        path.write_bytes(data)
                        written.append(path)
                path = QUESTIONS / question_file
                path.write_text(json.dumps(questions, ensure_ascii=False), encoding="utf-8")
                written.append(path)
                db().execute("""INSERT INTO assignments
                    (title, description, filename, question_file, question_count,
                     answer_key, duration_minutes, due_at, show_score, created_at, group_id, grading_json)
                     VALUES (?, ?, ?, ?, ?, '', ?, ?, 1, ?, ?, ?)""",
                     (title, description, filename, question_file, count, duration, due, now(), group_id,
                      json.dumps(grading, ensure_ascii=False)),
                )
                db().commit()
            except (OSError, sqlite3.Error):
                db().rollback()
                for path in written:
                    path.unlink(missing_ok=True)
                flash("Không lưu được đề và hình ảnh. Vui lòng thử lại.", "error")
                return redirect(url_for("create_assignment"))
            flash("Đã đăng bài tập.", "success")
            return redirect(url_for("dashboard"))
    groups = db().execute("SELECT * FROM groups ORDER BY name").fetchall()
    return render_template("create.html", groups=groups)


@app.get("/giao-vien/bai/<int:assignment_id>")
@teacher_only
def teacher_assignment(assignment_id):
    assignment = assignment_or_404(assignment_id)
    submissions = db().execute(
        "SELECT * FROM submissions WHERE assignment_id=? ORDER BY submitted_at DESC",
        (assignment_id,),
    ).fetchall()
    groups = db().execute("SELECT * FROM groups ORDER BY name").fetchall()
    config = config_for(assignment)
    review_rows = [(row, decode_answers(row["answers"], config)) for row in submissions]
    return render_template("teacher_assignment.html", assignment=assignment,
                           submissions=review_rows, groups=groups, max_score=total_points(config),
                           config_for_legacy=[str(q["points"]) for q in config],
                           is_available=is_available)


@app.post("/giao-vien/bai/<int:assignment_id>/xoa")
@teacher_only
def delete_assignment(assignment_id):
    check_csrf()
    connection = db()
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        assignment = connection.execute("SELECT * FROM assignments WHERE id=?", (assignment_id,)).fetchone()
        if not assignment:
            abort(404)
        delete_assignment_data(connection, assignment)
    remove_orphaned_files([assignment])
    flash(f"Đã xóa bài tập {assignment['title']} cùng toàn bộ bài làm và kết quả.", "success")
    return redirect(url_for("dashboard"))


@app.post("/giao-vien/bai/<int:assignment_id>/cap-nhat")
@teacher_only
def update_assignment(assignment_id):
    check_csrf()
    assignment = assignment_or_404(assignment_id)
    try:
        due = parse_due(request.form.get("due_at", ""))
        duration = parse_duration(request.form.get("duration_minutes"))
        group_id = int(request.form.get("group_id", ""))
        if not db().execute("SELECT id FROM groups WHERE id=?", (group_id,)).fetchone():
            raise ValueError("Vui lòng chọn nhóm hợp lệ.")
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("teacher_assignment", assignment_id=assignment_id))
    db().execute("""UPDATE assignments SET due_at=?, is_open=?, duration_minutes=?, group_id=?
                     WHERE id=?""",
                  (due, int(bool(request.form.get("is_open"))), duration, group_id, assignment_id))
    db().commit()
    flash("Đã cập nhật bài tập.", "success")
    return redirect(url_for("teacher_assignment", assignment_id=assignment_id))


@app.post("/giao-vien/bai/<int:assignment_id>/cham-diem")
@teacher_only
def update_grading(assignment_id):
    check_csrf()
    assignment = assignment_or_404(assignment_id)
    if not assignment["answer_key"]:
        flash("Bài dạng hỗn hợp: tạo bài mới nếu muốn thay cấu trúc hoặc đáp án.", "error")
        return redirect(url_for("teacher_assignment", assignment_id=assignment_id))
    try:
        answer_key = parse_answer_key(request.form.get("answer_key", ""), assignment["question_count"])
        if not answer_key:
            raise ValueError("Cần nhập đáp án đúng.")
        points = [parse_points(x) for x in request.form.get("points", "").split()]
        grading = legacy_config(answer_key, assignment["question_count"], points)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("teacher_assignment", assignment_id=assignment_id))
    db().execute("UPDATE assignments SET answer_key=?, grading_json=? WHERE id=?",
                 (answer_key, json.dumps(grading), assignment_id))
    for row in db().execute("SELECT id, answers FROM submissions WHERE assignment_id=?", (assignment_id,)):
        db().execute("UPDATE submissions SET score=? WHERE id=?",
                     (score_quiz(row["answers"], grading)[0], row["id"]))
    db().commit()
    flash("Đã lưu điểm từng câu và chấm lại các bài đã nộp.", "success")
    return redirect(url_for("teacher_assignment", assignment_id=assignment_id))


@app.get("/giao-vien/bai/<int:assignment_id>/xuat-csv")
@teacher_only
def export_csv(assignment_id):
    assignment = assignment_or_404(assignment_id)
    output = io.StringIO()
    writer = csv.writer(output)
    config = config_for(assignment)
    writer.writerow(["Mã học sinh (ID)", "Họ tên", "Lớp", "Thời gian nộp (GMT+7)", "Điểm", "Điểm tối đa", "Bài làm"])
    for row in db().execute("SELECT * FROM submissions WHERE assignment_id=? ORDER BY id", (assignment_id,)):
        # Tránh Excel diễn giải tên/lớp học sinh thành công thức.
        safe = lambda text: "'" + text if text.startswith(("=", "+", "-", "@")) else text
        writer.writerow([row["student_id"] or "", safe(row["student_name"]), safe(row["class_name"]),
                          row["submitted_at"], "" if row["score"] is None else row["score"],
                          total_points(config), safe(json.dumps(decode_answers(row["answers"], config), ensure_ascii=False))])
    return Response("\ufeff" + output.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="ket-qua-bai-{assignment_id}.csv"'})


@app.get("/bai/<int:assignment_id>")
def student_assignment(assignment_id):
    assignment = assignment_or_404(assignment_id)
    require_assignment_access(assignment)
    tokens = session.get("attempt_tokens", [])
    current = db().execute("""SELECT token FROM attempts WHERE assignment_id=?
                              AND token IN ({}) AND receipt='' LIMIT 1""".format(",".join("?" for _ in tokens)),
                           (assignment_id, *tokens)).fetchone() if tokens else None
    if student() and not session.get("teacher"):
        current = db().execute("SELECT token FROM attempts WHERE assignment_id=? AND student_id=? AND receipt=''",
                               (assignment_id, session["student_id"])).fetchone()
    submitted = db().execute("SELECT receipt FROM submissions WHERE assignment_id=? AND student_id=?",
                             (assignment_id, student()["id"])).fetchone() if student() else None
    return render_template("student_assignment.html", assignment=assignment, current_student=student(),
                            available=is_available(assignment) and bool(load_questions(assignment)),
                            current_attempt=current, submitted=submitted)


@app.get("/tai-lieu/<int:assignment_id>")
@teacher_only
def document(assignment_id):
    assignment = assignment_or_404(assignment_id)
    if not assignment["filename"]:
        abort(404)
    response = send_from_directory(UPLOADS, assignment["filename"], mimetype="application/pdf",
                                   as_attachment=False)
    response.headers["Cache-Control"] = "private, no-store"
    return response


@app.get("/hinh-cau-hoi/<int:assignment_id>/<filename>")
def question_image(assignment_id, filename):
    assignment = assignment_or_404(assignment_id)
    current = student()
    has_attempt = bool(current and db().execute(
        "SELECT 1 FROM attempts WHERE assignment_id=? AND student_id=?",
        (assignment_id, current["id"])).fetchone())
    if not student_can_access(assignment) and not has_attempt:
        abort(403)
    questions = load_questions(assignment) or []
    if not any(filename in question.get("images", []) for question in questions):
        abort(404)
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}.get(Path(filename).suffix)
    if not mime:
        abort(404)
    response = send_from_directory(QUESTION_IMAGES, filename, mimetype=mime)
    response.headers["Cache-Control"] = "private, no-store"
    return response


@app.post("/bai/<int:assignment_id>/bat-dau")
def start_attempt(assignment_id):
    check_csrf()
    assignment = assignment_or_404(assignment_id)
    require_assignment_access(assignment)
    current = student()
    if not current:
        abort(403, "Hãy đăng nhập bằng mã học sinh.")
    if not is_available(assignment) or not load_questions(assignment):
        abort(403, "Bài tập đã đóng hoặc hết hạn.")
    name = current["name"]
    group_name = db().execute("SELECT name FROM groups WHERE id=?", (current["group_id"],)).fetchone()["name"]
    class_name = f"{group_name} · HS#{current['id']}"
    existing = db().execute("SELECT 1 FROM submissions WHERE assignment_id=? AND student_id=?",
                            (assignment_id, current["id"])).fetchone()
    if existing:
        flash("Họ tên và lớp này đã nộp bài. Nếu nhập nhầm, hãy liên hệ giáo viên.", "error")
        return redirect(url_for("student_assignment", assignment_id=assignment_id))
    started = datetime.now(VN).replace(microsecond=0)
    ends = started + timedelta(minutes=assignment["duration_minutes"])
    if assignment["due_at"]:
        ends = min(ends, datetime.fromisoformat(assignment["due_at"]))
    token = secrets.token_urlsafe(24)
    try:
        db().execute("""INSERT INTO attempts
            (assignment_id, student_name, class_name, token, started_at, ends_at, draft, student_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (assignment_id, name, class_name, token, started.isoformat(), ends.isoformat(),
              encode_answers(decode_answers([], config_for(assignment))), current["id"]))
        db().commit()
    except sqlite3.IntegrityError:
        previous = db().execute("SELECT token FROM attempts WHERE assignment_id=? AND student_id=?",
                                (assignment_id, current["id"])).fetchone()
        if previous:
            session["attempt_tokens"] = (session.get("attempt_tokens", []) + [previous["token"]])[-20:]
            return redirect(url_for("take_exam", token=previous["token"]))
        flash("Họ tên và lớp này đã bắt đầu làm bài. Hãy mở lại trang đang làm trên thiết bị cũ.", "error")
        return redirect(url_for("student_assignment", assignment_id=assignment_id))
    tokens = session.get("attempt_tokens", [])
    session["attempt_tokens"] = (tokens + [token])[-20:]
    session.permanent = True
    return redirect(url_for("take_exam", token=token))


@app.get("/lam-bai/<token>")
def take_exam(token):
    attempt = attempt_or_404(token)
    if attempt["receipt"]:
        return redirect(url_for("receipt_page", receipt=attempt["receipt"]))
    assignment = assignment_or_404(attempt["assignment_id"])
    config = config_for(assignment)
    remaining = (datetime.fromisoformat(attempt["ends_at"]) - datetime.now(VN)).total_seconds()
    if remaining <= 0:
        receipt = finalize_attempt(attempt, assignment, saved_answers(attempt, assignment["question_count"], config))
        return redirect(url_for("receipt_page", receipt=receipt))
    questions = load_questions(assignment)
    if questions is None:
        abort(404)
    response = Response(render_template("exam.html", assignment=assignment, attempt=attempt,
                                         questions=questions, remaining=max(1, int(remaining + .999)),
                                         draft=saved_answers(attempt, assignment["question_count"], config),
                                         answers=decode_answers(saved_answers(attempt, assignment["question_count"], config), config)))
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/lam-bai/<token>/luu")
def save_draft(token):
    check_csrf()
    attempt = attempt_or_404(token)
    if attempt["receipt"] or datetime.now(VN) >= datetime.fromisoformat(attempt["ends_at"]):
        return "", 409
    assignment = assignment_or_404(attempt["assignment_id"])
    choices = form_answers(config_for(assignment))
    db().execute("UPDATE attempts SET draft=? WHERE id=?", (stored_answers(attempt, choices), attempt["id"]))
    db().commit()
    return "", 204


@app.post("/lam-bai/<token>/nop")
def submit(token):
    check_csrf()
    attempt = attempt_or_404(token)
    if attempt["receipt"]:
        return redirect(url_for("receipt_page", receipt=attempt["receipt"]))
    assignment = assignment_or_404(attempt["assignment_id"])
    config = config_for(assignment)
    expired_seconds = (datetime.now(VN) - datetime.fromisoformat(attempt["ends_at"])).total_seconds()
    if expired_seconds > 5:
        answers = saved_answers(attempt, assignment["question_count"], config)
    else:
        answers = form_answers(config)
    receipt = finalize_attempt(attempt, assignment, stored_answers(attempt, answers)
                               if isinstance(answers, list) else answers)
    return redirect(url_for("receipt_page", receipt=receipt))


@app.get("/da-nop/<receipt>")
def receipt_page(receipt):
    row = db().execute("""SELECT s.*, a.title, a.question_count, a.show_score, a.answer_key, a.grading_json
                          FROM submissions s JOIN assignments a ON a.id=s.assignment_id
                          WHERE s.receipt=?""", (receipt,)).fetchone()
    if row is None:
        abort(404)
    if not session.get("teacher") and (row["student_id"] is not None and
                                       (not student() or row["student_id"] != student()["id"])):
        abort(403)
    review = None
    grading = config_for(row)
    if row["show_score"] and grading:
        _, review = score_quiz(row["answers"], grading)
    return render_template("receipt.html", result=row, review=review, max_score=total_points(grading))


@app.errorhandler(413)
def too_large(_error):
    return "Tổng dung lượng PDF và ảnh trong bài vượt giới hạn 20 MB.", 413


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    # Không gửi gói tin; kết nối UDP chỉ để tìm giao diện có đường ra mạng.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
            connection.connect(("1.1.1.1", 80))
            lan_ip = connection.getsockname()[0]
    except OSError:
        lan_ip = "<IP-cua-may>"
    print(f"Tren may nay: http://127.0.0.1:{port}", flush=True)
    print(f"Thiet bi cung Wi-Fi: http://{lan_ip}:{port}", flush=True)
    app.run(host=host, port=port, debug=False)
