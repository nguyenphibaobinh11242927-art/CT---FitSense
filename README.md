# Ratatouille

Trợ lý nấu ăn, quản lý chi tiêu và hỗ trợ thói quen cá nhân.

## Hiện trạng

Đây là khung dự án Streamlit: có các tab giao diện khởi đầu và module chờ triển khai.
Chưa có AI, database, tính toán giỏ mua hay tích hợp cửa hàng. Không cần API key để chạy khung.

## Chạy trên máy cá nhân

Đề xuất nhóm thống nhất Python 3.12. Mở terminal tại thư mục chứa `app.py`:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Các lệnh Windows trên không cần kích hoạt môi trường ảo.
Trên macOS/Linux thay `.\.venv\Scripts\python.exe` bằng `.venv/bin/python`.

## Cấu trúc

```text
app.py                         Giao diện và điểm chạy chung
src/profile_inventory.py       Hồ sơ, bếp và nguyên liệu
src/menu_shopping.py            Thực đơn và mua sắm
src/cooking.py                  Nấu ăn
src/diary_statistics.py         Nhật ký và thống kê
src/habits_exercise.py          Thói quen và tập luyện
data/samples/                   Dữ liệu mẫu được phép chia sẻ
tests/                          Kiểm thử nghiệp vụ
docs/                           Quy tắc, dữ liệu bàn giao và hướng dẫn
requirements.txt                Thư viện
.env.example                    Mẫu biến cấu hình, không có key thật
.gitignore                      Loại trừ file không đưa lên Git
```

## Làm việc cùng nhóm

- Jira là nơi quản lý công việc; điền URL bảng Jira vào phần Liên kết bên dưới.
- Mỗi task làm trên branch riêng, ví dụ `SCRUM-12-user-profile`.
- Mở Pull Request, gắn mã/link Jira, nêu thay đổi và cách kiểm tra.
- Người phối hợp review trước khi merge vào `main`; quy tắc này cần nhóm thống nhất áp dụng.
- Thống nhất hợp đồng dữ liệu trước khi nối module; không thay tên trường âm thầm.
- Chỉ chuyển task sang Done sau khi đầu ra đáp ứng tiêu chí và có bằng chứng.

Đọc [hướng dẫn nhóm](docs/team-onboarding.md),
[hợp đồng dữ liệu](docs/data-contracts.md) và
[đưa dự án lên GitHub](docs/github-setup.md).

## Liên kết

- GitHub repository: CHƯA ĐIỀN
- Jira board: CHƯA ĐIỀN
- Thư mục tài liệu/biên bản họp: CHƯA ĐIỀN
- Hướng dẫn hoặc URL demo: CHƯA ĐIỀN

## Kiểm thử

Hiện chưa có kiểm thử nghiệp vụ. Xem `tests/README.md` để thêm cùng chức năng.
Kiểm tra cú pháp khi cần:

```powershell
python -m compileall -q app.py src
```
