# Kiểm thử webcam SCRUM-16 — 10/11/2026

| Ca | Quan sát | Kết quả mong đợi | Trạng thái |
|---|---|---|---|
| Mất dấu ở đáy squat | Người thử rời khung lúc đang thấp rồi quay lại khi đứng thẳng. Bộ đếm đôi khi tăng 1 rep. Đã tái hiện bằng chuỗi góc mô phỏng. | Giữ số rep cũ, chờ thấy người đứng thẳng rồi mới nhận chu kỳ mới. | Đã sửa và test tự động trên nhánh review. Chờ xác nhận bằng webcam. |
| Giữ chữ X | Người thử giữ nguyên tư thế nhưng thanh xác nhận liên tục quay về 0, gây khó dừng phiên. | Giữ đúng cử chỉ đủ thời gian thiết kế thì khóa rep; hạ tay sớm thì hủy. | Đã ghi nhận từ webcam, chưa sửa. Chưa xác định mốc nào mất trong lần thử. |

HUD đếm 45 khung liên tiếp. Ở 16,8 FPS, thời gian lý tưởng khoảng 2,7 giây. Một khung mất điều kiện làm tiến trình về 0. Hiện hai cổ tay phải có độ lệch ngang nhỏ hơn 8% bề rộng vai và hệ thống phải thấy đầu.

## Thử tiếp

- Tập 2 rep, che camera ở đáy rep thứ 3, đứng thẳng trước khi mở camera. Kỳ vọng giữ 2, squat trọn vẹn tiếp theo mới lên 3.
- Giữ chữ X trước ngực, mặt nhìn thẳng, thấy đủ đầu và hai tay. Ghi FPS, số khung cao nhất và thời gian tới lúc khóa. So sánh với hai cổ tay đặt sát nhau nhưng cẳng tay không bắt chéo để kiểm tra khóa nhầm.
- Sau khi chữ X khóa thành công, bỏ tay ra rồi squat. Số rep phải đứng yên đến khi đặt lại phiên.
- Lặp lại ca mất dấu bằng nút tắt/bật camera ngay trong cùng phiên. Khi bật lại ở tư thế đứng, rep phải giữ nguyên.
