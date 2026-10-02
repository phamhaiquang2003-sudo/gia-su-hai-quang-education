"""Fictional catalog cards used to demonstrate search, filters and layout."""

SUBJECTS = [
    dict(key='toan-hoc', label='Toán Học'), dict(key='vat-ly', label='Vật Lý'),
    dict(key='hoa-hoc', label='Hóa Học'), dict(key='tin-hoc', label='Tin Học'),
    dict(key='hsa', label='Đề thi HSA/TSA'), dict(key='thpt', label='Thi thử TNTHPT'),
]

COVERS = {
    'notes.jpg': 'Những tờ báo và tài liệu xếp cạnh nhau',
    'laboratory.jpg': 'Dụng cụ thí nghiệm trong phòng nghiên cứu',
    'earth.jpg': 'Trái Đất nhìn từ không gian',
    'light.jpg': 'Đèn bàn chiếu sáng',
    'space.jpg': 'Bầu trời đêm và những vì sao',
    'science.jpg': 'Quả cầu plasma với những tia sáng điện',
    'computer.jpg': 'Máy tính và không gian học tập',
}

# Card counts/times/prices describe illustrative listings, not real published exams.
# All cards open the clearly labeled three-question practice demo.
CATALOG = []
for index, (subject, title, tags, badge, image, count, duration, price, popularity) in enumerate([
    ('vat-ly', 'Bài Kiểm Tra Vật Lý Nhiệt – Lớp 12 – Lần 1', ['12'], 'Lớp 12', 'notes.jpg', 40, 45, 0, 1820),
    ('vat-ly', 'Đề Thi Thử TNTHPT Môn Vật Lý – Đề Số 01', ['thpt', '12'], 'Thi thử TNTHPT', 'science.jpg', 40, 50, 0, 2640),
    ('vat-ly', 'Đề Ôn Tập Đánh Giá Năng Lực (HSA) – Vật Lý', ['hsa', '12'], 'Đề thi HSA/TSA', 'laboratory.jpg', 50, 60, 49000, 1350),
    ('vat-ly', 'Bài Kiểm Tra Dao Động Cơ – Vật Lý 12 Giữa Kỳ I', ['12'], 'Lớp 12', 'space.jpg', 30, 45, 0, 1920),
    ('vat-ly', 'Trắc Nghiệm Dòng Điện Xoay Chiều Nâng Cao', ['12'], 'Lớp 12', 'earth.jpg', 40, 50, 29000, 980),
    ('vat-ly', 'Tổng Ôn Quang Hình Học – Vật Lý Lớp 11', ['11'], 'Lớp 11', 'light.jpg', 40, 45, 0, 1470),
    ('vat-ly', 'Đề Thi Thử TNTHPT Môn Vật Lý – Đề Số 02', ['thpt', '12'], 'Thi thử TNTHPT', 'science.jpg', 40, 50, 39000, 810),
    ('toan-hoc', 'Bài Kiểm Tra Hàm Số Và Đồ Thị – Toán 12', ['12'], 'Lớp 12', 'notes.jpg', 35, 45, 0, 2310),
    ('toan-hoc', 'Đề Ôn Tập Tư Duy Định Lượng HSA/TSA', ['hsa', '12'], 'Đề thi HSA/TSA', 'computer.jpg', 40, 60, 39000, 1410),
    ('toan-hoc', 'Đề Thi Thử TNTHPT Môn Toán – Đề Số 01', ['thpt', '12'], 'Thi thử TNTHPT', 'space.jpg', 40, 90, 0, 3540),
    ('hoa-hoc', 'Trắc Nghiệm Cấu Tạo Nguyên Tử – Hóa Học 10', ['10'], 'Lớp 10', 'science.jpg', 30, 30, 0, 620),
    ('hoa-hoc', 'Đề Ôn Tập Hóa Hữu Cơ – Hóa Học 12', ['12'], 'Lớp 12', 'laboratory.jpg', 40, 50, 29000, 1090),
    ('tin-hoc', 'Bài Kiểm Tra Tư Duy Lập Trình – Tin Học 10', ['10'], 'Lớp 10', 'computer.jpg', 25, 30, 0, 890),
    ('tin-hoc', 'Ôn Tập Cơ Sở Dữ Liệu – Tin Học 11', ['11'], 'Lớp 11', 'computer.jpg', 30, 45, 0, 530),
]):
    CATALOG.append(dict(id=index + 1, subject=subject, title=title, tags=tags, category_label=badge,
                        image=image, image_alt=COVERS[image], count=count, duration=duration,
                        price=price, popularity=popularity, order=100 - index, teacher='Thầy Hải Quang'))
