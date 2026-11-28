# Action Engine – Sprint 4

Lead: M03 – Đậu Cao Dũng. Review: M04 – Nguyễn Diệp Vĩnh Khang. 2.5 SP.

## Phạm vi và tích hợp

Bản nền: CT---FitSense-main(1).zip (các entry mang ngày 24/11/2026). Bản này có mascot nhưng chưa có chat API SCRUM-29. Chưa xác minh branch SCRUM-29 hoặc main hiện tại. Không sửa các file SCRUM-24 trong gói này. So sánh từng file với branch hiện tại trước khi áp dụng, đặc biệt backend/main.py, backend/routers/planner.py và frontend/js/views/planner.js. Nếu SCRUM-29 đã có POST /api/capybara/chat, tích hợp logic của router mới vào endpoint đó, không đăng ký hai endpoint trùng đường dẫn.

## Hành vi

- POST /api/capybara/chat, body {"message":"đau đầu gối"}, hoặc "dời lịch thứ 4 sang thứ 5", hoặc "giảm tải". Yêu cầu đăng nhập theo CURRENT_SESSION hiện có. Parser rule-based cho câu lệnh rõ ràng, không cần LLM; không phải chatbot hội thoại tổng quát. Câu không nhận diện được không thay đổi dữ liệu.
- Chấn thương: hỗ trợ knee, wrist (tag có trong catalog); lọc chống chỉ định, dụng cụ, độ khó; ưu tiên alternatives trong catalog, rồi điểm giao nhóm cơ chính/phụ. Chỉ ngày hiện tại trở đi, bỏ qua ngày hoàn thành hoặc đang tập. Squat -> Glute Bridge khi có thảm theo catalog và có Squat trong lịch còn lại. Không có thảm có thể chọn phương án khác theo bộ lọc hoặc tạm ngừng. Đây là quy tắc dữ liệu, không bảo đảm y khoa; cần reviewer kiểm tra. Bài không xác định hoặc không có ứng viên được đánh dấu paused; giao diện Planner và endpoint start-day-workout chặn cả buổi có bài tạm ngừng cho đến khi chỉnh lại kế hoạch.
- Hoán đổi cả kế hoạch, giữ tên ngày; từ chối ngày đã hoàn thành/đang tập. Ngày chưa đánh dấu hoàn thành có thể đổi theo yêu cầu kể cả ngày đã qua. Lịch sử workout không bị ghi đè.
- Deload: hôm nay, rep nguyên dương nhân 7 chia nguyên 10, tối thiểu 1; giữ kiểu int hoặc chuỗi số; bỏ qua bài theo thời gian, bài tạm ngừng, ngày nghỉ, đang tập/đã hoàn thành. Cờ instant_deload_applied tránh giảm lặp trên cùng kế hoạch.
- Response: success, action, diff, schedule, message, partial. Injury/deload diff có target_day, exercise_index, old_exercise, new_exercise (null nếu paused); move diff có old_day/new_day cho hai ngày.
- JSON: data/private/api_weekly_plans/<hash-email>_<monday>.json, ghi file tạm rồi os.replace. Đồng bộ USER_SCHEDULES sau khi ghi thành công. Planner đọc file khi cache chưa có và đồng bộ các thao tác sửa lịch của Planner nếu file đã tồn tại. Không ghi dữ liệu guest. Thư mục đã được gitignore.

## Kiểm thử

`python -m pytest tests/test_capybara_api.py -v`: 30 passed trên Python 3.13, FastAPI TestClient dùng router thật, thay adapter đăng nhập/profile/cache bằng dữ liệu giả lập, ghi JSON thật vào tmp_path. Không gọi mô hình AI. Bao gồm parser, knee, move, deload, quyền truy cập giả lập, JSON hỏng và lỗi ghi.

`python -m pytest -q`: chưa hoàn tất, 8 lỗi collection do thiếu Streamlit/MediaPipe. Chưa xác nhận hồi quy, chưa chạy app đầy đủ. Python compileall và Node syntax check: thành công.

## Checklist trên máy người thực hiện

1. Cập nhật branch làm việc dựa trên main/branch SCRUM-29 đã thống nhất với nhóm, giữ nguyên SCRUM-24. Kiểm tra diff trước khi copy file.
2. Chạy hai lệnh pytest trên; chạy `python run_server.py`, mở http://localhost:8000/docs. Đăng nhập tài khoản test, có thảm và lịch có Squat chưa thực hiện; thử ba câu lệnh ở trên, so sánh GET /api/planner/week và JSON. Thử hoán đổi ngày nghỉ, không có thảm, lặp deload, không đăng nhập. Chỉ đánh dấu PASS sau khi thực hiện.
3. Kiểm tra giao diện Planner không cho bắt đầu buổi có paused. Chat UI SCRUM-29/31 chưa có trong bản nền nên chưa xác minh cập nhật action card tự động.
4. Khang review thuật toán, chạy test cục bộ, approve. Chưa có approve.

## Giới hạn đã biết

- CURRENT_SESSION là biến toàn cục có sẵn của app demo; chưa có xác thực độc lập theo từng HTTP client. Không tuyên bố bảo mật đa người dùng production. Lock chỉ tuần tự hóa các chat action trong một process; chưa bao phủ các router khác hay multi-worker. Cache tuần của app gốc không tự rollover khi process đang chạy; cần restart/đồng bộ với kiến trúc mới. Adaptive evaluation trong progress router hiện sửa cache trực tiếp; chưa đồng bộ riêng xuống file action để tránh xung đột SCRUM-24. Cần thống nhất storage chung với nhóm trước khi merge.
- Trạng thái hoàn thành dựa vào is_completed/workout_status của kế hoạch; app nền có lịch sử workout riêng, chưa xác minh mọi đường cập nhật cờ hoàn thành. Không phải bảo đảm tất cả buổi đã tập được phát hiện.
- Thao tác không rõ ràng, nhiều chấn thương cùng lúc, hội thoại dài, tỷ lệ deload tùy chỉnh chưa hỗ trợ. Không tự thay đổi dữ liệu khi chưa nhận diện rõ.
- Cờ deload đi cùng nội dung buổi khi hoán đổi; chỉnh sửa/reset kế hoạch có thể đặt lại cờ. Không phải cơ chế idempotency tổng quát cho move.
