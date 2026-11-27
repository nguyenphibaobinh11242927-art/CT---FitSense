"""Capybara's Vietnamese chat response and action proposals for SCRUM-30."""

from datetime import date
import os
import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.adaptive_weekly_plan import DAYS
from src.exercise_library import INJURIES
from src.school_ai import FitAIServiceError, complete_with_school_ai


Intent = Literal["QA_FITNESS_APP", "INJURY_REPORT", "RESCHEDULE_DELOAD"]
Joint = Literal["knee", "wrist", "shoulder", "lower_back"]
Action = Literal["swap_exercise_for_injury", "move_workout_day", "apply_instant_deload"]

SIGNATURE = "🦫✨"
CAPYBARA_SYSTEM_PROMPT = """
Bạn là Capybara của FitSense, trợ lý calisthenics nói tiếng Việt thân thiện, vui và đồng cảm.
Trả về đúng một đối tượng JSON có hai trường: intent và reply.
- QA_FITNESS_APP: hỏi kiến thức thể hình hoặc cách dùng FitSense.
- INJURY_REPORT: người dùng báo đau hoặc chấn thương của chính họ.
- RESCHEDULE_DELOAD: người dùng yêu cầu dời lịch hoặc giảm tải.
Phân biệt câu hỏi kiến thức, câu giả định và câu phủ định với yêu cầu thật.
Trả lời ngắn gọn, không chẩn đoán, không tự nhận đã đổi bài hoặc cập nhật lịch.
Chỉ mô tả tính năng FitSense đã biết: Kế hoạch, Thư viện, Live HUD và Đánh giá.
Kết thúc câu trả lời bằng 🦫✨.
""".strip()


class IntentParams(BaseModel):
    """Inputs understood by the workout dispatcher."""

    joint: Joint | None = None
    from_day: str | None = None
    to_day: str | None = None
    percentage: float | None = None


class CapybaraReply(BaseModel):
    """A classification and an optional proposal. No workout is changed here."""

    intent: Intent
    action: Action | None = None
    params: IntentParams = Field(default_factory=IntentParams)
    reply: str


class _OnlineReply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    reply: str = Field(min_length=1, max_length=700)


_JOINT_TERMS: dict[Joint, str] = {
    "knee": r"(?:khop )?goi",
    "wrist": r"co tay",
    "shoulder": r"(?:khop )?vai",
    "lower_back": r"lung duoi|that lung",
}
_SYMPTOM = r"(?:dau|nhuc|sung|e|chan thuong)"
_MOVE = re.compile(r"\b(?:doi|doi lai|chuyen|hoan doi|chuyen doi|lui|hoan|sap xep lai) (?:lich|buoi|ngay|thu|t[2-7]|hom nay|chu nhat|cn|tu|sang|qua)\b")
_DELOAD = re.compile(r"\b(?:deload|giam (?:tai|khoi luong|cuong do|volume|so rep|so hiep)|tap nhe (?:hon|lai))\b")
_HYPOTHETICAL = re.compile(r"\b(?:gia su|neu|co (?:the )?(?:gay|lam))\b|^(?:cach|tai sao)\b")
_NON_ACTION = re.compile(
    r"^(?:hom nay[,.]? )?(?:(?:minh|toi|em) )?(?:"
    r"(?:dung|khoi) (?:doi|chuyen|lui|hoan|giam|deload|tap nhe)|"
    r"khong (?:(?:con|bi|thay|he) )?(?:dau|nhuc|sung|chan thuong)|"
    r"(?:khong|chua) (?:(?:can|muon) )?(?:doi|chuyen|lui|hoan|giam|deload|tap nhe)|"
    r"het (?:dau|nhuc|sung)|(?:ban|nguoi yeu) (?:toi|minh|em) (?:bi )?(?:dau|nhuc|sung|chan thuong)"
    r")\b"
)
_EDUCATIONAL = re.compile(
    r"^(?:chi (?:minh|toi|em) )?cach\b|\b(?:la gi|nghia la gi|nhu the nao|the nao)\b"
)
_DAY = re.compile(
    r"\b(?:thu ?[2-7]|thu (?:hai|ba|tu|nam|sau|bay)|t[2-7]|chu nhat|cn|hom nay|ngay mai)\b"
)
_DAY_INDEX = {
    **{f"thu {word}": index for index, word in enumerate(("hai", "ba", "tu", "nam", "sau", "bay"))},
    "chu nhat": 6,
    "cn": 6,
}
_DESTINATION = re.compile(r"\b(?:sang|qua|den|toi|vao) +$")
_PERCENT = re.compile(r"(?<![\w.,])(-?\d+(?:[.,]\d+)?)\s*(?:%|phan tram\b)")


def _normalize(message: str) -> str:
    text = unicodedata.normalize("NFC", message).casefold()
    # “Đầu gối” alone names a joint, while spoken “đau gối” reports pain.
    text = re.sub(r"\bđầu\s+gối\b", "khớp gối", text)
    text = unicodedata.normalize("NFD", text).replace("đ", "d")
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^\w%.,-]", " ", text)).strip()


def _reply(intent: Intent, message: str, *, action: Action | None = None,
           params: IntentParams | None = None) -> CapybaraReply:
    text = message.strip().removesuffix(SIGNATURE).strip()
    return CapybaraReply(
        intent=intent, action=action, params=params or IntentParams(), reply=f"{text} {SIGNATURE}"
    )


def _resolve_day(token: str, today: date) -> str | None:
    if token == "hom nay":
        return DAYS[today.weekday()]
    if token == "ngay mai":
        tomorrow = today.weekday() + 1
        return DAYS[tomorrow] if tomorrow < len(DAYS) else None
    index = _DAY_INDEX.get(token)
    return DAYS[index if index is not None else int(token[-1]) - 2]


def _reschedule(text: str, today: date) -> CapybaraReply:
    matches = list(_DAY.finditer(text))
    from_day, to_day = None, None
    if 1 <= len(matches) <= 2:
        first = matches[0]
        first_day = _resolve_day(first[0], today)
        first_is_destination = bool(_DESTINATION.search(text[:first.start()]))
        if len(matches) == 2:
            second = matches[1]
            between = text[first.end():second.start()]
            second_day = _resolve_day(second[0], today)
            if _DESTINATION.search(between):
                from_day, to_day = first_day, second_day
            elif first_is_destination:
                to_day = first_day
                if re.search(r"\b(?:tu|buoi|lich) +$", between):
                    from_day = second_day
            elif re.search(r"\bhoan doi\b", text) and re.search(r"\b(?:voi|va)\b", between):
                from_day, to_day = first_day, second_day
        elif first_is_destination:
            to_day = first_day
        else:
            from_day = first_day

    params = IntentParams(from_day=from_day, to_day=to_day)
    if from_day and to_day and from_day != to_day:
        return _reply(
            "RESCHEDULE_DELOAD",
            f"Capy hiểu rồi, bạn muốn dời buổi {from_day} sang {to_day}.",
            action="move_workout_day", params=params,
        )
    question = (
        "Bạn muốn dời buổi sang ngày nào khác trong tuần này?" if from_day
        else "Bạn muốn dời buổi tập nào?" if to_day
        else "Bạn muốn dời buổi tập từ ngày nào sang ngày nào trong tuần này?"
    )
    return _reply("RESCHEDULE_DELOAD", question, params=params)


def _deload(text: str) -> CapybaraReply:
    matches = _PERCENT.findall(text)
    if not matches and not re.search(r"\d|%|phan tram", text):
        percentage = 30.0
    elif len(matches) == 1:
        percentage = float(matches[0].replace(",", "."))
    else:
        percentage = None

    if percentage is None or not 0 < percentage < 100:
        return _reply("RESCHEDULE_DELOAD", "Bạn muốn giảm tải bao nhiêu phần trăm, ví dụ 30%?")
    return _reply(
        "RESCHEDULE_DELOAD", f"Capy hiểu rồi, bạn muốn giảm tải {percentage:g}%.",
        action="apply_instant_deload", params=IntentParams(percentage=percentage / 100),
    )


def _injury(text: str, mentions_schedule_change: bool) -> CapybaraReply | None:
    joints = [
        joint for joint, aliases in _JOINT_TERMS.items()
        if re.search(
            rf"\b{_SYMPTOM} (?:o |vung )?(?:{aliases})\b"
            rf"|\b(?:{aliases}) (?:(?:minh|toi|em|bi|dang|hoi|rat) )*{_SYMPTOM}\b",
            text,
        )
    ]
    if not joints and not re.search(
        rf"^(?:(?:minh|toi|em) )?(?:bi |dang )?{_SYMPTOM}(?: qua| lam)?[.,!?]*$",
        text,
    ):
        return None

    mentioned = [aliases for aliases in _JOINT_TERMS.values() if re.search(rf"\b(?:{aliases})\b", text)]
    if len(joints) != 1 or len(mentioned) > 1:
        return _reply("INJURY_REPORT", "Capy nghe rồi. Vùng nào đang đau hoặc khó chịu nhất vậy?")
    joint = joints[0]
    params = IntentParams(joint=joint)
    if mentions_schedule_change:
        return _reply(
            "INJURY_REPORT", "Capy nghe rồi. Bạn muốn xem bài thay thế hay dời buổi tập?", params=params,
        )
    if joint not in INJURIES:
        return _reply(
            "INJURY_REPORT", "Capy ghi nhận vùng đang khó chịu. Thư viện chưa đủ dữ liệu để đề xuất đổi bài cho vùng này.",
            params=params,
        )
    return _reply(
        "INJURY_REPORT", "Capy nghe rồi. Mình có thể tìm bài thay thế phù hợp với lịch tập của bạn.",
        action="swap_exercise_for_injury", params=params,
    )


def _offline_qa(text: str) -> CapybaraReply:
    if re.search(r"\b(?:chong day|hit dat|push[ -]?ups?)\b", text) and not re.search(r"\b(?:dau|nhuc)\b", text):
        answer = "Khi chống đẩy, thử giữ thân người thẳng và hạ xuống có kiểm soát. Bạn muốn hỏi thêm về tư thế hay số rep?"
    elif re.search(r"\b(?:thu vien|tim bai tap)\b", text):
        answer = "Mở mục Thư viện để tìm bài tập theo tên, nhóm cơ hoặc dụng cụ bạn có."
    elif re.search(r"\b(?:danh gia|tien do|lich su tap)\b", text):
        answer = "Mở mục Đánh giá để xem lịch sử tập và theo dõi tiến độ của mình."
    elif re.search(r"\b(?:ke hoach|lich tap)\b", text):
        answer = "Bạn có thể mở mục Kế hoạch để xem lịch tuần và chọn buổi muốn tập."
    elif re.search(r"\b(?:live hud|camera|dem rep)\b", text):
        answer = "Mở Live HUD rồi chọn tập với camera để đếm rep, hoặc chọn chế độ nhập rep thủ công."
    elif re.search(r"\b(?:deload|giam tai)\b", text):
        answer = "Giảm tải là giảm khối lượng hoặc độ khó của buổi tập. Bạn muốn hỏi cách giảm tải hay đề nghị điều chỉnh lịch?"
    else:
        answer = "Capy có thể giúp bạn tìm hiểu bài tập Calisthenics hoặc cách dùng Kế hoạch, Thư viện và Live HUD. Bạn muốn hỏi phần nào?"
    return _reply("QA_FITNESS_APP", answer)


def classify_intent(message: str, *, today: date | None = None) -> CapybaraReply:
    """Classify and respond locally, without calling FIT-AI or modifying a plan."""
    text = _normalize(message)
    if _NON_ACTION.search(text) or _HYPOTHETICAL.search(text):
        return _offline_qa(text)

    move, deload = bool(_MOVE.search(text)), bool(_DELOAD.search(text))
    injury = _injury(text, move or deload)
    if injury:
        return injury
    if _EDUCATIONAL.search(text):
        return _offline_qa(text)
    if move and deload:
        return _reply("RESCHEDULE_DELOAD", "Bạn muốn dời lịch hay giảm tải buổi tập trước?")
    if move:
        return _reschedule(text, today or date.today())
    if deload:
        return _deload(text)
    return _offline_qa(text)


def respond_to_message(message: str, *, today: date | None = None) -> CapybaraReply:
    """Use Qwen for unanswered language, with a local fallback and no model-created actions."""
    offline = classify_intent(message, today=today)
    if offline.intent != "QA_FITNESS_APP" or not os.getenv("FITAI_API_KEY", "").strip():
        return offline

    text = _normalize(message)
    if _NON_ACTION.search(text):
        return offline

    try:
        raw = complete_with_school_ai(
            message, system_prompt=CAPYBARA_SYSTEM_PROMPT, max_tokens=320, timeout=(2.0, 5.0),
        )
        online = _OnlineReply.model_validate_json(raw)
    except (FitAIServiceError, ValidationError):
        return offline
    if online.intent == "QA_FITNESS_APP" and online.reply.strip().removesuffix(SIGNATURE).strip():
        return _reply(online.intent, online.reply)
    if not (_HYPOTHETICAL.search(text) or _EDUCATIONAL.search(text)):
        if online.intent == "INJURY_REPORT":
            return _reply(online.intent, "Capy muốn hiểu rõ hơn. Bạn đang thấy khó chịu ở vùng nào?")
        if online.intent == "RESCHEDULE_DELOAD":
            return _reply(online.intent, "Bạn muốn dời buổi tập hay giảm tải? Cho Capy thêm chi tiết nha.")
    return offline
