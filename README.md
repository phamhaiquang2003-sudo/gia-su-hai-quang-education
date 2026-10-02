# gia-su-hai-quang-education

Demo giao diện website bài tập của Gia sư Hải Quang, chạy độc lập trên **GitHub Pages** bằng HTML, CSS và JavaScript.

## Mở website

**[Mở website demo →](https://phamhaiquang2003-sudo.github.io/gia-su-hai-quang-education/)**

Học sinh có thể mở bản demo này mà không cần máy giáo viên bật.

### Các màn hình

- Trang danh sách bài tập, đăng nhập học sinh và đăng nhập giáo viên bằng thông tin mẫu.
- Trang giáo viên, quản lý lớp, quản lý bài tập và theo dõi tiến độ mẫu.
- Soạn đề với ba dạng câu hỏi, kho 111 mẫu LaTeX, chọn ảnh và dán ảnh vào câu hỏi.
- Làm đề mẫu có đồng hồ, tự lưu câu trả lời trong phiên trình duyệt và nộp bài sớm.
- Xem điểm và đối chiếu đáp án; đúng/sai bốn ý dùng thang điểm 0 / 0,1 / 0,25 / 0,5 / 1.

Thanh **DEMO GIAO DIỆN** giúp chuyển giữa các màn hình. Có thể làm thử và xem điểm ngay trên trình duyệt.

**Đây là demo với dữ liệu minh họa.** Biểu mẫu quản lý chưa tạo nhóm, cấp mã hoặc đăng đề thật; điểm làm thử không gửi cho giáo viên và không đồng bộ sang thiết bị khác. Không nhập mật khẩu hoặc thông tin học sinh thật vào demo.

### Giao diện học sinh

![Trang bài tập học sinh](docs/screenshots/hoc-sinh.png)

### Giao diện giáo viên

![Trang quản lý bài tập của giáo viên](docs/screenshots/giao-vien.png)

[Xem trang soạn đề](https://phamhaiquang2003-sudo.github.io/gia-su-hai-quang-education/demo/soan-de.html) · [Làm thử đề mẫu](https://phamhaiquang2003-sudo.github.io/gia-su-hai-quang-education/demo/lam-bai.html)

## Mã nguồn và cập nhật

```powershell
git clone https://github.com/phamhaiquang2003-sudo/gia-su-hai-quang-education.git
cd gia-su-hai-quang-education
```

Trong bản đã clone, cập nhật bằng `git pull --ff-only`.

## Chỉnh sửa giao diện

Các trang tĩnh được tạo từ `templates/` bằng Jinja2. Python chỉ dùng khi chỉnh sửa/xây dựng giao diện; người xem website không cần Python hoặc máy chủ trên máy giáo viên.

```powershell
py -m pip install -r requirements.txt
py scripts/build_pages.py
py -m unittest discover -s tests -v
```

- `templates/`: mẫu giao diện.
- `static/`: CSS, JavaScript và thư viện KaTeX lưu cục bộ.
- `scripts/build_pages.py`: dựng 11 trang bằng dữ liệu mẫu, không dùng cơ sở dữ liệu.
- `index.html`, `demo/`: trang HTML được xuất để GitHub Pages phục vụ.
- `docs/screenshots/`: ảnh giao diện.

Sau khi sửa mẫu, chạy lại trình dựng rồi commit các tệp đã thay đổi. GitHub Actions kiểm tra đường dẫn và đảm bảo bản HTML đã cập nhật.

GitHub Pages dùng **Deploy from a branch → main → / (root)**. Tệp `.nojekyll` và `index.html` giúp trang chủ hiển thị giao diện website.

## Trạng thái dự án

Bản máy chủ Flask, dữ liệu lớp/đề thật và các tệp chạy máy chủ đã được gỡ khỏi phiên bản hiện tại. Dự án hiện chỉ giữ bản demo GitHub Pages.
