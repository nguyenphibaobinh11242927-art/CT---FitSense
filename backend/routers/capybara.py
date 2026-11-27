"""Capybara Workout Mascot Companion Router."""

import logging
import random
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field, StringConstraints

from backend.routers.auth import resolve_authenticated_session
from src.capybara_agent import CapybaraReply, respond_to_message
from src.capybara_history import (
    append_chat_exchange,
    clear_chat_history,
    load_chat_history,
    normalize_user_email,
    save_chat_history,
    user_history_key,
)
from src.capybara_widget import CAPY_SVG_HAPPY, CAPY_SVG_SAD
from backend.routers.progress import HAS_WORKED_OUT_TODAY

logger = logging.getLogger("fitsense.capybara")
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


class CapybaraChatResponse(CapybaraReply):
    persisted: bool = True
    persistence_error: str | None = None


class CapybaraHistorySaveRequest(BaseModel):
    messages: list[dict[str, Any]] = Field(default_factory=list, max_length=200)


def _resolve_client_user(
    request: Request,
    expected_user: str | None = None,
    *,
    require_auth: bool = False,
) -> str | None:
    """Resolve user email strictly from the client's authenticated session token."""
    email, _ = resolve_authenticated_session(request)
    expected_normalized = normalize_user_email(expected_user)

    if not email:
        if require_auth or expected_normalized:
            raise HTTPException(
                status_code=401,
                detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại.",
            )
        return None

    if expected_normalized and expected_normalized != email:
        logger.warning(
            "Session user mismatch rejected: expected=%s session=%s",
            user_history_key(expected_normalized)[:12],
            user_history_key(email)[:12],
        )
        raise HTTPException(
            status_code=409,
            detail="Tài khoản trên phiên hiện tại đã thay đổi. Thao tác bị hủy để bảo vệ dữ liệu.",
        )

    return email


@router.post("/chat", response_model=CapybaraChatResponse)
def chat_with_capybara(
    payload: CapybaraChatRequest,
    request: Request,
    x_fitsense_user: Annotated[str | None, Header(alias="X-FitSense-User")] = None,
) -> CapybaraChatResponse:
    email = _resolve_client_user(request, expected_user=x_fitsense_user, require_auth=False)
    reply = respond_to_message(payload.message)
    persisted = False
    persistence_error: str | None = None

    if email:
        try:
            append_chat_exchange(email, payload.message, reply.model_dump())
            persisted = True
        except OSError:
            logger.exception(
                "Failed to persist Capybara chat exchange for user %s",
                user_history_key(email)[:16],
            )
            persistence_error = (
                "Không thể lưu lịch sử trò chuyện lên máy chủ. "
                "Dữ liệu hiện chỉ được lưu cục bộ trên trình duyệt này."
            )

    return CapybaraChatResponse(
        **reply.model_dump(),
        persisted=persisted,
        persistence_error=persistence_error,
    )


@router.get("/history")
def get_capybara_history(
    request: Request,
    x_fitsense_user: Annotated[str | None, Header(alias="X-FitSense-User")] = None,
) -> dict[str, Any]:
    email = _resolve_client_user(request, expected_user=x_fitsense_user, require_auth=False)
    if not email:
        return {
            "authenticated": False,
            "user_key": None,
            "messages": [],
        }
    try:
        messages = load_chat_history(email)
    except OSError as exc:
        logger.exception(
            "Failed to load Capybara chat history for user %s",
            user_history_key(email)[:16],
        )
        raise HTTPException(
            status_code=500,
            detail="Không thể đọc lịch sử trò chuyện từ máy chủ. Đang hiển thị bản lưu cục bộ (nếu có).",
        ) from exc

    return {
        "authenticated": True,
        "user_key": user_history_key(email)[:16],
        "messages": messages,
    }


@router.post("/history")
def save_capybara_history(
    payload: CapybaraHistorySaveRequest,
    request: Request,
    x_fitsense_user: Annotated[str | None, Header(alias="X-FitSense-User")] = None,
) -> dict[str, Any]:
    email = _resolve_client_user(request, expected_user=x_fitsense_user, require_auth=True)
    try:
        saved = save_chat_history(email, payload.messages)
    except OSError as exc:
        logger.exception(
            "Failed to save Capybara chat history for user %s",
            user_history_key(email)[:16],
        )
        raise HTTPException(
            status_code=500,
            detail="Không thể lưu lịch sử trò chuyện lên máy chủ. Dữ liệu hiện chỉ được lưu cục bộ.",
        ) from exc

    return {
        "success": True,
        "user_key": user_history_key(email)[:16],
        "count": len(saved),
        "messages": saved,
    }


@router.delete("/history")
def delete_capybara_history(
    request: Request,
    x_fitsense_user: Annotated[str | None, Header(alias="X-FitSense-User")] = None,
) -> dict[str, Any]:
    email = _resolve_client_user(request, expected_user=x_fitsense_user, require_auth=True)
    try:
        cleared = clear_chat_history(email)
    except OSError as exc:
        logger.exception(
            "Failed to delete Capybara chat history for user %s",
            user_history_key(email)[:16],
        )
        raise HTTPException(
            status_code=500,
            detail="Không thể xóa lịch sử trò chuyện trên máy chủ. Dữ liệu mới được xóa cục bộ.",
        ) from exc

    return {
        "success": True,
        "authenticated": True,
        "cleared": cleared,
    }

