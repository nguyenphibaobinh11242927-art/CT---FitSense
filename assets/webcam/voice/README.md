# Âm thanh Voice Coach

`vi.mp3` chứa các câu được tổng hợp cho FitSense bằng Piper với [giọng vi_VN-vais1000-medium](https://huggingface.co/rhasspy/piper-voices/tree/664c651454f055ed34bd83f09e024ffbc0da09ac/vi/vi_VN/vais1000/medium). Giọng được huấn luyện từ [VAIS-1000 Vietnamese Speech Synthesis Corpus](https://ieee-dataport.org/documents/vais-1000-vietnamese-speech-synthesis-corpus), giấy phép [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Các đoạn đã được cắt khoảng lặng, ghép và mã hóa MP3.

`vi_cues.mjs` ghi vị trí và độ dài từng đoạn theo giây. Các mục 0–100 đọc số tương ứng, mục 101 đọc câu xác nhận bật giọng và mục 102 đọc câu nhắc squat. Cập nhật cả hai tệp khi thay đổi âm thanh.
