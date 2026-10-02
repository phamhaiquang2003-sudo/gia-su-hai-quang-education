"""Render the standalone static GitHub Pages demo from Jinja templates.

Only fictional data declared here is included; no backend or database is needed.
"""
import argparse
import html as html_helpers
import json
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

ROOT = Path(__file__).resolve().parents[1]

DEMO_QUIZ = [
    {'type': 'mcq', 'prompt': r'Tính giá trị của \(\frac{1}{2}+\frac{1}{4}\).',
     'options': [r'\(\frac{1}{4}\)', r'\(\frac{3}{4}\)', '1', '2'], 'correct': 'B', 'points': 0.25},
    {'type': 'true_false', 'prompt': 'Xác định tính đúng/sai của các khẳng định sau.',
     'statements': [r'\(2^3=8\)', r'\(\sqrt{9}=4\)', r'\(\frac{1}{2}=0{,}5\)', r'\(3+4=6\)'],
     'correct': ['D', 'S', 'D', 'S'], 'points': 1},
    {'type': 'short', 'prompt': 'Một vật dao động điều hòa với chu kỳ T = 0,5 s. Tần số dao động (Hz) là bao nhiêu?',
     'correct': ['2', '2 Hz'], 'points': 0.75},
]


def demo_content():
    """Compile the three fixed sample questions and their example result."""
    questions, grading, review = [], [], []
    selected = ['B', ['D', 'S', 'D', ''], '2']
    for number, sample in enumerate(DEMO_QUIZ, 1):
        kind = sample['type']
        question = dict(number=number, type=kind, content=html_helpers.escape(sample['prompt']), points=sample['points'])
        rule = dict(type=kind, points=sample['points'], correct=sample['correct'])
        chosen = selected[number - 1]
        if kind == 'mcq':
            question['options'] = [dict(key=key, content=html_helpers.escape(text))
                                   for key, text in zip('ABCD', sample['options'])]
            right = chosen == sample['correct']
            awarded = sample['points'] if right else 0
            chosen_text, correct_text = chosen, sample['correct']
        elif kind == 'true_false':
            question['statements'] = [html_helpers.escape(text) for text in sample['statements']]
            rule['scheme'] = 'tf_4_1'
            matches = sum(a == b for a, b in zip(chosen, sample['correct']))
            right, awarded = matches == 4, [0, 0.1, 0.25, 0.5, 1][matches]
            chosen_text = ', '.join(f'{"abcd"[i]}. {value or "—"}' for i, value in enumerate(chosen))
            correct_text = ', '.join(f'{"abcd"[i]}. {value}' for i, value in enumerate(sample['correct']))
        else:
            question['max_length'] = 200
            right = chosen in sample['correct']
            awarded = sample['points'] if right else 0
            chosen_text, correct_text = chosen, '; '.join(sample['correct'])
        questions.append(question)
        grading.append(rule)
        review.append(dict(number=number, chosen=chosen_text, correct=correct_text, right=right,
                           awarded=awarded, max_points=sample['points']))
    return questions, grading, selected, review

PAGE_MAP = {
    'home': 'index.html', 'student_login': 'demo/hoc-sinh.html', 'login': 'demo/dang-nhap.html',
    'dashboard': 'demo/giao-vien.html', 'group_detail': 'demo/nhom.html',
    'student_progress': 'demo/tien-do.html', 'create_assignment': 'demo/soan-de.html',
    'teacher_assignment': 'demo/quan-ly-bai.html', 'student_assignment': 'demo/bai-tap.html',
    'start_attempt': 'demo/lam-bai.html', 'take_exam': 'demo/lam-bai.html',
    'submit': 'demo/ket-qua.html', 'receipt_page': 'demo/ket-qua.html',
    'logout': 'index.html', 'student_logout': 'demo/hoc-sinh.html',
    'create_group': 'demo/giao-vien.html', 'add_student': 'demo/nhom.html',
    'rotate_student_code': 'demo/nhom.html', 'delete_student': 'demo/nhom.html',
    'delete_group': 'demo/giao-vien.html', 'delete_assignment': 'demo/giao-vien.html',
    'update_assignment': 'demo/quan-ly-bai.html', 'save_draft': 'demo/lam-bai.html',
    'export_csv': 'demo/ket-qua.html',
}


def build(output):
    questions, grading, selected, review = demo_content()
    assignment = dict(id=1, title='Bài tập mẫu: Toán & dao động điều hòa',
                      description='Dữ liệu minh họa · 3 dạng câu hỏi · Tổng 2 điểm.', question_count=3,
                      duration_minutes=15, due_at='', filename='', answer_key='', group_id=1,
                      group_name='Lớp minh họa', submission_count=1, is_open=1)
    groups = [dict(id=1, name='Lớp minh họa', student_count=2)]
    roster = [dict(id=1, name='Học sinh mẫu A', completed=1, average_percent=87.5),
              dict(id=2, name='Học sinh mẫu B', completed=0, average_percent=None)]
    score = round(sum(item['awarded'] for item in review), 2)
    roster[0]['average_percent'] = round(score / 2 * 100, 1)
    submitted = dict(id=1, student_name='Học sinh mẫu A', class_name='Lớp minh họa',
                     score=score, submitted_at='2026-10-02T09:00:00+07:00', title=assignment['title'])
    record = dict(id=1, name='Học sinh mẫu A', group_id=1, group_name='Lớp minh họa')
    common = dict(preview_mode=True, groups=groups, assignments=[assignment], assignment=assignment,
                  is_available=lambda item: bool(item['is_open']), csrf_token=lambda: 'public-demo',
                  get_flashed_messages=lambda **kwargs: [], max_score=2, questions=questions,
                  total_points=lambda config: sum(item['points'] for item in config),
                  config_for=lambda item: grading)
    pages = [
        ('home.html', 'home', {}),
        ('student_login.html', 'student_login', {}),
        ('auth.html', 'login', dict(initial=False)),
        ('dashboard.html', 'dashboard', {}),
        ('group.html', 'group_detail', dict(group=groups[0], roster=roster, new_code=None)),
        ('student_progress.html', 'student_progress', dict(record=record, progress=[
            dict(assignment, assignment_id=1, receipt='demo', started_at='', score=score,
                 submitted_at=submitted['submitted_at'])])),
        ('create.html', 'create_assignment', dict(request=SimpleNamespace(form={
            'title': 'Đề minh họa của bạn', 'duration_minutes': 15, 'quiz_json': json.dumps(DEMO_QUIZ)}))),
        ('teacher_assignment.html', 'teacher_assignment', dict(submissions=[(submitted, selected)],
                                                              config_for_legacy=[])),
        ('student_assignment.html', 'student_assignment', dict(available=True, current_attempt=None,
                                                              submitted=None, current_student=record)),
        ('exam.html', 'take_exam', dict(attempt=dict(token='demo', student_name=record['name'],
                                                   class_name=record['group_name']),
                                       remaining=900, draft='', answers=['', ['', '', '', ''], ''])),
        ('receipt.html', 'receipt_page', dict(result=submitted, review=review)),
    ]
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'),
                      autoescape=select_autoescape(['html']), undefined=StrictUndefined)
    navigation = [('home', 'Bài tập'), ('student_login', 'Đăng nhập HS'), ('login', 'Đăng nhập GV'),
                  ('dashboard', 'Giáo viên'), ('group_detail', 'Quản lý lớp'),
                  ('create_assignment', 'Soạn đề'), ('take_exam', 'Làm bài'), ('receipt_page', 'Kết quả')]
    for template, endpoint, context in pages:
        in_demo = endpoint != 'home'
        prefix = '../' if in_demo else ''

        def url_for(name, **values):
            if name == 'static':
                return prefix + 'static/' + values['filename']
            if name not in PAGE_MAP:
                raise ValueError(f'Unmapped preview endpoint: {name}')
            return prefix + PAGE_MAP[name]

        teacher = endpoint in ('dashboard', 'group_detail', 'student_progress',
                               'create_assignment', 'teacher_assignment')
        data = dict(common, **context, url_for=url_for, teacher_logged_in=teacher,
                    student_logged_in=not teacher and endpoint not in ('login', 'student_login'),
                    preview_navigation=[dict(label=label, href=url_for(target), active=target == endpoint)
                                        for target, label in navigation])
        html = env.get_template(template).render(**data)
        if endpoint == 'receipt_page':
            html = html.replace('đã được gửi đến giáo viên.', 'đã được chấm thử trong bản demo.')
        payload = json.dumps(dict(grading=grading, total=2, exampleScore=score, title=assignment['title']), ensure_ascii=False)
        html = html.replace('</body>', '<script id="preview-config" type="application/json">' +
                            payload.replace('<', '\\u003c') + '</script>\n</body>')
        path = output / PAGE_MAP[endpoint]
        path.parent.mkdir(parents=True, exist_ok=True)
        html = '\n'.join(line.rstrip() for line in html.splitlines()) + '\n'
        path.write_text(html, encoding='utf-8', newline='\n')
    (output / '.nojekyll').touch()
    print(f'Built {len(pages)} static preview screens.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT)
    build(parser.parse_args().output)
