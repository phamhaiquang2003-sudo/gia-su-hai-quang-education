"""Validate three quiz formats and grade submitted answers."""

import html
import json
import re
import unicodedata
from decimal import Decimal, InvalidOperation


def parse_points(value):
    try:
        points = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ValueError("Điểm mỗi câu phải là số từ 0,01 đến 100.")
    if not points.is_finite() or not Decimal("0.01") <= points <= Decimal("100"):
        raise ValueError("Điểm mỗi câu phải là số từ 0,01 đến 100.")
    if points.as_tuple().exponent < -2:
        raise ValueError("Điểm chỉ được có tối đa hai chữ số thập phân.")
    return float(points)


def validate_quiz(raw):
    """Return (public questions, private grading config). Never embed keys in public JSON."""
    try:
        rows = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        raise ValueError("Dữ liệu câu hỏi không hợp lệ. Vui lòng tải lại trang.")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise ValueError("Bài tập cần từ 1 đến 100 câu hỏi.")
    questions, grading = [], []
    for number, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Câu {number} không hợp lệ.")
        kind = row.get("type", "mcq")
        prompt = str(row.get("prompt", "")).strip()
        if not prompt or len(prompt) > 3000:
            raise ValueError(f"Câu {number}: nhập nội dung (tối đa 3000 ký tự).")
        points = 1.0 if kind == "true_false" else parse_points(row.get("points", 1))
        public = {"number": number, "type": kind, "content": html.escape(prompt), "points": points}
        private = {"type": kind, "points": points}
        if kind == "mcq":
            options = row.get("options")
            correct = str(row.get("correct", "")).upper()
            if not isinstance(options, list) or len(options) != 4 or any(not str(x).strip() or len(str(x)) > 1000 for x in options):
                raise ValueError(f"Câu {number}: nhập đủ bốn phương án A, B, C, D.")
            if correct not in "ABCD" or len(correct) != 1:
                raise ValueError(f"Câu {number}: chọn một đáp án đúng A, B, C hoặc D.")
            public["options"] = [{"key": k, "content": html.escape(str(text).strip())}
                                 for k, text in zip("ABCD", options)]
            private["correct"] = correct
        elif kind == "true_false":
            statements = row.get("statements")
            answers = row.get("correct")
            if not isinstance(statements, list) or len(statements) != 4 or any(not str(x).strip() or len(str(x)) > 1000 for x in statements):
                raise ValueError(f"Câu {number}: cần đủ bốn ý a, b, c, d để chấm theo thang điểm đúng/sai.")
            if not isinstance(answers, list) or len(answers) != len(statements) or any(x not in ("D", "S") for x in answers):
                raise ValueError(f"Câu {number}: đánh dấu Đúng hoặc Sai cho từng mệnh đề.")
            public["statements"] = [html.escape(str(text).strip()) for text in statements]
            private["correct"] = answers
            private["scheme"] = "tf_4_1"
        elif kind == "short":
            accepted = row.get("correct")
            if isinstance(accepted, str):
                accepted = [x.strip() for x in accepted.split(";") if x.strip()]
            if not isinstance(accepted, list) or not 1 <= len(accepted) <= 10 or any(not str(x).strip() or len(str(x)) > 200 for x in accepted):
                raise ValueError(f"Câu {number}: nhập đáp án ngắn hợp lệ (có thể cách nhau bởi dấu ;).")
            public["max_length"] = 200
            private["correct"] = [str(x).strip() for x in accepted]
        else:
            raise ValueError(f"Câu {number}: loại câu hỏi không hợp lệ.")
        questions.append(public)
        grading.append(private)
    return questions, grading


def legacy_config(answer_key, count, points=None):
    values = points or [1.0] * count
    if len(answer_key) != count or len(values) != count:
        raise ValueError("Số câu và đáp án không khớp.")
    return [{"type": "mcq", "correct": answer_key[i], "points": parse_points(values[i])}
            for i in range(count)]


def config_for(assignment):
    if assignment["grading_json"]:
        return json.loads(assignment["grading_json"])
    return legacy_config(assignment["answer_key"], assignment["question_count"])


def decode_answers(raw, config):
    if isinstance(raw, list):
        values = raw
    elif isinstance(raw, str) and raw.startswith("["):
        try:
            values = json.loads(raw)
        except ValueError:
            values = []
    else:
        values = list(raw or "")  # Existing one-letter-per-question submissions.
    result = []
    for index, item in enumerate(config):
        value = values[index] if index < len(values) else None
        if item["type"] == "true_false":
            if not isinstance(value, list):
                value = []
            result.append([(v if v in ("D", "S") else "") for v in value[:len(item["correct"])]] +
                          [""] * max(0, len(item["correct"]) - len(value)))
        elif item["type"] == "mcq":
            result.append(value if isinstance(value, str) and value in "ABCD" and len(value) == 1 else "")
        else:
            result.append(str(value or "")[:200] if isinstance(value, str) else "")
    return result


def normalize_short(value):
    text = " ".join(unicodedata.normalize("NFKC", value).strip().casefold().split())
    if re.fullmatch(r"[+-]?\d+(?:[.,]\d+)?", text):
        text = text.replace(",", ".")
        try:
            return str(Decimal(text).normalize())
        except InvalidOperation:
            pass
    return text


def score_quiz(answers, config):
    answers = decode_answers(answers, config)
    review = []
    for number, (chosen, question) in enumerate(zip(answers, config), 1):
        points = float(question["points"])
        correct = question["correct"]
        if question["type"] == "true_false":
            matches = sum(a == b for a, b in zip(chosen, correct))
            # Older quizzes without this scheme keep their original proportional rubric.
            awarded = ((0.0, 0.1, 0.25, 0.5, 1.0)[matches]
                       if question.get("scheme") == "tf_4_1" and len(correct) == 4
                       else round(points * matches / len(correct), 2))
            chosen_display = ", ".join(f"{chr(97+i)}. {x or '—'}" for i, x in enumerate(chosen))
            correct_display = ", ".join(f"{chr(97+i)}. {x}" for i, x in enumerate(correct))
            right = matches == len(correct)
        elif question["type"] == "short":
            right = bool(chosen) and normalize_short(chosen) in {normalize_short(x) for x in correct}
            awarded = points if right else 0.0
            chosen_display = chosen or "—"
            correct_display = "; ".join(correct)
        else:
            right = chosen == correct
            awarded = points if right else 0.0
            chosen_display = chosen or "—"
            correct_display = correct
        review.append({"number": number, "chosen": chosen_display,
                       "correct": correct_display, "right": right,
                       "awarded": awarded, "max_points": points})
    return round(sum(item["awarded"] for item in review), 2), review


def total_points(config):
    return round(sum(float(item["points"]) for item in config), 2)
