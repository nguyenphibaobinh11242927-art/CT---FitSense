# FitSense — AI Fitness & Workout Assistant

Hệ thống Trợ lý AI hỗ trợ rèn luyện Thể dục Thể thao & Calisthenics thích ứng thông minh.  
**Môn học:** CSC10014 — Tư duy Tính toán (Computational Thinking) — HCMUS.

---

## ⚡ Hiện trạng Dự án (Sprint 1 — SCRUM-11)

Đây là khung giao diện Streamlit chính thức của dự án FitSense, được module hóa theo kiến trúc Tư duy Tính toán (8 phân hệ $D1 \rightarrow D8$):
- **Phụ trách chính (Lead - Code):** Nguyễn Nhật Thùy Khanh (M02)
- **Hỗ trợ (Support - Review & Merge):** Trương Cẩm Tú Nga (M05)
- **Mã Jira:** `SCRUM-11` (Sprint 1: Nền tảng & UI — 4.5 Story Points).

---

## 🚀 Khởi chạy trên Máy cá nhân

Khuyến nghị môi trường **Python 3.10 - 3.12**. Mở terminal tại thư mục gốc dự án:

### Cách 1: Chạy trực tiếp (Nhanh nhất)
```powershell
# Cài đặt thư viện:
python -m pip install -r requirements.txt

# Khởi chạy ứng dụng FitSense:
python -m streamlit run app.py
```

### Cách 2: Khởi tạo Virtual Environment (Chuẩn phát triển)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

---

### Tạo giáo án tuần với FIT-AI (SCRUM-12)

Đặt `FITAI_API_KEY` trong môi trường của tiến trình Streamlit trước khi khởi động app.
Ví dụ trên PowerShell, nhập key khi được hỏi:

```powershell
$env:FITAI_API_KEY = (Get-Credential -UserName 'FIT-AI' -Message 'Nhập key FIT-AI ở ô Password').GetNetworkCredential().Password
python -m streamlit run app.py
```

Mở **Kế hoạch Tập luyện**, chọn mục tiêu và bấm **Tái lập Kế hoạch AI**.
FitSense gọi model `Qwen-27B` của HCMUS FIT-AI từ máy chủ và chỉ thay lịch sau
khi kiểm tra đủ bảy ngày cùng các bài tập hợp lệ. Khi API lỗi, lịch hiện tại vẫn dùng được.
Key của lớp lấy theo [hướng dẫn FIT-AI](https://www.fit.hcmus.edu.vn/llm-services/).

## 📂 Cấu trúc Mã nguồn FitSense (SCRUM-11)

```text
app.py                         # Giao diện chính, điều hướng Sidebar & khởi tạo Session State FitSense
src/
├── __init__.py                # Khai báo package ứng dụng
├── profile_view.py            # D1: Hồ sơ thể chất, đo BMI, chấn thương & hạn chế vận động
├── planner_view.py            # D2: Lập lịch tập tuần, phân bổ nhóm cơ & giải thích lý do AI
├── library_view.py            # D3: Thư viện động tác Calisthenics, bộ lọc nhóm cơ & bài thay thế
├── session_view.py            # D4 & D5: Phòng tập Rảnh tay (HUD), nhúng AI Pose Tracking & khóa sửa rep
├── evaluation_view.py         # D5 & D7: Đánh giá sau buổi (RPE 1-10) & Thuật toán Thích ứng Tải trọng
├── heatmap_view.py            # D6: Bảng nhiệt phục hồi nhóm cơ (Muscle Heatmap Matrix 24h-48h-72h)
└── progress_view.py           # D6: Biểu đồ thể lực, kỷ lục PRs & Streak duy trì (tối thiểu 70%)
tests/
└── test_fitsense_ui.py        # Kiểm thử đơn vị tự động xác thực render và dữ liệu phiên tập
docs_private/                  # Tài liệu nội bộ, Báo cáo Tư duy Tính toán (PDF), Bảng phân công (Excel)
requirements.txt               # Danh mục thư viện Python (Streamlit, Pandas)
```

---

## 🧪 Chạy Kiểm thử Đơn vị (Unit Tests)

Xác thực tính toàn vẹn của toàn bộ các hàm render và cấu trúc dữ liệu thể thao:
```powershell
python -m unittest tests/test_fitsense_ui.py
```

---

## 🔗 Liên kết Dự án

- **Jira Board:** https://ratatouille2026.atlassian.net (Project: `FitSense - AI Fitness & Workout Assistant`, Key: `SCRUM`)
- **Git Branch:** `scrum-14-mediapipe-pose`
Tài liệu dự án nằm trong `docs/`. Chạy webcam SCRUM-14 bằng `python -m src.pose_tracking`.
