# Kiểm thử

Thêm kiểm thử cùng lúc triển khai logic nghiệp vụ; hiện chưa có test.

Các trường hợp ưu tiên:
- Nguyên liệu chung giữa nhiều món: gộp trước khi trừ tồn.
- Đổi khẩu phần, thiếu lượng hoặc không thể quy đổi đơn vị.
- Voucher không hợp lệ, thiếu giá, vượt ngân sách.
- Xác nhận lặp không trừ tồn hoặc ghi chi hai lần.
- Sửa/xóa hoạt động cập nhật nhật ký và streak liên quan.

Nếu dùng thư viện chuẩn `unittest`, chạy từ thư mục gốc:

```powershell
python -m unittest discover -s tests -v
```

Thông báo chạy 0 test chỉ có nghĩa là chưa có test, không chứng minh chức năng đúng.
