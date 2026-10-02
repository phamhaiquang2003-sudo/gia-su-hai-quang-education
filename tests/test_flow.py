"""Run: py -m unittest discover -s tests -v"""
import importlib.util
import io
import json
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from contextlib import closing
from pathlib import Path
from PIL import Image
from quiz import score_quiz, validate_quiz

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))


class FlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="homework-v2-")
        self.root = Path(self.tmp.name)
        shutil.copy2(SOURCE / "app.py", self.root / "app.py")
        for folder in ("templates", "static", "questions"):
            shutil.copytree(SOURCE / folder, self.root / folder)
        sample_questions = self.root / "questions" / "btap1.json"
        if not sample_questions.exists():
            sample_questions.write_text(json.dumps([
                {"number": number, "content": f"Test question {number}",
                 "options": [{"key": key, "content": key} for key in "ABCD"]}
                for number in range(1, 31)
            ]), encoding="utf-8")
        (self.root / "uploads").mkdir()
        (self.root / "uploads" / "btap1.pdf").write_bytes(b"%PDF-1.4\n")
        spec = importlib.util.spec_from_file_location("homework_flow", self.root / "app.py")
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.mod.app.config["TESTING"] = True
        self.teacher = self.mod.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def csrf(self, client, url):
        page = client.get(url)
        self.assertEqual(page.status_code, 200, page.get_data(as_text=True)[:400])
        return re.search(r'name="csrf" value="([^"]+)"', page.get_data(as_text=True)).group(1)

    def post(self, client, url, data, page_url=None):
        return client.post(url, data={"csrf": self.csrf(client, page_url or url), **data})

    def setup_teacher(self):
        response = self.post(self.teacher, "/giao-vien/khoi-tao",
                             {"password":"Teacher-password-123", "confirm":"Teacher-password-123"})
        self.assertEqual(response.status_code, 302)

    def create_student(self, group_id, name):
        response = self.post(self.teacher, f"/giao-vien/nhom/{group_id}/hoc-sinh", {"name":name},
                             f"/giao-vien/nhom/{group_id}")
        self.assertEqual(response.status_code, 302)
        page = self.teacher.get(response.headers["Location"]).get_data(as_text=True)
        return re.search(r'HS-[0-9A-F]{12}', page).group(0)

    def login_student(self, code):
        client = self.mod.app.test_client()
        response = self.post(client, "/hoc-sinh/dang-nhap", {"code":code})
        self.assertEqual(response.headers["Location"], "/")
        return client

    def test_mixed_quiz_student_isolation_and_early_submit(self):
        self.setup_teacher()
        self.post(self.teacher, "/giao-vien/nhom/tao", {"name":"Toán 9"}, "/giao-vien")
        self.post(self.teacher, "/giao-vien/nhom/tao", {"name":"Lý 12"}, "/giao-vien")
        db = sqlite3.connect(self.mod.DATABASE)
        group = db.execute("SELECT id FROM groups WHERE name='Toán 9'").fetchone()[0]
        other = db.execute("SELECT id FROM groups WHERE name='Lý 12'").fetchone()[0]
        db.close()
        first_code = self.create_student(group, "Minh")
        second_code = self.create_student(group, "Minh")  # identical names remain distinguishable
        other_code = self.create_student(other, "Student Other")
        quiz = [
            {"type":"mcq", "prompt":"1 + 1?", "options":["2","3","4","5"], "correct":"A", "points":"2"},
            {"type":"true_false", "prompt":"Đánh giá", "statements":["Ý a", "Ý b", "Ý c", "Ý d"], "correct":["D","S","D","S"], "points":"3"},
            {"type":"short", "prompt":"Kết quả", "correct":"0,5; 1/2", "points":"5"},
        ]
        result = self.post(self.teacher, "/giao-vien/tao-bai", {"title":"Bài hỗn hợp", "group_id":str(group),
                           "duration_minutes":"10", "quiz_json":json.dumps(quiz)})
        self.assertEqual(result.status_code, 302)
        own = self.login_student(first_code)
        other_client = self.login_student(other_code)
        self.assertEqual(other_client.get("/bai/2").status_code, 403)
        self.assertNotIn("Bài hỗn hợp", other_client.get("/").get_data(as_text=True))
        self.assertEqual(other_client.get("/giao-vien").status_code, 302)
        self.assertEqual(other_client.get("/tai-lieu/1").status_code, 302)
        self.assertEqual(other_client.get("/giao-vien/nhom/1").status_code, 302)
        self.assertEqual(other_client.get("/giao-vien/dang-nhap").status_code, 200)
        denied = self.post(other_client, "/giao-vien/dang-nhap", {"password":other_code})
        self.assertNotIn("/giao-vien\"", denied.get_data(as_text=True))
        self.assertNotIn("correct", own.get("/bai/2").get_data(as_text=True))
        start = self.post(own, "/bai/2/bat-dau", {}, "/bai/2")
        exam_url = start.headers["Location"]
        exam = own.get(exam_url).get_data(as_text=True)
        self.assertIn("Trả lời ngắn", exam)
        self.assertNotIn('name="q1" value="A" checked', exam)
        self.assertNotIn("1/2", exam)
        self.assertEqual(other_client.get(exam_url).status_code, 403)
        self.assertEqual(self.post(own, exam_url + "/luu", {"q1":"A", "q2_0":"D", "q3":"0,5"}, exam_url).status_code, 204)
        self.assertIn("value=\"0,5\"", own.get(exam_url).get_data(as_text=True))
        # A new login on another device resumes the same student's unfinished attempt.
        own_again = self.login_student(first_code)
        self.assertEqual(own_again.get(exam_url).status_code, 200)
        submit = self.post(own_again, exam_url + "/nop", {"q1":"A", "q2_0":"D", "q2_1":"S", "q2_2":"D", "q3":"0,5"}, exam_url)
        receipt = own_again.get(submit.headers["Location"]).get_data(as_text=True)
        self.assertIn("7.5/8", receipt)  # 2 + 0.5 for three true/false ideas + 5
        self.assertEqual(other_client.get(submit.headers["Location"]).status_code, 403)
        second = self.login_student(second_code)
        second_start = self.post(second, "/bai/2/bat-dau", {}, "/bai/2")
        self.assertIn("/lam-bai/", second_start.headers["Location"])
        self.assertIn("Minh", self.teacher.get("/giao-vien/nhom/" + str(group)).get_data(as_text=True))
        self.assertIn("7.5", self.teacher.get("/giao-vien/bai/2/xuat-csv").get_data(as_text=True))
        with closing(sqlite3.connect(self.mod.DATABASE)) as db:
            student_id = db.execute("SELECT id FROM students WHERE name='Minh' ORDER BY id LIMIT 1").fetchone()[0]
        self.assertIn("7.5", self.teacher.get(f"/giao-vien/hoc-sinh/{student_id}").get_data(as_text=True))
        self.assertEqual(other_client.get(f"/giao-vien/hoc-sinh/{student_id}").status_code, 302)
        self.post(self.teacher, f"/giao-vien/hoc-sinh/{student_id}/doi-ma", {},
                  f"/giao-vien/nhom/{group}")
        self.assertEqual(own_again.get(exam_url).status_code, 403)
        invalid_old_code = self.post(self.mod.app.test_client(), "/hoc-sinh/dang-nhap", {"code":first_code})
        self.assertEqual(invalid_old_code.status_code, 200)

    def test_old_data_and_legacy_scoring(self):
        self.assertEqual(self.teacher.get("/giao-vien/khoi-tao", environ_overrides={"REMOTE_ADDR":"192.168.0.5"}).status_code, 403)
        self.assertEqual(self.teacher.get("/giao-vien/khoi-tao", headers={"CF-Connecting-IP":"1.2.3.4"}).status_code, 403)
        self.setup_teacher()
        pdf = self.teacher.get("/tai-lieu/1")
        self.assertEqual(pdf.status_code, 200)
        pdf.close()
        self.assertEqual(self.teacher.get("/giao-vien/bai/1").status_code, 200)
        page = self.teacher.get("/giao-vien/bai/1").get_data(as_text=True)
        self.assertIn("Chấm điểm bài cũ", page)
        points = "2 " + "1 " * 29
        response = self.post(self.teacher, "/giao-vien/bai/1/cham-diem", {
            "answer_key":self.mod.SEED_ANSWERS, "points":points}, "/giao-vien/bai/1")
        self.assertEqual(response.status_code, 302)
        student_code = self.create_student(1, "Legacy Student")
        student = self.login_student(student_code)
        start = self.post(student, "/bai/1/bat-dau", {}, "/bai/1")
        exam_url = start.headers["Location"]
        submit = self.post(student, exam_url + "/nop", {"q1":"B"}, exam_url)
        self.assertIn("2/31", student.get(submit.headers["Location"]).get_data(as_text=True))
        self.assertEqual(student.get(exam_url).status_code, 302)
        self.assertEqual(student.get("/tai-lieu/1").status_code, 302)

    def test_expired_attempt_uses_saved_draft(self):
        self.setup_teacher()
        code = self.create_student(1, "Timed Student")
        student = self.login_student(code)
        start = self.post(student, "/bai/1/bat-dau", {}, "/bai/1")
        exam_url = start.headers["Location"]
        self.post(student, exam_url + "/luu", {"q1":"B"}, exam_url)
        with closing(sqlite3.connect(self.mod.DATABASE)) as db:
            with db:
                db.execute("UPDATE attempts SET ends_at=? WHERE token=?",
                           ((datetime.now(timezone(timedelta(hours=7))) - timedelta(seconds=10)).isoformat(),
                            exam_url.rsplit('/',1)[-1]))
        result = student.get(exam_url)
        self.assertEqual(result.status_code, 302)
        self.assertIn("1/30", student.get(result.headers["Location"]).get_data(as_text=True))

    def test_delete_student_assignment_and_group_isolated(self):
        self.setup_teacher()
        self.post(self.teacher, "/giao-vien/nhom/tao", {"name":"Toán 9"}, "/giao-vien")
        self.post(self.teacher, "/giao-vien/nhom/tao", {"name":"Lý 12"}, "/giao-vien")
        with closing(sqlite3.connect(self.mod.DATABASE)) as connection:
            group_a, group_b = [row[0] for row in connection.execute(
                "SELECT id FROM groups WHERE name IN ('Toán 9','Lý 12') ORDER BY id")]
        code_a = self.create_student(group_a, "Student A")
        code_b = self.create_student(group_b, "Student B")
        quiz = json.dumps([{"type":"mcq", "prompt":"1+1?", "options":["2","3","4","5"],
                            "correct":"A", "points":"2"}])
        first = self.post(self.teacher, "/giao-vien/tao-bai", {
            "title":"Bài Toán", "group_id":str(group_a), "duration_minutes":"10",
            "quiz_json":quiz, "pdf":(io.BytesIO(b"%PDF-1.4\n"), "practice.pdf")})
        self.assertEqual(first.status_code, 302)
        second = self.post(self.teacher, "/giao-vien/tao-bai", {
            "title":"Bài Lý", "group_id":str(group_b), "duration_minutes":"10", "quiz_json":quiz})
        self.assertEqual(second.status_code, 302)
        with closing(sqlite3.connect(self.mod.DATABASE)) as connection:
            student_a = connection.execute("SELECT id FROM students WHERE name='Student A'").fetchone()[0]
            assignment_a, question_file, pdf_file = connection.execute(
                "SELECT id, question_file, filename FROM assignments WHERE title='Bài Toán'").fetchone()
            assignment_b = connection.execute("SELECT id FROM assignments WHERE title='Bài Lý'").fetchone()[0]
        child_a = self.login_student(code_a)
        start = self.post(child_a, f"/bai/{assignment_a}/bat-dau", {}, f"/bai/{assignment_a}")
        attempt_a = start.headers["Location"]
        receipt = self.post(child_a, attempt_a + "/nop", {"q1":"A"}, attempt_a).headers["Location"]
        child_b = self.login_student(code_b)
        start_b = self.post(child_b, f"/bai/{assignment_b}/bat-dau", {}, f"/bai/{assignment_b}")
        receipt_b = self.post(child_b, start_b.headers["Location"] + "/nop",
                              {"q1":"A"}, start_b.headers["Location"]).headers["Location"]

        delete_student_url = f"/giao-vien/hoc-sinh/{student_a}/xoa"
        self.assertEqual(child_a.post(delete_student_url).status_code, 302)
        self.assertEqual(self.teacher.get(delete_student_url).status_code, 405)
        self.assertEqual(self.teacher.post(delete_student_url).status_code, 400)
        self.assertEqual(child_a.get(receipt).status_code, 200)
        deleted = self.post(self.teacher, delete_student_url, {}, f"/giao-vien/nhom/{group_a}")
        self.assertEqual(deleted.status_code, 302)
        self.assertEqual(child_a.get(receipt).status_code, 404)
        self.assertEqual(child_a.get(attempt_a).status_code, 404)
        self.assertEqual(self.post(self.mod.app.test_client(), "/hoc-sinh/dang-nhap", {"code":code_a}).status_code, 200)
        self.assertEqual(child_b.get(receipt_b).status_code, 200)
        self.assertEqual(self.teacher.get(f"/giao-vien/bai/{assignment_a}").status_code, 200)

        # Deleting a quiz removes its private files but not other groups' work.
        code_a2 = self.create_student(group_a, "Student A2")
        child_a2 = self.login_student(code_a2)
        pending = self.post(child_a2, f"/bai/{assignment_a}/bat-dau", {},
                            f"/bai/{assignment_a}").headers["Location"]
        self.assertTrue((self.root / "questions" / question_file).exists())
        self.assertTrue((self.root / "uploads" / pdf_file).exists())
        deleted = self.post(self.teacher, f"/giao-vien/bai/{assignment_a}/xoa", {},
                            f"/giao-vien/bai/{assignment_a}")
        self.assertEqual(deleted.status_code, 302)
        self.assertFalse((self.root / "questions" / question_file).exists())
        self.assertFalse((self.root / "uploads" / pdf_file).exists())
        self.assertEqual(self.teacher.get(f"/giao-vien/bai/{assignment_a}").status_code, 404)
        self.assertEqual(child_a2.get(pending).status_code, 404)
        self.assertEqual(child_b.get(receipt_b).status_code, 200)

        # Removing the empty class does not affect the other class or re-create the first one.
        deleted = self.post(self.teacher, f"/giao-vien/nhom/{group_a}/xoa", {},
                            f"/giao-vien/nhom/{group_a}")
        self.assertEqual(deleted.status_code, 302)
        self.mod.init_db()
        self.assertEqual(self.teacher.get(f"/giao-vien/nhom/{group_a}").status_code, 404)
        self.assertEqual(child_a2.get("/").status_code, 302)
        self.assertEqual(self.teacher.get(f"/giao-vien/bai/{assignment_b}").status_code, 200)
        self.assertEqual(child_b.get(receipt_b).status_code, 200)

    def test_delete_class_with_contents_and_no_sample_reseed(self):
        self.setup_teacher()
        code = self.create_student(1, "Student Chung")
        child = self.login_student(code)
        attempt = self.post(child, "/bai/1/bat-dau", {}, "/bai/1").headers["Location"]
        receipt = self.post(child, attempt + "/nop", {"q1":"B"}, attempt).headers["Location"]
        self.assertEqual(child.get(receipt).status_code, 200)
        self.assertTrue((self.root / "questions" / "btap1.json").exists())
        deleted = self.post(self.teacher, "/giao-vien/nhom/1/xoa", {}, "/giao-vien/nhom/1")
        self.assertEqual(deleted.status_code, 302)
        self.assertEqual(child.get(receipt).status_code, 404)
        self.assertEqual(child.get(attempt).status_code, 404)
        self.assertFalse((self.root / "questions" / "btap1.json").exists())
        self.assertFalse((self.root / "uploads" / "btap1.pdf").exists())
        self.mod.init_db()
        with closing(sqlite3.connect(self.mod.DATABASE)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM groups").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM assignments").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM submissions").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM students").fetchone()[0], 0)

    def test_true_false_fixed_rubric_and_old_scoring(self):
        row = {"type":"true_false", "prompt":"Đúng hay sai?", "points":"99",
               "statements":["a", "b", "c", "d"], "correct":["D", "S", "D", "S"]}
        questions, config = validate_quiz([row])
        self.assertEqual(questions[0]["points"], 1)
        self.assertEqual(config[0]["points"], 1)
        for selections, expected in [(["", "", "", ""], 0), (["D", "", "", ""], .1),
                                     (["D", "S", "", ""], .25), (["D", "S", "D", ""], .5),
                                     (["D", "S", "D", "S"], 1)]:
            self.assertEqual(score_quiz([selections], config)[0], expected)
        self.assertEqual(score_quiz([["S", "D", "S", "D"]], config)[0], 0)
        with self.assertRaisesRegex(ValueError, "đủ bốn ý"):
            validate_quiz([{**row, "statements":["a", "b"], "correct":["D", "S"]}])
        old_config = [{"type":"true_false", "correct":["D", "S"], "points":3}]
        self.assertEqual(score_quiz([["D", ""]], old_config)[0], 1.5)

    def test_math_and_uploaded_images_visible_only_to_class(self):
        self.setup_teacher()
        editor = self.teacher.get("/giao-vien/tao-bai").get_data(as_text=True)
        self.assertIn('id="latex-picker"', editor)
        self.assertIn('latex-catalog.js', editor)
        self.assertIn('latex-picker.js', editor)
        image = io.BytesIO()
        Image.new("RGB", (24, 20), "white").save(image, format="PNG")
        image.seek(0)
        second_image = io.BytesIO()
        Image.new("RGB", (24, 20), "black").save(second_image, format="PNG")
        second_image.seek(0)
        quiz = [{"type":"mcq", "prompt":r"Tính \(\frac{1}{2}\) <script>alert(1)</script>",
                 "options":[r"\(x^2\)", "0", "1", "2"], "correct":"A", "points":2}]
        response = self.post(self.teacher, "/giao-vien/tao-bai", {
            "title":"Bài có hình và toán", "group_id":"1", "duration_minutes":"10",
            "quiz_json":json.dumps(quiz), "image_1":[(image, "hinh.png"), (second_image, "hinh2.png")]})
        self.assertEqual(response.status_code, 302)
        with closing(sqlite3.connect(self.mod.DATABASE)) as connection:
            assignment_id, question_file = connection.execute(
                "SELECT id,question_file FROM assignments WHERE title='Bài có hình và toán'").fetchone()
        questions = json.loads((self.root / "questions" / question_file).read_text(encoding="utf-8"))
        self.assertEqual(len(questions[0]["images"]), 2)
        image_name = questions[0]["images"][0]
        image_url = f"/hinh-cau-hoi/{assignment_id}/{image_name}"
        self.assertEqual(self.mod.app.test_client().get(image_url).status_code, 403)
        teacher_image = self.teacher.get(image_url)
        self.assertEqual(teacher_image.mimetype, "image/png")
        teacher_image.close()
        code = self.create_student(1, "Geometry Student")
        child = self.login_student(code)
        exam_url = self.post(child, f"/bai/{assignment_id}/bat-dau", {},
                             f"/bai/{assignment_id}").headers["Location"]
        exam = child.get(exam_url).get_data(as_text=True)
        self.assertIn(image_url, exam)
        self.assertIn(r"\(\frac{1}{2}\)", exam)
        self.assertIn("&lt;script&gt;", exam)
        self.assertNotIn("<script>alert(1)</script>", exam)
        self.assertIn("vendor/katex/katex.min.js", exam)
        student_image = child.get(image_url)
        self.assertEqual(student_image.mimetype, "image/png")
        student_image.close()
        self.assertEqual(self.mod.app.test_client().get(image_url).status_code, 403)
        self.post(self.teacher, "/giao-vien/nhom/tao", {"name":"Lý 12"}, "/giao-vien")
        other_code = self.create_student(2, "Other Group")
        self.assertEqual(self.login_student(other_code).get(image_url).status_code, 403)
        # HTML or SVG disguised as an image must not become a served question image.
        invalid = self.post(self.teacher, "/giao-vien/tao-bai", {
            "title":"Ảnh lỗi", "group_id":"1", "duration_minutes":"10",
            "quiz_json":json.dumps(quiz), "image_1":(io.BytesIO(b'<svg onload="alert(1)"/>'), "hinh.png")})
        self.assertEqual(invalid.status_code, 200)
        self.assertIn("chỉ nhận ảnh PNG", invalid.get_data(as_text=True))
        self.post(self.teacher, f"/giao-vien/bai/{assignment_id}/xoa", {},
                  f"/giao-vien/bai/{assignment_id}")
        self.assertFalse((self.root / "uploads" / "question-images" / image_name).exists())
        self.assertEqual(child.get(image_url).status_code, 404)
        for name in questions[0]["images"]:
            self.assertFalse((self.root / "uploads" / "question-images" / name).exists())


if __name__ == "__main__":
    unittest.main()
