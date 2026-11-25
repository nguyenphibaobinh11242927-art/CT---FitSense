## Hợp đồng sự kiện frontend

### `capy:transcript`

```js
document.addEventListener("capy:transcript", (event) => {
  const text = event.detail?.text;
  const shouldSubmit = event.detail?.submit;
});
```

`submit: true` biểu thị transcript cuối từ micro và yêu cầu tự gửi. Capybara lắng nghe sự kiện này, gửi nội dung cùng lịch sử hội thoại gần nhất tới `POST /api/capybara/chat`, hiển thị câu trả lời và yêu cầu TTS đọc nếu âm thanh đang bật. Người dùng cũng có thể nhập và gửi bằng nút hoặc phím Enter.

API dùng FIT-AI hiện có (`FITAI_API_KEY`); nếu máy chủ chưa cấu hình key hoặc dịch vụ lỗi, giao diện hiển thị lỗi và giữ lại nội dung để thử lại. Hội thoại chỉ được giữ trong bộ nhớ trình duyệt trong phiên hiện tại. Trợ lý hiện chỉ tư vấn, không tự thay đổi lịch tập.

### `capy:schedule-changed`

```js
document.dispatchEvent(new CustomEvent("capy:schedule-changed", {
  detail: {message: "Đã đổi lịch tập xong."},
}));
```

## Thành phần mã

- `frontend/js/components/voice_assistant.js`: adapter STT/TTS của trình duyệt, độc lập với giao diện.
- `frontend/js/components/capybara.js`: tích hợp callback, chat composer, hiển thị hội thoại và TTS phản hồi.
- `frontend/js/api.js`: client cho API hội thoại Capy.
- `backend/routers/capybara.py`, `backend/schemas.py`: endpoint chat có kiểm tra đăng nhập, giới hạn nội dung và xác thực định dạng phản hồi AI.
- `frontend/index.html`, `frontend/css/style.css`: giao diện chat, nút điều khiển, trạng thái và animation.
- `tests/test_capybara_chat.py`: kiểm tra xác thực, phản hồi AI, lỗi cấu hình và dữ liệu không hợp lệ.
- `tests/test_voice_assistant.mjs`: kiểm tra cấu hình tiếng Việt, callback transcript, lỗi hỗ trợ và mute.
- `tests/test_voice_assistant_extra.mjs`: kiểm tra lỗi, echo, Unicode, cắt câu, đo latency, mute và audio sprite.
- `frontend/js/views/planner.js`: phát sự kiện thành công sau tạo, đặt lại, nạp, cập nhật, đổi bài và đổi buổi lịch.

## Báo cáo kiểm thử thủ công

| Hạng mục | Kết quả được báo cáo | Ghi chú |
|---|---|---|
| STT tiếng Việt | PASS với “Mở kế hoạch tập luyện” và “Đổi lịch tập sang thứ Sáu”; transcript tạm hiển thị và chuẩn hóa dấu/khoảng trắng | Chưa có số mẫu hoặc video đính kèm |
| Quyền micro | PASS khi từ chối quyền; ứng dụng hiện thông báo hướng dẫn | |
| Thiết bị/mạng | PASS với lỗi `audio-capture` và `network` | |
| Làm sạch nội dung TTS | PASS với emoji, URL và Markdown | |
| Ngắt TTS/STT | PASS khi chuyển giữa đang đọc và đang nghe | |
| Mute | PASS; trạng thái được giữ sau khi tải lại trang | |
| Chrome/Edge | Được báo cáo hoạt động | Chưa ghi phiên bản trình duyệt, OS hoặc thiết bị |

### Trạng thái nghiệm thu

- Các thao tác STT, quyền micro, lỗi, mute và chuyển trạng thái audio ở trên được ghi nhận là PASS theo báo cáo thủ công.
- Chat composer/listener/API đã được tích hợp; cần kiểm thử thủ công trên Chrome/Edge bằng API key FIT-AI hợp lệ để nghiệm thu phản hồi thật đầu-cuối.
- Xác nhận ngưỡng TTS `<100 ms`. Âm báo cold start 354 ms được báo cáo.
- Chrome/Edge được báo cáo hoạt động nhưng chưa ghi phiên bản trình duyệt, hệ điều hành hoặc thiết bị. Chưa có video/log latency để tái kiểm tra.
