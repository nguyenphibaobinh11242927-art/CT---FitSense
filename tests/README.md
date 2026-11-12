# Kiểm thử FitSense

Chạy từ thư mục gốc:

```powershell
python -m unittest discover -s tests -v
```

Với SCRUM-14, kiểm tra góc 90°, 180° và trường hợp hai mốc trùng nhau.

Với SCRUM-15 và SCRUM-20, chạy `node --test tests/test_voice_coach.mjs tests/test_webcam_session.mjs`.
Kiểm tra thực tế trong
Phòng tập Trực tiếp. Bấm Voice Coach để nạp âm thanh đi kèm và nghe câu thử.
Sau đó bật camera rồi giơ tay để bắt đầu phiên. Thử squat nông trong và ngoài
khoảng chờ 3,5 giây. Lọc `Voice Coach squat nông` trong console ở mức Verbose để
đối chiếu số khung hình và quyết định phát hoặc bỏ qua. Chỉ số trên HUD đo từ lúc
chụp khung hình đến lúc trình duyệt lên lịch phát. Đo thêm trên thiết bị đích
để xác nhận âm thanh nghe rõ và độ trễ đến khi thực sự nghe được.

### SCRUM-23 — Khẩu lệnh

Chạy `node --test tests/test_voice_commands.mjs tests/test_webcam_session.mjs`.
Trong **Phòng tập Trực tiếp → AI Vision**, bấm **Khẩu lệnh** và cấp quyền micro
trên trình duyệt. Thử “Bắt đầu đi”, “Ngưng”, “Tập tiếp”, “Thôi tập” và
“FitSense, thôi”. Thử thêm “Thôi” và “Đừng dừng lại” để xác nhận HUD bỏ qua.
Kiểm tra số rep còn nguyên qua một lượt tạm ngưng và tiếp tục. Bật Voice Coach
để kiểm tra mic đợi phát tiếng xong rồi nghe tiếp. Trên một số trình duyệt,
dịch vụ nhận diện của trình duyệt cần mạng để xử lý âm thanh.

“Nghỉ hiệp” và “Bài tiếp theo” đã được nhận diện. Cả hai thao tác sẽ cần nối
vào đồng hồ nghỉ và luồng chuyển bài của SCRUM-19.
