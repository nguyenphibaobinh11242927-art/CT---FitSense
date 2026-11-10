# Kiểm thử FitSense

Chạy từ thư mục gốc:

```powershell
python -m unittest discover -s tests -v
```

Với SCRUM-14, kiểm tra góc 90°, 180° và trường hợp hai mốc trùng nhau.

Với SCRUM-15, chạy `node --test tests/test_voice_coach.mjs`. Kiểm tra thực tế trong
Phòng tập Trực tiếp bằng trình duyệt có giọng tiếng Việt. Bấm Voice Coach để nghe
câu thử, bật camera rồi giơ tay để bắt đầu phiên. Tập squat đủ biên độ và thử một
lần chưa đủ biên độ để kiểm tra hai loại phản hồi. Chỉ số từ khung hình đến lúc
trình duyệt bắt đầu đọc bao gồm cả thời gian gửi khung hình và xử lý FSM, nên có
thể dùng làm cận trên cho độ trễ sau FSM. Xác nhận âm thanh nghe rõ và ghi nhận
kết quả trên trình duyệt, thiết bị đích.
