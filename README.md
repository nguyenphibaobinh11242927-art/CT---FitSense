# FitSense — AI Fitness & Workout Assistant

Hệ thống Trợ lý AI hỗ trợ rèn luyện Thể dục Thể thao & Calisthenics thích ứng thông minh.  
**Môn học:** CSC10014 — Tư duy Tính toán (Computational Thinking) — HCMUS.  
**Kiến trúc hệ thống:** Decoupled Architecture (FastAPI REST Backend + Modern HTML5/CSS3/ES6 JavaScript Web Client).

---

## ✨ Các tính năng chính

1. **Tài khoản, Xác thực & Hồ sơ Thể chất ([`backend/routers/auth.py`](backend/routers/auth.py), [`backend/routers/profile.py`](backend/routers/profile.py), [`src/profile.py`](src/profile.py)):**
   - Quản lý đăng ký, đăng nhập an toàn và đăng nhập một chạm qua **Google OAuth**.
   - Tính toán chỉ số BMI tự động, quản lý mục tiêu rèn luyện, dụng cụ hiện có và hồ sơ thể trạng.
   - **Tự động thích ứng hạn chế vận động:** Khi người dùng cập nhật hạn chế mới (khớp gối yếu, đau lưng, cổ tay đau,...), hệ thống tự động rà soát và thay thế bài tập trong giáo án bằng các bài tập an toàn, tương thích nhóm cơ.

2. **Kế hoạch Tập luyện Tuần & FIT-AI ([`backend/routers/planner.py`](backend/routers/planner.py), [`src/planner_generation.py`](src/planner_generation.py), [`src/school_ai.py`](src/school_ai.py), [`src/adaptive_weekly_plan.py`](src/adaptive_weekly_plan.py)):**
   - Tự động sinh giáo án tuần 7 ngày cá nhân hóa bằng **HCMUS FIT-AI (`Qwen-27B`)** hoặc thuật toán heuristic dự phòng.
   - **Tái cấu trúc lịch thông minh khi tập lệch ngày:** Cho phép chọn tập buổi khác thay cho hôm nay, AI tự động chuyển buổi tập và sắp xếp lại các ngày còn lại trong tuần để cân bằng nhóm cơ & ngày nghỉ sinh học.
   - Hỗ trợ đổi bài tập tương đương theo nhóm cơ chính/phụ, nạp giáo án cá nhân từ file (`.json` / `.csv`), cảnh báo phục hồi cơ bắp và lưu trạng thái hoàn thành.

3. **Thư viện 28 Bài tập Calisthenics Chuẩn hóa ([`backend/routers/exercises.py`](backend/routers/exercises.py), [`data/exercises.json`](data/exercises.json), [`src/exercise_library.py`](src/exercise_library.py)):**
   - Danh mục 28 bài tập Calisthenics chuẩn hóa theo JSON Schema với sơ đồ giải phẫu cơ bắp chi tiết (mặt trước & sau).
   - Bộ lọc đa tiêu chí (độ khó, nhóm cơ, thiết bị) kết hợp tìm kiếm tức thì theo tên tiếng Việt và tiếng Anh.

4. **Phòng tập Rảnh tay (Cyber-HUD) & AI Pose Tracking ([`backend/routers/session.py`](backend/routers/session.py), [`src/fsm_rep_counter.py`](src/fsm_rep_counter.py), [`src/fsm_gestures.py`](src/fsm_gestures.py), [`assets/webcam/`](assets/webcam/)):**
   - AI Pose Tracking bằng **MediaPipe Pose Landmarker** trực tiếp trên trình duyệt client với độ trễ thấp (WASM/WebGL).
   - Nhận diện cử chỉ rảnh tay: **Giơ tay bắt đầu** và **Chữ X dừng khẩn cấp** phiên tập.
   - Máy trạng thái hữu hạn (FSM) đếm rep chuẩn xác theo góc khớp động học, khóa số rep AI đối chiếu, kèm **Chế độ Không dùng Camera** cho người tập tự do.
   - Tích hợp **Voice Coach giọng nói tiếng Việt** hướng dẫn kỹ thuật thời gian thực và thú cưng **Capybara Mascot** đồng hành.

5. **Đánh giá Sau Buổi tập, Adaptive AI Deload & Ma trận Phục hồi Sinh học ([`backend/routers/progress.py`](backend/routers/progress.py), [`src/adaptive_weekly_plan.py`](src/adaptive_weekly_plan.py)):**
   - Khảo sát mức độ gắng sức RPE (thang đo Borg 1 - 10) và vùng cơ mỏi sau buổi tập.
   - **Tỉ lệ hoàn thành do AI đối chiếu:** Đo đạc khách quan và cố định (`AI Verified`), tự động kích hoạt chiến lược thích ứng tải trọng (Tăng tiến Overload +10%, Giảm tải Deload -15%, hoặc Duy trì Optimal Maintenance).
   - Khối khuyến nghị Adaptive AI tự động hiển thị sau khi hoàn tất khảo sát.
   - Ma trận bản đồ nhiệt theo dõi chu kỳ phục hồi của 7 nhóm cơ và chuỗi ngày rèn luyện (Streak công bằng $\ge 50\%$).

---

## 🚀 Cài đặt & Khởi chạy

Khuyến nghị môi trường **Python 3.10 – 3.12+** (mở terminal tại thư mục gốc dự án):

### 1. Tạo môi trường ảo & cài đặt thư viện
```bash
# Tạo môi trường ảo
python -m venv .venv

# Kích hoạt môi trường ảo:
# Trên Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Trên Linux / macOS / WSL:
source .venv/bin/activate

# Cài đặt các gói phụ thuộc
pip install -r requirements.txt
```

### 2. Cấu hình biến môi trường (Tùy chọn)
Tham khảo [`.env.example`](.env.example) và [hướng dẫn HCMUS FIT-AI](https://www.fit.hcmus.edu.vn/llm-services/). Nếu muốn sử dụng AI School để sinh giáo án tuần:

```powershell
# Windows PowerShell:
$env:FITAI_API_KEY = "<API_KEY_CUA_BAN>"
```
```bash
# Linux / macOS / WSL:
export FITAI_API_KEY="<API_KEY_CUA_BAN>"
```

### 3. Khởi chạy Ứng dụng Web FitSense
Chạy máy chủ ứng dụng FastAPI phục vụ toàn bộ Web Client và REST API:

```bash
python run_server.py
```

*(Bạn cũng có thể khởi chạy bằng lệnh Uvicorn: `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload`)*

* **Ứng dụng Web chính thức:** [http://localhost:8000](http://localhost:8000)
* **Tài liệu API tương tác (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Tài liệu API ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📂 Cấu trúc Mã nguồn Dự án

```text
run_server.py                  # Script khởi chạy toàn bộ dịch vụ FitSense (FastAPI + Web Client)
backend/                       # Backend REST API (FastAPI)
├── main.py                    # Khởi tạo FastAPI app, định tuyến router, CORS, cache headers & mount static files
├── schemas.py                 # Pydantic schemas kiểm định request/response
└── routers/
    ├── auth.py                # API Đăng nhập, Đăng ký, Google OAuth & Phiên làm việc
    ├── profile.py             # API Hồ sơ thể chất, tính BMI & tự động thích ứng hạn chế vận động
    ├── exercises.py           # API Thư viện 28 bài Calisthenics & gợi ý bài thay thế
    ├── planner.py             # API Kế hoạch tuần 7 ngày, đổi bài, sinh giáo án & re-plan thông minh
    ├── session.py             # API Quản lý phiên tập, FSM rep counter theo góc khớp
    ├── progress.py            # API Lịch sử rèn luyện, khảo sát RPE & Ma trận phục hồi 7 nhóm cơ
    └── capybara.py            # API Trạng thái biểu cảm & câu thoại Capybara Mascot
frontend/                      # Giao diện Web Client (HTML5, CSS3, ES6 JavaScript)
├── index.html                 # Single Page Application (SPA) container & các modal pop-up web
├── css/
│   ├── style.css              # Obsidian Dark & Light Theme, Glassmorphism, animations & typography
│   └── workout.css            # Styling chuyên biệt cho Cyber-HUD, camera overlay & rep gauge
└── js/
    ├── api.js                 # REST API fetch client kết nối Backend
    ├── state.js               # Reactive state store quản lý trạng thái
    ├── app.js                 # SPA Router, theme switcher & điều phối sự kiện
    ├── components/
    │   ├── toast.js           # Hệ thống thông báo toast notification
    │   ├── modal.js           # Pop-up Web Modal xác nhận hành động thay thế alert trình duyệt
    │   └── capybara.js        # Hoạt ảnh, câu thoại & tương tác Capybara mascot
    └── views/
        ├── dashboard.js       # Bảng điều khiển tổng quan, streak & quick stats
        ├── planner.js         # Kế hoạch 7 ngày, đổi ngày tập thông minh & swap bài tập
        ├── library.js         # Thư viện 28 bài tập, tìm kiếm tức thì & modal kỹ thuật
        ├── workout.js         # AI HUD Live camera, FSM đếm rep & Chế độ Không dùng Camera
        ├── progress.js        # Bản đồ nhiệt 7 nhóm cơ, khảo sát RPE & đề xuất Adaptive AI
        └── profile.js         # Quản lý hồ sơ thể chất & cập nhật hạn chế vận động
config.py                      # Cấu hình camera & thiết bị phần cứng
requirements.txt               # Danh sách thư viện Python
data/
├── exercises.json             # Danh mục 28 bài tập Calisthenics chuẩn hóa JSON Schema
└── private/                   # Lưu trữ hồ sơ người dùng cục bộ & cấu hình OAuth
models/
└── pose_landmarker_lite.task  # Model MediaPipe Pose chạy trên trình duyệt / Python
assets/
├── exercises/                 # Media minh họa bài tập Calisthenics
└── webcam/                    # MediaPipe WASM, Web Workers & Voice Coach tiếng Việt
src/                           # Modules thuật toán & logic tính toán CT cốt lõi (Domain Logic dùng chung)
├── adaptive_weekly_plan.py    # Thuật toán tái cấu trúc tuần thông minh & Adaptive Deload
├── exercise_library.py        # Quản lý danh mục bài tập, lọc hạn chế chấn thương & bài tương đương
├── fsm_rep_counter.py         # Máy trạng thái hữu hạn (FSM) đếm rep theo góc khớp động học
├── fsm_gestures.py            # FSM nhận diện cử chỉ Giơ tay (Bắt đầu) & Chữ X (Dừng khẩn cấp)
├── planner_generation.py      # Tích hợp prompt & phân tích cú pháp JSON sinh giáo án FIT-AI
├── school_ai.py               # Kết nối API HCMUS FIT-AI Qwen-27B
├── profile.py                 # Xử lý hồ sơ thể chất, tính BMI & xác thực thông tin cá nhân
└── capybara_widget.py         # Đồ họa vector SVG & hệ sinh thái biểu cảm Capybara Mascot
tests/                         # Bộ kiểm thử tự động toàn diện (129 test cases) bao quát toàn bộ 8 phân hệ CT
docs/                          # Báo cáo kiến trúc 4 trụ cột CT, bảng phân công nhiệm vụ Scrum & biên bản nghiệm thu
```

---

## 🧪 Chạy Kiểm thử (Tests)

Chạy toàn bộ bộ kiểm thử tự động Python từ thư mục gốc dự án:
```bash
python -m unittest discover -s tests -v
```

Chạy unit test JavaScript cho Voice Coach & Webcam Session (yêu cầu Node.js, xem thêm [`tests/README.md`](tests/README.md)):
```bash
node --test tests/test_voice_coach.mjs tests/test_webcam_session.mjs
```

---

## 🔗 Liên kết Dự án

- **Jira Board:** https://fitsense2026.atlassian.net/jira/software/projects/SCRUM/boards/1 (Project: `FitSense - AI Fitness & Workout Assistant`, Key: `SCRUM`)
- **Nhánh chính:** `main`
- **Tài liệu:** [`docs/`](docs/)
