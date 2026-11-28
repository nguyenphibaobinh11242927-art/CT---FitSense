"""Lưu lịch FastAPI theo tài khoản và tuần, không dùng chung với Streamlit."""
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
import json
import os
import tempfile
from src.capybara_actions import validate_schedule

STORE = Path(__file__).resolve().parents[1] / 'data' / 'private' / 'api_weekly_plans'


def plan_path(email, today=None):
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    key = sha256(email.strip().lower().encode()).hexdigest()
    return STORE / f'{key}_{monday.isoformat()}.json'


def read_plan(email, today=None):
    path = plan_path(email, today)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    validate_schedule(data)
    return data


def save_plan(email, plan, today=None):
    validate_schedule(plan)
    path = plan_path(email, today)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(plan, stream, ensure_ascii=False, indent=2, allow_nan=False)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
