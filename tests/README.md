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
khoảng chờ 4 giây. Lọc `Voice Coach squat nông` trong console ở mức Verbose để
đối chiếu số khung hình và quyết định phát hoặc bỏ qua. Chỉ số trên HUD đo từ lúc
chụp khung hình đến lúc trình duyệt lên lịch phát. Đo thêm trên thiết bị đích
để xác nhận âm thanh nghe rõ và độ trễ đến khi thực sự nghe được.
