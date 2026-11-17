"""Capybara Workout Mascot Companion Router."""

import random
from fastapi import APIRouter
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
