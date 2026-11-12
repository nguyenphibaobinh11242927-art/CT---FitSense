# FitSense — AI Fitness & Workout Assistant

Hệ thống Trợ lý AI hỗ trợ rèn luyện Thể dục Thể thao & Calisthenics thích ứng thông minh.  
**Môn học:** CSC10014 — Tư duy Tính toán (Computational Thinking) — HCMUS.

---

## ✨ Các tính năng chính

1. **Tài khoản & Hồ sơ Thể chất ([`src/auth_view.py`](src/auth_view.py), [`src/profile.py`](src/profile.py), [`src/profile_view.py`](src/profile_view.py)):**
   - Quản lý đăng nhập / đăng ký, tính chỉ số BMI, mục tiêu tập luyện, dụng cụ hiện có và các hạn chế vận động / chấn thương.
2. **Kế hoạch Tập luyện Tuần & FIT-AI ([`src/planner_view.py`](src/planner_view.py), [`src/planner_generation.py`](src/planner_generation.py), [`src/school_ai.py`](src/school_ai.py), [`src/adaptive_weekly_plan.py`](src/adaptive_weekly_plan.py)):**
   - Sinh giáo án tuần 7 ngày cá nhân hóa bằng **HCMUS FIT-AI (`Qwen-27B`)**, lọc sẵn bài tập hợp lệ theo dụng cụ và chấn thương.
   - Đổi bài tập thay thế theo nhóm cơ chính/phụ, hỗ trợ tải lên giáo án (`.json` / `.csv`), chỉnh sửa từng ngày, cảnh báo phục hồi và lưu trạng thái hoàn thành.
3. **Thư viện 28 Bài tập Calisthenics ([`src/exercise_library.py`](src/exercise_library.py), [`src/exercise_library_view.py`](src/exercise_library_view.py), [`data/exercises.json`](data/exercises.json)):**
   - Tìm kiếm tức thì theo tên tiếng Việt / tiếng Anh / nhóm cơ (`streamlit-keyup` với debounce 180ms), lọc đa tiêu chí và sơ đồ giải phẫu minh họa cơ chính/phụ mặt trước & sau.
4. **Phòng tập Rảnh tay (HUD) & AI Pose Tracking ([`src/session_view.py`](src/session_view.py), [`src/pose_tracking.py`](src/pose_tracking.py), [`src/fsm_gestures.py`](src/fsm_gestures.py), [`src/fsm_rep_counter.py`](src/fsm_rep_counter.py), [`assets/webcam/`](assets/webcam/)):**
   - Chạy **MediaPipe Pose Landmarker** trực tiếp trên trình duyệt, nhận diện cử chỉ **giơ tay bắt đầu** và **chữ X kết thúc**, đếm rep tự động bằng FSM, kèm **Chế độ Tự do** không cần camera.
   - Tích hợp **Voice Coach tiếng Việt** ([`assets/webcam/voice_coach.mjs`](assets/webcam/voice_coach.mjs)) và thú cưng đồng hành **Capybara** ([`src/capybara_widget.py`](src/capybara_widget.py)).
5. **Đánh giá Sau Buổi tập, Heatmap & Tiến độ ([`src/evaluation_view.py`](src/evaluation_view.py), [`src/heatmap_view.py`](src/heatmap_view.py), [`src/progress_view.py`](src/progress_view.py)):**
   - Ghi nhận cảm nhận RPE, bản đồ nhiệt phục hồi từng nhóm cơ và theo dõi chuỗi ngày duy trì (Streak tối thiểu 70%).

---

## 🚀 Cài đặt & Khởi chạy

Khuyến nghị **Python 3.10 – 3.12+** (mở terminal tại thư mục gốc dự án):

### 1. Tạo môi trường ảo & cài đặt thư viện
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```
*(Trên Linux/macOS dùng `source .venv/bin/activate` thay cho `Activate.ps1`.)*

### 2. Cấu hình `FITAI_API_KEY` (cho tính năng tạo giáo án FIT-AI)
Tham khảo [`.env.example`](.env.example) và [hướng dẫn FIT-AI](https://www.fit.hcmus.edu.vn/llm-services/). Đặt biến môi trường trước khi chạy Streamlit:

```powershell
# Windows PowerShell:
$env:FITAI_API_KEY = "<API_KEY_CUA_BAN>"
```
```bash
# Linux / macOS / WSL:
export FITAI_API_KEY="<API_KEY_CUA_BAN>"
```

### 3. Khởi chạy ứng dụng FitSense
```powershell
python -m streamlit run app.py
```
*(Tùy chọn kiểm tra Pose Tracking độc lập bằng Python: `python -m src.pose_tracking`.)*

---

## 📂 Cấu trúc Mã nguồn

```text
app.py                         # Điểm chạy Streamlit chính, điều hướng Sidebar & theme Dark/Light
config.py                      # Cấu hình dùng chung của ứng dụng
requirements.txt               # Danh sách thư viện Python (Streamlit, Pandas, Requests, MediaPipe, ...)
.env.example                   # Mẫu biến môi trường (FITAI_API_KEY)
data/
└── exercises.json             # Danh mục 28 bài tập Calisthenics chuẩn hóa JSON Schema
models/
└── pose_landmarker_lite.task  # Model MediaPipe Pose chạy trên trình duyệt / Python
assets/
├── exercises/                 # Media minh họa bài tập
└── webcam/                    # Thành phần Streamlit webcam, MediaPipe WASM & Voice Coach JS
src/
├── auth_view.py               # Đăng nhập / Đăng ký tài khoản
├── profile.py                 # Xử lý dữ liệu & lưu hồ sơ người dùng
├── profile_view.py            # Giao diện Hồ sơ Thể chất & Hạn chế Vận động
├── planner_view.py            # Giao diện Lập lịch Tuần, đổi bài & chỉnh sửa giáo án
├── planner_generation.py      # Chuẩn hóa & sinh giáo án tuần từ AI
├── school_ai.py               # Kết nối API HCMUS FIT-AI (Qwen-27B)
├── workout_planner.py         # Quy tắc & kiểm định cấu trúc giáo án
├── adaptive_weekly_plan.py    # Sắp xếp lại lịch tuần thích ứng & cảnh báo phục hồi
├── weekly_plan_sync.py        # Đồng bộ trạng thái buổi tập với lịch tuần
├── weekly_plan_storage.py     # Lưu / khôi phục trạng thái kế hoạch tuần
├── exercise_library.py        # Logic tìm kiếm, lọc và gợi ý bài thay thế theo nhóm cơ
├── exercise_library_view.py   # Giao diện thư viện 28 bài tập & sơ đồ cơ giải phẫu
├── library_view.py            # Wrapper điều hướng Thư viện Bài tập
├── session_view.py            # Phòng tập Trực tiếp (HUD) & điều phối phiên webcam
├── workout_session.py         # Quản lý trạng thái phiên tập (active/paused/completed)
├── pose_tracking.py           # Nhận diện tư thế & tính góc khớp bằng MediaPipe
├── fsm_gestures.py            # FSM nhận diện cử chỉ bắt đầu (giơ tay) & dừng (chữ X)
├── fsm_rep_counter.py         # FSM đếm số rep & kiểm tra độ sâu squat
├── evaluation_view.py         # Đánh giá sau buổi tập (RPE)
├── heatmap_view.py            # Bản đồ nhiệt phục hồi nhóm cơ
├── progress_view.py           # Thống kê tiến độ & Streak
└── capybara_widget.py         # Widget Capybara đồng hành
tests/                         # Bộ kiểm thử Python (`unittest`) và JS (`node --test`)
docs/                          # Báo cáo kiến trúc, bảng phân công & biên bản nghiệm thu
```

---

## 🧪 Chạy Kiểm thử (Tests)

Chạy toàn bộ unit test Python từ thư mục gốc:
```powershell
python -m unittest discover -s tests -v
```

Chạy unit test JavaScript cho Voice Coach & Webcam Session (yêu cầu Node.js, xem thêm [`tests/README.md`](tests/README.md)):
```powershell
node --test tests/test_voice_coach.mjs tests/test_webcam_session.mjs
```

---

## 🔗 Liên kết Dự án

- **Jira Board:** https://ratatouille2026.atlassian.net (Project: `FitSense - AI Fitness & Workout Assistant`, Key: `SCRUM`)
- **Nhánh chính:** `main`
- **Tài liệu:** [`docs/`](docs/)
