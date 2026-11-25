"""Capybara Workout Mascot Companion Router."""

import random
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, StringConstraints

from backend.routers.auth import CURRENT_SESSION
from src.capybara_agent import CapybaraReply, respond_to_message
from src.capybara_history import (
    append_chat_exchange,
    clear_chat_history,
    load_chat_history,
    save_chat_history,
    user_history_key,
)
from src.capybara_widget import CAPY_SVG_HAPPY, CAPY_SVG_SAD
from backend.routers.progress import HAS_WORKED_OUT_TODAY

router = APIRouter(prefix="/api/capybara", tags=["Capybara Mascot"])

QUOTES_PENDING = [
    "Hôm nay bạn chưa rèn luyện đó nha! Hãy cùng tôi khởi động làm vài hiệp Calisthenics nào! 🦫✨",
    "Kỷ luật là cầu nối giữa mục tiêu và thành tựu! Chỉ 15 phút hôm nay thôi! 💪",
    "Một buổi tập nhỏ cũng tốt hơn việc ngồi im cả ngày! Bắt đầu ngay nhé! 🔥",
    "Capybara đang chờ bạn vào phòng tập nè, đừng để chuỗi streak bị ngắt nha! 🥺",
    "Uống một ngụm nước và chuẩn bị vào thảm nào, bạn làm được mà! 💧",
]

QUOTES_DONE = [
    "Tuyệt vời quá! Bạn đã hoàn thành buổi tập hôm nay, Capybara rất tự hào về bạn! 🥰🍊",
    "Cơ bắp đang phát triển và phục hồi! Nhớ bổ sung nước và dinh dưỡng nhé! 🥗🥛",
    "Phong độ tuyệt đỉnh! Chuỗi rèn luyện của bạn đang rất ấn tượng đấy! 🔥✨",
    "Nghỉ ngơi thật tốt để ngày mai tiếp tục bứt phá giới hạn nha bạn tôi ơi! 🛌⚡",
]


@router.get("/status")
def get_capybara_status():
    worked_out = HAS_WORKED_OUT_TODAY
    quotes = QUOTES_DONE if worked_out else QUOTES_PENDING
    quote = random.choice(quotes)
    mood = "happy" if worked_out else "reminder"
    svg = CAPY_SVG_HAPPY if worked_out else CAPY_SVG_SAD
    
    return {
        "mood": mood,
        "has_worked_out_today": worked_out,
        "quote": quote,
        "svg": svg,
        "all_quotes": quotes,
    }


class CapybaraChatRequest(BaseModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class CapybaraHistorySaveRequest(BaseModel):
    messages: list[dict[str, Any]] = Field(default_factory=list, max_length=200)


def _active_user_email() -> str | None:
    if not CURRENT_SESSION.get("is_logged_in"):
        return None
    email = CURRENT_SESSION.get("user_email")
    if not isinstance(email, str) or not email.strip():
        return None
    return email.strip().lower()


@router.post("/chat", response_model=CapybaraReply)
def chat_with_capybara(payload: CapybaraChatRequest) -> CapybaraReply:
    reply = respond_to_message(payload.message)
    email = _active_user_email()
    if email:
        try:
            append_chat_exchange(email, payload.message, reply.model_dump())
        except OSError:
            pass
    return reply


@router.get("/history")
def get_capybara_history() -> dict[str, Any]:
    email = _active_user_email()
    if not email:
        return {
            "authenticated": False,
            "user_key": None,
            "messages": [],
        }
    return {
        "authenticated": True,
        "user_key": user_history_key(email)[:16],
        "messages": load_chat_history(email),
    }


@router.post("/history")
def save_capybara_history(payload: CapybaraHistorySaveRequest) -> dict[str, Any]:
    email = _active_user_email()
    if not email:
        raise HTTPException(status_code=401, detail="Cần đăng nhập để lưu lịch sử trò chuyện Capybara.")
    saved = save_chat_history(email, payload.messages)
    return {
        "success": True,
        "user_key": user_history_key(email)[:16],
        "count": len(saved),
        "messages": saved,
    }


@router.delete("/history")
def delete_capybara_history() -> dict[str, Any]:
    email = _active_user_email()
    if not email:
        return {
            "success": True,
            "authenticated": False,
            "cleared": False,
        }
    cleared = clear_chat_history(email)
    return {
        "success": True,
        "authenticated": True,
        "cleared": cleared,
    }

