"""Server-side client for HCMUS FIT-AI Chat Completions."""

import os

import requests

from src.workout_planner import WorkoutPlanError


FITAI_CHAT_URL = "https://api-fit.hcmus.edu.vn/v1/chat/completions"
FITAI_MODEL = "Qwen-27B"


class FitAIServiceError(WorkoutPlanError):
    """FIT-AI could not return a complete response."""


def complete_with_school_ai(
    prompt: str, *, system_prompt: str | None = None, max_tokens: int = 2300,
    timeout: tuple[float, float] = (5, 90),
) -> str:
    key = os.getenv("FITAI_API_KEY", "").strip()
    if not key:
        raise FitAIServiceError("Máy chủ FitSense chưa cấu hình FITAI_API_KEY.")

    messages = [{"role": "user", "content": prompt}]
    if system_prompt is not None:
        messages.insert(0, {"role": "system", "content": system_prompt})

    try:
        response = requests.post(
            FITAI_CHAT_URL,
            headers={"Authorization": f"Bearer {key}", "User-Agent": "FitSense/1.0"},
            json={
                "model": FITAI_MODEL,
                "messages": messages,
                "chat_template_kwargs": {"enable_thinking": False},
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
            },
            timeout=timeout,
            allow_redirects=False,
        )
    except requests.Timeout:
        raise FitAIServiceError("API AI phản hồi quá chậm. Bạn có thể thử lại.") from None
    except requests.RequestException:
        raise FitAIServiceError("Không kết nối được với API AI. Bạn có thể thử lại.") from None

    if response.status_code in (401, 403):
        raise FitAIServiceError("API AI từ chối truy cập. Hãy kiểm tra API key và quyền dùng model.")
    if response.status_code == 429:
        raise FitAIServiceError("API AI đang giới hạn lượt gọi. Bạn có thể thử lại sau.")
    if not 200 <= response.status_code < 300:
        raise FitAIServiceError(f"API AI trả lỗi HTTP {response.status_code}.")

    try:
        choice = response.json()["choices"][0]
        content = choice["message"]["content"]
    except (ValueError, IndexError, KeyError, TypeError):
        raise FitAIServiceError("API AI trả về phản hồi không đúng định dạng.") from None
    if choice.get("finish_reason") in ("length", "content_filter"):
        raise FitAIServiceError("API AI chưa trả về giáo án đầy đủ. Bạn có thể thử lại.")
    if not isinstance(content, str) or not content.strip():
        raise FitAIServiceError("API AI không trả về nội dung giáo án.")
    return content
