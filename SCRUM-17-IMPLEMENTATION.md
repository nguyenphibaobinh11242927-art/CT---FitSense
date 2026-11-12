# SCRUM-17 — Thư viện bài tập Calisthenics

## Những gì đã triển khai

- 16 bài tập Bodyweight/Calisthenics/Cardio có ID cố định, tên Việt/Anh, nhóm cơ chính/phụ, dụng cụ, độ khó, các bước, lỗi thường gặp, ghi chú an toàn và mã bài tập thay thế.
- Dữ liệu nằm tại `data/exercises.json` thay cho danh sách hardcode trong `app.py`.
- `src/exercise_library.py`: kiểm tra tính hợp lệ và liên kết, tìm kiếm không dấu, lọc theo nhóm cơ chính/phụ, độ khó, dụng cụ và loại bài; lựa chọn bài thay thế theo danh mục kiểm duyệt có lọc dụng cụ và hạn chế cổ tay/gối.
- `src/exercise_library_view.py`: giao diện Streamlit, sơ đồ khu vực nhóm cơ trước/sau được vẽ từ mã nguồn, hướng dẫn kỹ thuật và cảnh báo.
- `src/library_view.py`: giữ nguyên API `render_library_view()` để tương thích các trang hiện có.
- 3 GIF gốc, đơn giản hóa chuyển động: squat, nhón bắp chân, jumping jack, nằm trong `assets/exercises/`. Đây không phải tài liệu hướng dẫn giải phẫu chính xác.
- `tests/test_exercise_library.py`: 21 bài test tự động không cần kết nối mạng.

## Các file thay đổi

- `app.py`: **chỉ thay đoạn khởi tạo 5 bài tập mẫu** bằng `load_catalog()`.
- `src/library_view.py`: chuyển sang wrapper điều hướng.
- `src/exercise_library.py`, `src/exercise_library_view.py`: mới.
- `data/exercises.json`: mới.
- `assets/exercises/{squat,jumping_jack,calf_raise}.gif`: mới.
- `tests/test_exercise_library.py`: mới.

## Chạy trên máy

Dùng môi trường Python tương thích với dependencies của nhóm (README nhóm đề xuất Python 3.12):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_exercise_library.py' -v
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Lưu ý cần Lead review

1. GIF chỉ có cho 3/16 bài; các bài còn lại **không sử dụng video/GIF ngoài chưa được kiểm chứng**. Cần bổ sung media đã cấp quyền/kiểm duyệt trước khi coi DoD hình động đạt toàn bộ thư viện.
2. Sơ đồ cơ là mô hình trực quan giản lược, chưa phải atlas giải phẫu đầy đủ. Nên thay bằng asset giải phẫu được cấp phép nếu nhóm yêu cầu chuẩn chuyên nghiệp.
3. Tính năng chọn bài thay thế **không phải chỉ dẫn y khoa**. Nhãn `avoid_if` là giới hạn bảo thủ của bản mẫu; cần chuyên gia/Lead duyệt trước khi dùng làm tư vấn tập luyện thực tế.
4. Luồng `weekly_schedule` trong `app.py` vẫn sử dụng dữ liệu lịch tập riêng của nhóm; SCRUM-17 không thay đổi planner.
5. Không thay đổi hệ thống tài khoản, profile hoặc những file không liên quan.
