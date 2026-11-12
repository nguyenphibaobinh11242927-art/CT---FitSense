# FitSense – bản cập nhật 28 bài tập (12/11/2026)

## Phạm vi

Bản phát hành này được tạo từ `CT---FitSense-main (1).zip` của người dùng. **Không tự động gộp các thay đổi trên branch Git cục bộ của bạn**. Nếu branch hiện tại có tính năng mới khác bản ZIP, hãy review diff và sao lưu trước khi chép đè.

### Đã sửa

1. `data/exercises.json`: tăng từ 16 lên đúng 28 bài có mã ID duy nhất, tên Việt–Anh, nhóm cơ chính/phụ, dụng cụ, mức độ, các bước thực hiện, lỗi thường gặp, lưu ý an toàn. Phủ đủ 8 nhóm hiển thị: ngực, lưng, vai, tay, core, mông, đùi, bắp chân. Các nhóm có thể chồng lấn.
2. `src/exercise_library.py`: giữ API tìm kiếm cũ; thêm `compatible_replacements`, `resolve_exercise` nhận tên kế hoạch cũ; `suggest_alternatives` tìm thêm theo nhóm cơ chính/phụ nếu các lựa chọn định sẵn đều không đáp ứng, vẫn tôn trọng hạn chế đã khai báo và dụng cụ.
3. `src/planner_view.py`: dropdown đổi bài lấy từ danh mục thật theo nhóm cơ, dùng `exercise_id` và đồng bộ tên, nhóm cơ chính/phụ, dụng cụ, độ khó, hướng dẫn; tránh gợi ý chuỗi giả chưa có trong catalogue. Có xét dụng cụ/hạn chế hồ sơ.
4. `src/exercise_library_view.py`: loại bỏ hình người que trong luồng hiển thị, dùng mô hình giải phẫu **dạng hình khối người** phía trước/sau, tô màu cơ chính/phụ. Hướng dẫn chi tiết mở theo lựa chọn thay vì mở hết cùng lúc. Có liên kết thư viện hướng dẫn hình ảnh ACE.
5. `tests/test_feedback_28_exercises.py`: regression test cho số bài, 8 nhóm cơ, đổi bài, tên cũ trong giáo án và các quy tắc danh mục.

### Giới hạn quan trọng

- **Không có 28 GIF/video người thật đóng gói offline**. Các GIF người que cũ không được trình bày trong giao diện mới. Để không sử dụng hình ảnh có bản quyền sai phép hoặc animation mô tả sai kỹ thuật, giao diện dùng hình cơ thể minh họa không phải người que, hướng dẫn từng bước và liên kết ra thư viện ảnh của ACE. Muốn dùng GIF/video người thật nội bộ cho từng bài cần chọn nguồn có quyền tái sử dụng, tải đúng media và ghi attribution cụ thể.
- Hình SVG tự dựng chỉ là minh họa phân bố nhóm cơ tương đối, không thay thế hình giải phẫu chính xác và không mô phỏng động tác.
- Đã chạy kiểm thử không phụ thuộc UI: `35 passed, 60 subtests passed` và kiểm tra cú pháp Python. Một số test giao diện/video không chạy được trong môi trường đóng gói vì thiếu `streamlit` và `mediapipe`. Cần thử `python -m pytest tests/ -q` và `python -m streamlit run app.py` trên Windows của bạn.
- Thư viện 28 bài không đồng nghĩa 28 bài đều phù hợp thể trạng; giao diện chỉ gợi ý theo điều kiện đã khai báo. Một số bài có thể không được gợi ý nếu người dùng bị hạn chế khớp hoặc thiếu dụng cụ.

### Nguồn nghiên cứu tham khảo

- ACE Fitness – Exercise Library: https://www.acefitness.org/resources/everyone/exercise-library/ (hướng dẫn kỹ thuật và ảnh, không sao chép ảnh vào ZIP)
- Wikimedia Commons – `Muscles front and back.svg` (OpenStax / Tomáš Kebert / umimeto.org; CC BY-SA 4.0): https://commons.wikimedia.org/wiki/File:Muscles_front_and_back.svg (dẫn link tham khảo, không đưa tác phẩm này vào ZIP)

### Cài đặt lên repository hiện có

Đặt thư mục bản vá cạnh thư mục `CT---FitSense` (cùng cấp trong `Project`). Từ PowerShell tại `Project/CT---FitSense`, chạy:

```powershell
git status
robocopy "..\FitSense_28_Patch" "." /E /R:1 /W:1 /XD .git .venv __pycache__ .pytest_cache
python -m pytest tests/ -q
python -m streamlit run app.py
```

**Lưu ý:** Không dùng `/MIR` hoặc `/PURGE`; `robocopy` exit code 0–7 thường không phải lỗi. Sao lưu trước những sửa đổi chưa commit. Sau đó kiểm tra `git diff --stat` và `git status` trước khi commit.
