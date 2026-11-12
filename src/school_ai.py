"""Server-side client for HCMUS FIT-AI Chat Completions."""

import os

import requests

from src.workout_planner import WorkoutPlanError


FITAI_CHAT_URL = "https://api-fit.hcmus.edu.vn/v1/chat/completions"
FITAI_MODEL = "Qwen-27B"


def complete_with_school_ai(prompt: str) -> str:
    key = os.getenv("FITAI_API_KEY", "").strip()
    if not key:
        raise WorkoutPlanError("Máy chủ FitSense chưa cấu hình FITAI_API_KEY.")

    try:
        response = requests.post(
            FITAI_CHAT_URL,
            headers={"Authorization": f"Bearer {key}", "User-Agent": "FitSense/1.0"},
            json={
                "model": FITAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "chat_template_kwargs": {"enable_thinking": False},
                "max_tokens": 2300,
                "response_format": {"type": "json_object"},
            },
            timeout=(5, 90),
            allow_redirects=False,
        )
    except requests.Timeout:
        raise WorkoutPlanError("API AI phản hồi quá chậm. Bạn có thể thử lại.") from None
    except requests.RequestException:
        raise WorkoutPlanError("Không kết nối được với API AI. Bạn có thể thử lại.") from None

    if response.status_code in (401, 403):
        raise WorkoutPlanError("API AI từ chối truy cập. Hãy kiểm tra API key và quyền dùng model.")
    if response.status_code == 429:
        raise WorkoutPlanError("API AI đang giới hạn lượt gọi. Bạn có thể thử lại sau.")
    if not 200 <= response.status_code < 300:
        raise WorkoutPlanError(f"API AI trả lỗi HTTP {response.status_code}.")

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (ValueError, IndexError, KeyError, TypeError):
        raise WorkoutPlanError("API AI trả về phản hồi không đúng định dạng.") from None
    if not isinstance(content, str) or not content.strip():
        raise WorkoutPlanError("API AI không trả về nội dung giáo án.")
    return content
