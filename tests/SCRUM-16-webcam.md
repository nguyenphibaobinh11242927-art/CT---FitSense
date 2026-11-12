# Kiểm thử webcam SCRUM-16

## Luồng đã triển khai

- Pose, bộ đếm squat, Start và chữ X được xử lý trong trình duyệt. Python chỉ nhận sự kiện ngữ nghĩa; không gửi batch frame định kỳ.
- Start và chữ X cần giữ 1.500 ms. Mất điều kiện tối đa 250 ms được bỏ qua; mất lâu hơn thì reset tiến trình.
- Chữ X cần nhìn thấy đầu và hai cổ tay trong vùng thân người; ngưỡng gần cổ tay là 15% bề rộng vai. Sự kiện `END_SET` mang số reps và thời gian nghỉ trong kế hoạch.
- Khi mất dấu giữa squat, bộ đếm hủy rep dở và chờ thấy người đứng thẳng trước khi nhận chu kỳ tiếp.
- `END_SET` được chuyển vào session state để điều khiển đồng hồ nghỉ trên HUD; `REST_COMPLETE` chuyển trạng thái và tiến tới hiệp/bài kế.

## Kiểm thử tự động

```powershell
python -m unittest tests.test_gestures tests.test_session_fsm tests.test_rep_counter
node --test tests/workout_fsm.test.mjs
```

## Cần xác nhận thủ công trên webcam thật

- Giữ tay giơ cao 1,5 giây để bắt đầu.
- Hoàn thành squat, rời khung ở đáy rep tiếp theo rồi quay lại đứng thẳng; rep dở không được tính.
- Giữ chữ X đủ 1,5 giây; xác nhận số reps hiệp được chốt một lần và timer trên HUD đếm về 0.
- Kiểm tra timer hết thì tự sang hiệp/bài kế tiếp; thử ngắt camera trong lúc nghỉ.
- Việc không gửi frame qua Python được kiểm tra trong mã; quyền camera và độ mượt cần xác nhận trên trình duyệt thật.
