# LOGBOOK NHÓM 3 — DỰ ÁN FITSENSE (SCRUM-28)

* **Học phần:** CSC10014 — Tư duy Tính toán (Computational Thinking), Khoa CNTT, ĐH KHTN — ĐHQG-HCM
* **Repository:** https://github.com/nguyenphibaobinh11242927-art/CT---FitSense
* **Jira Board:** https://ratatouille2026.atlassian.net (Key: `SCRUM`)
* **Phụ trách tổng hợp (`SCRUM-28`):** Nguyễn Phi Bảo Bình (M01 — `25127020`) | **Support Review:** Nguyễn Diệp Vĩnh Khang (M04 — `25127366`)
* **Trạng thái tài liệu:** Bản nháp chuẩn bị trước (cập nhật đến **25/11/2026**, đối chiếu `main` tại commit `5bbca4b` — sẽ chốt bản cuối sau khi merge hết Sprint 4 & Sprint 5).

---

## 1. Tổng quan Kiểm tra Vệ sinh & Bảo mật Repository (`main` — `5bbca4b`)

| Hạng mục kiểm tra | Kết quả | Ghi chú |
|---|---|---|
| Lộ `.env` / API Key / dữ liệu `data/private/` trong `git ls-files` | ✅ **Sạch (0 file)** | Đã rà soát toàn bộ tracked files; `.env` và `data/private/` nằm ngoài Git. |
| Remote URL chuẩn | ✅ **Đã cập nhật** | Đổi từ `CT---Ratatouille.git` sang `CT---FitSense.git`. |
| Tình trạng merge conflict trên `main` | ✅ **0 conflict** | `main` (`5bbca4b`) đang sạch, đã chuyển sang kiến trúc FastAPI + Vanilla JS SPA. |
| Kiểm thử tự động Python (`unittest`) | ✅ **194/194 PASS** | Đã xác minh trên nhánh `feature/m01-scrum-34-chat-storage` (`7.777s`), bao gồm backend FastAPI, Capybara UI & storage. |
| Kiểm thử tự động JavaScript (`node --test`) | ⏳ **Chờ chốt trên máy có Node.js** | Cần chạy `node --test tests/*.mjs` trước khi đóng băng `main` cuối kỳ. |

---

## 2. Minh chứng Pull Request & Tích hợp đã hoàn thành trên `main`

| PR / Commit | Nhánh nguồn | Nội dung chính |
|---|---|---|
| `PR #10` (`891e480`) | `codex/scrum-15-20-integration` | Tích hợp Voice Coach (`SCRUM-15`) với Workout Session (`SCRUM-20`). |
| `PR #11` (`b1cce37`) | `codex/scrum-15-sprint-2-feedback` | Sửa phản hồi Voice Coach Sprint 2, chống nhiễu tracking ngắn. |
| `PR #12`, `#15` (`e6d17a8`, `96fd06f`) | `scrum-11-streamlit-ui` + `m03-scrum-17` | Khung UI đa màn hình, thư viện bài tập Calisthenics (`SCRUM-17`), tối ưu webcam. |
| `PR #13` (`c3c4d8e`) | `codex/scrum-12-school-ai` | Kết nối AI Workout Planner (`SCRUM-12`) với HCMUS FIT-AI (`Qwen-27B`). |
| `PR #17` (`1167a42`) | `feature/fitsense-feedback-update` | Cập nhật toàn diện 28 bài tập, live search 180ms debounce, đồng bộ kế hoạch tuần. |
| `PR #19`, `#25` (`93bf5b0`, `5bbca4b`) | `codex/scrum-18-pipeline-webcam` | Pipeline webcam MediaPipe Pose, overlay khung xương & pose diagnostics (`SCRUM-18`). |
| `PR #20` (`c53f13d`) | `feature/fastapi-modern-ui` | Chuyển đổi kiến trúc sang Backend FastAPI + Frontend SPA hiện đại. |
| `PR #21` (`c6431fb`) | `codex/scrum-12-15-fastapi-fixes` | Tương thích FIT-AI planner & Voice Coach trên FastAPI. |
| `PR #22` (`a039c95`) | `codex/camera-position-warnings` | Cảnh báo vị trí đứng trước camera bằng tiếng Việt. |
| `PR #23` (`4e0c827`) | `feature/m05-scrum-21-progress-dashboard` | Analytics tiến độ bằng Pandas, biểu đồ Plotly Reps/Plank, PRs động (`SCRUM-21`). |
| `PR #24` (`abff9f0`) | `feature/scrum-19-session-hud` | HUD phiên tập, Rest Timer, Up Next, nối sự kiện cử chỉ (`SCRUM-19`). |
| `41ef9bd`, `8547bce`, `fad3ccf` | `scrum-20`, `mai-anh-voice-coach`, `scrum-23` | Toàn vẹn phiên tập & khóa rep AI (`SCRUM-20`), giọng Mai Anh, khẩu lệnh tiếng Việt (`SCRUM-23`). |

---

## 3. Minh chứng Đóng góp theo Thành viên (Trích xuất từ Git đến 25/11/2026)

| Mã TV | MSSV | Họ và tên | Tài khoản Git | Số commit (no-merge) | Nhiệm vụ chính đã/đang triển khai | Tỷ lệ đóng góp dự kiến *(chờ chốt 6/6)* |
|---|---|---|---|---:|---|---:|
| **M01** | `25127020` | Nguyễn Phi Bảo Bình | `NGUYEN PHI BAO BINH` / `nguyenphibaobinh11242927-art` | 22 | `SCRUM-14`, `SCRUM-20`, `SCRUM-34` (đã push), `SCRUM-28` (đang chuẩn bị) | 16.67% |
| **M02** | `25127373` | Nguyễn Nhật Thùy Khanh | `Yu` | 28 | `SCRUM-11`, `SCRUM-19`, FastAPI SPA, `SCRUM-22` (chờ merge), `SCRUM-31` (chờ merge) | 16.67% |
| **M03** | `25127301` | Đậu Cao Dũng | `DauCaoDung132` | 13 | `SCRUM-13`, `SCRUM-17`, QA (`SCRUM-24`), `SCRUM-30` (đang làm) | 16.67% |
| **M04** | `25127366` | Nguyễn Diệp Vĩnh Khang | `KhangNguyendotcpp` | 19 | `SCRUM-12`, `SCRUM-15`, `SCRUM-23`, `SCRUM-29` (chờ merge) | 16.67% |
| **M05** | `25127427` | Trương Cẩm Tú Nga | `tunnnga2605-png` | 6 | `SCRUM-21`, `SCRUM-26`, `SCRUM-27`, `SCRUM-32` (đang làm) | 16.67% |
| **M06** | `25127062` | Nguyễn Minh Huy | `Huy Minh` | 11 | `SCRUM-16`, `SCRUM-18`, `SCRUM-25`, `SCRUM-33` (đang làm) | 16.65% |

> **Lưu ý:** Số commit trên chỉ là chỉ số tham khảo kỹ thuật (chưa tính các commit mới của Sprint 4/5 sắp đẩy và công việc viết báo cáo/slide/QA). Tỷ lệ phần trăm đóng góp chính thức sẽ được 6/6 thành viên thống nhất ký xác nhận ở bước chốt cuối kỳ.

---

## 4. Checklist Đóng gói & Chốt Nhánh `main` Trước Khi Nộp A23

- [x] Rà soát không có `.env`, API key hay dữ liệu cá nhân trong lịch sử tracked files.
- [x] Cập nhật URL remote chuẩn `CT---FitSense.git`.
- [ ] Review & merge `origin/feature/scrum-22-post-workout-evaluation` (`SCRUM-22`).
- [ ] Review & merge hoàn chỉnh Sprint 4 Capybara AI: `SCRUM-29` → `SCRUM-30` → `SCRUM-31` → `SCRUM-32` → `SCRUM-33` → `SCRUM-34`.
- [ ] Review & merge các hạng mục Sprint 5 còn lại (`SCRUM-24`, `SCRUM-25`, `SCRUM-26`).
- [ ] Chạy toàn bộ bộ test tự động Python (`unittest` / `pytest`) và JavaScript (`node --test tests/*.mjs`) pass 100% trên `main`.
- [ ] Kiểm thử cài đặt sạch từ đầu (`pip install -r requirements.txt` & `python run_server.py`) và kiểm tra FPS camera $\ge 25$ FPS khi bật đồng thời Capybara Chat + Micro.
- [ ] Chốt bảng tỷ lệ % đóng góp có đồng thuận 6/6 thành viên và nhờ **Khang (M04)** review approve `SCRUM-28`.
