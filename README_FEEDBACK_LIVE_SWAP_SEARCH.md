# FitSense — sửa đổi bài tập & tìm kiếm tức thì (12/11/2026)

## Sửa đổi

1. Danh sách thay thế chỉ gồm bài có tác động đến **ít nhất một** trong các nhóm cơ chính hoặc phụ của bài hiện tại; không trả về bài không liên quan để lấp đầy danh sách.
2. Mỗi lựa chọn hiển thị vai trò của bài mới: **Cơ chính** hoặc **Cơ phụ** và tên nhóm cơ trùng khớp. Giữ ưu tiên bảo toàn cơ chính của bài gốc.
3. Chọn một bài thay thế sẽ cập nhật `weekly_schedule` ngay qua callback Streamlit; lưu `exercise_id`, tên, nhóm cơ, dụng cụ, độ khó và hướng dẫn; vẫn giữ số sets/reps/nghỉ của lịch cũ.
4. Key của dropdown thay đổi theo bài hiện tại, ngăn giá trị cũ bị tái sử dụng sau khi thay thế; có placeholder, không tự chọn bài khi mới mở.
5. Tìm kiếm thư viện dùng `st_keyup` với debounce 180ms để lọc ngay trong lúc gõ, không cần Enter. Bổ sung `streamlit-keyup` vào requirements.
6. Giữ tương thích với test/giáo án cũ chỉ có `name` (không có `id`) mà không gây `KeyError`.

## File thay đổi

- `src/exercise_library.py` — phân tích cơ chính/phụ, tạo danh sách thay thế có đánh dấu vai trò và lọc điều kiện.
- `src/planner_view.py` — nhãn dropdown và callback cập nhật lịch theo ID, không cần nút phụ.
- `src/exercise_library_view.py` — tìm kiếm tức thì từng phím.
- `requirements.txt` — thêm dependency `streamlit-keyup>=1.0.0,<2`.
- `tests/test_feedback_live_swap_search.py` — kiểm tra trường hợp cơ chính/cơ phụ, loại bài không liên quan, tên cũ, search và wiring callback.

## Kiểm thử môi trường thực hiện

`python -m pytest tests/test_exercise_library.py tests/test_feedback_28_exercises.py tests/test_feedback_live_swap_search.py -q`

Kết quả: **36 passed, 64 subtests passed**. Kiểm tra cú pháp Python đã qua.
Chưa thể xác nhận trực tiếp AppTest/Streamlit trên máy người dùng vì môi trường build hiện không cài Streamlit.

## Cập nhật dự án Git trên Windows

Đặt ZIP patch đã giải nén ngang cấp với thư mục `CT---FitSense` rồi mở terminal trong `CT---FitSense`:

```powershell
python -m pip install -r requirements.txt
python -m pytest tests/ -q
python -m streamlit run app.py
```

Khi kiểm thử giao diện: dùng bài Hít đất chuẩn; danh sách thay thế phải có Knee Push-up, Bench Dips nhưng **không** có Squat; chọn bài sẽ đổi tên ngay trong giáo án. Kiểm tra ô tìm kiếm bằng cách gõ `hit` và `hit dat` từng ký tự.

**Lưu ý:** File ZIP này xuất phát từ bản FitSense 28 bài và đã tích hợp bản vá `KeyError: 'id'` trước đó. Nếu repository đang có các chỉnh sửa riêng chưa commit, nên áp dụng *patch* sau khi sao lưu và xem `git diff`, không dùng `/MIR`.
