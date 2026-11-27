"""Authentication and User Session Router."""

import hashlib
import json
from pathlib import Path
import secrets
import threading
from typing import Any
from fastapi import APIRouter, HTTPException, Request, Response

from backend.schemas import (
    GoogleAuthRequest,
    GoogleCompleteRegistrationRequest,
    LoginRequest,
    RegisterRequest,
)
from src.auth_view import is_valid_email, validate_login_inputs, validate_registration_inputs
from src.profile import load_profile, save_profile

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

USERS_FILE = Path(__file__).resolve().parents[2] / "data" / "private" / "users.json"
OAUTH_CONFIG_FILE = Path(__file__).resolve().parents[2] / "data" / "private" / "oauth_config.json"
DEFAULT_GOOGLE_CLIENT_ID = "211629740739-utd4fhgshgoddif6puq44bq69tl5up8m.apps.googleusercontent.com"


@router.get("/config")
def get_auth_config():
    """Return public authentication configuration."""
    import os
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id and OAUTH_CONFIG_FILE.exists():
        try:
            with OAUTH_CONFIG_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
                client_id = data.get("google_client_id", "").strip()
        except Exception:
            pass
    if not client_id:
        client_id = DEFAULT_GOOGLE_CLIENT_ID
    return {
        "google_client_id": client_id,
        "google_auth_enabled": bool(client_id),
    }


@router.post("/config")
def set_auth_config(payload: dict[str, Any]):
    """Set and persist Google OAuth Client ID."""
    client_id = str(payload.get("google_client_id", "")).strip()
    OAUTH_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OAUTH_CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump({"google_client_id": client_id}, f, indent=2)
    return {
        "success": True,
        "google_client_id": client_id,
        "google_auth_enabled": bool(client_id),
        "message": "Đã lưu cấu hình Google OAuth Client ID thành công!",
    }

# Legacy process-wide session dict kept for older routers; per-client auth uses SESSION_TOKENS.
CURRENT_SESSION = {
    "user_email": None,
    "is_logged_in": False,
}

SESSION_COOKIE_NAME = "fitsense_session"
SESSION_HEADER_NAME = "X-FitSense-Session"
SESSION_TOKENS: dict[str, dict[str, Any]] = {}
_SESSION_LOCK = threading.RLock()


def extract_session_token(request: Request | None) -> str | None:
    """Extract a client's opaque session token from headers or cookies."""
    if request is None:
        return None
    header_token = request.headers.get(SESSION_HEADER_NAME)
    if header_token and header_token.strip():
        return header_token.strip()
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        bearer = auth_header[7:].strip()
        if bearer:
            return bearer
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token and cookie_token.strip():
        return cookie_token.strip()
    return None


def issue_client_session(email: str, response: Response) -> str:
    """Create a dedicated server-side session bound to this client."""
    normalized = email.strip().lower()
    token = secrets.token_urlsafe(32)
    with _SESSION_LOCK:
        SESSION_TOKENS[token] = {
            "user_email": normalized,
            "is_logged_in": True,
        }
        CURRENT_SESSION["user_email"] = normalized
        CURRENT_SESSION["is_logged_in"] = True

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return token


def resolve_authenticated_session(request: Request | None) -> tuple[str | None, str | None]:
    """Resolve authenticated user email strictly from the request's client token.

    Never falls back to the process-wide ``CURRENT_SESSION`` so concurrent clients
    cannot inherit or overwrite each other's identity.
    """
    token = extract_session_token(request)
    if not token:
        return None, None
    with _SESSION_LOCK:
        record = SESSION_TOKENS.get(token)
        if not record or not record.get("is_logged_in"):
            return None, None
        email = record.get("user_email")
    if not isinstance(email, str) or not email.strip():
        return None, None
    return email.strip().lower(), token


def revoke_client_session(request: Request | None, response: Response) -> None:
    """Revoke only the calling client's session token (and legacy global if un-tokenized)."""
    token = extract_session_token(request)
    revoked_email = None
    with _SESSION_LOCK:
        if token:
            record = SESSION_TOKENS.pop(token, None)
            if record:
                revoked_email = record.get("user_email")
        if token is None or (revoked_email and CURRENT_SESSION.get("user_email") == revoked_email):
            CURRENT_SESSION["user_email"] = None
            CURRENT_SESSION["is_logged_in"] = False

    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


def _hash_password(raw_password: str) -> str:
    """Hash password with sha256 and internal salt."""
    salt = "fitsense_hcmus_salt_2026"
    return hashlib.sha256(f"{raw_password}:{salt}".encode("utf-8")).hexdigest()


def load_users() -> dict[str, Any]:
    if not USERS_FILE.exists():
        return {}
    try:
        with USERS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_users(users: dict[str, Any]) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with USERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


@router.get("/me")
def get_current_user(request: Request):
    token = extract_session_token(request)
    if token is not None:
        email, active_token = resolve_authenticated_session(request)
        if not email:
            return {
                "is_logged_in": False,
                "user": None,
            }
    else:
        with _SESSION_LOCK:
            if SESSION_TOKENS:
                return {
                    "is_logged_in": False,
                    "user": None,
                }
            if not CURRENT_SESSION.get("is_logged_in") or not CURRENT_SESSION.get("user_email"):
                return {
                    "is_logged_in": False,
                    "user": None,
                }
            email = CURRENT_SESSION["user_email"]
            active_token = None

    profile = load_profile(email)
    if not profile:
        profile = {
            "name": email.split("@")[0].capitalize(),
            "email": email,
            "age": 22,
            "gender": "Nam",
            "height_cm": 170.0,
            "weight_kg": 65.0,
            "days_per_week": 4,
            "session_duration_minutes": 45,
            "goal": "Tăng cơ & Sức mạnh",
            "fitness_level": "Beginner (Người mới bắt đầu)",
            "environment": "Tại nhà (Home Workout)",
            "restrictions": ["Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)"],
            "equipment": ["Không có dụng cụ (Chỉ tập Bodyweight)"],
        }
        save_profile(email, profile)

    result = {
        "is_logged_in": True,
        "user": profile,
    }
    if active_token:
        result["session_token"] = active_token
    return result


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    email = payload.email.strip().lower()
    password = payload.password or ""

    errors = validate_login_inputs(email, password)
    if errors:
        raise HTTPException(status_code=400, detail=" ".join(errors))

    users = load_users()
    user_record = users.get(email)

    # If user exists in persistent user storage
    if user_record:
        expected_hash = user_record.get("password_hash")
        if expected_hash and expected_hash != _hash_password(password):
            raise HTTPException(status_code=401, detail="Mật khẩu không chính xác. Vui lòng thử lại!")
    else:
        # Check if this user had a profile created previously
        profile_exists = load_profile(email)
        if not profile_exists:
            # Register user on the fly for test/demo emails if password valid
            user_record = {
                "name": email.split("@")[0].capitalize(),
                "email": email,
                "password_hash": _hash_password(password),
                "auth_provider": "local",
            }
            users[email] = user_record
            save_users(users)

    session_token = issue_client_session(email, response)

    profile = load_profile(email)
    if not profile:
        profile = {
            "name": user_record.get("name") if user_record else email.split("@")[0].capitalize(),
            "email": email,
            "age": 22,
            "gender": "Nam",
            "height_cm": 170.0,
            "weight_kg": 65.0,
            "days_per_week": 4,
            "session_duration_minutes": 45,
            "goal": "Tăng cơ & Sức mạnh",
            "fitness_level": "Beginner (Người mới bắt đầu)",
            "environment": "Tại nhà (Home Workout)",
            "restrictions": ["Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)"],
            "equipment": ["Không có dụng cụ (Chỉ tập Bodyweight)"],
        }
        save_profile(email, profile)

    return {
        "success": True,
        "message": f"Chào mừng {profile.get('name')} trở lại với FitSense!",
        "user": profile,
        "session_token": session_token,
    }


@router.post("/register")
def register(payload: RegisterRequest, response: Response):
    email = payload.email.strip().lower()
    name = payload.name.strip()
    password = payload.password

    users = load_users()
    errors = validate_registration_inputs(name, email, password, existing_users=users)
    if errors:
        raise HTTPException(status_code=400, detail=" ".join(errors))

    # Save credentials
    users[email] = {
        "name": name,
        "email": email,
        "password_hash": _hash_password(password),
        "auth_provider": "local",
    }
    save_users(users)

    # Initialize profile
    profile = {
        "name": name,
        "email": email,
        "age": payload.age or 22,
        "gender": payload.gender or "Nam",
        "height_cm": payload.height_cm or 170.0,
        "weight_kg": payload.weight_kg or 65.0,
        "days_per_week": payload.days_per_week or 4,
        "session_duration_minutes": payload.session_duration_minutes or 45,
        "goal": payload.goal or "Tăng cơ & Sức mạnh",
        "fitness_level": payload.fitness_level or "Beginner (Người mới bắt đầu)",
        "environment": payload.environment or "Tại nhà (Home Workout)",
        "restrictions": payload.restrictions or ["Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)"],
        "equipment": payload.equipment or ["Không có dụng cụ (Chỉ tập Bodyweight)"],
    }
    save_profile(email, profile)

    session_token = issue_client_session(email, response)

    return {
        "success": True,
        "message": "Đăng ký tài khoản FitSense thành công!",
        "user": profile,
        "session_token": session_token,
    }


@router.post("/google")
def google_auth(payload: GoogleAuthRequest, response: Response):
    """Google Sign-In. Direct login if user exists; otherwise flags as new user."""
    email = payload.email.strip().lower()
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Địa chỉ Google Email không hợp lệ.")

    users = load_users()
    existing_profile = load_profile(email)

    if email in users or existing_profile:
        # Existing account -> Sign in immediately
        session_token = issue_client_session(email, response)

        profile = existing_profile or {
            "name": payload.name or email.split("@")[0].capitalize(),
            "email": email,
            "age": 22,
            "gender": "Nam",
            "height_cm": 170.0,
            "weight_kg": 65.0,
            "days_per_week": 4,
            "session_duration_minutes": 45,
            "goal": "Tăng cơ & Sức mạnh",
            "fitness_level": "Beginner (Người mới bắt đầu)",
            "environment": "Tại nhà (Home Workout)",
            "restrictions": ["Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)"],
            "equipment": ["Không có dụng cụ (Chỉ tập Bodyweight)"],
        }
        if payload.avatar_url:
            profile["avatar_url"] = payload.avatar_url
            save_profile(email, profile)
        elif not existing_profile:
            save_profile(email, profile)

        return {
            "success": True,
            "is_new_user": False,
            "message": f"Đăng nhập thành công với tài khoản Google ({email})!",
            "user": profile,
            "session_token": session_token,
        }

    # Brand new Google user -> Request onboarding information
    return {
        "success": True,
        "is_new_user": True,
        "google_data": {
            "email": email,
            "name": payload.name or email.split("@")[0].capitalize(),
            "avatar_url": payload.avatar_url,
            "google_id": payload.google_id,
        },
    }


@router.post("/google/complete-registration")
def google_complete_registration(payload: GoogleCompleteRegistrationRequest, response: Response):
    """Completes registration for a new Google authenticated user."""
    email = payload.email.strip().lower()
    name = payload.name.strip()

    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Email không hợp lệ.")

    users = load_users()
    users[email] = {
        "name": name,
        "email": email,
        "auth_provider": "google",
        "avatar_url": payload.avatar_url,
    }
    save_users(users)

    profile = {
        "name": name,
        "email": email,
        "avatar_url": payload.avatar_url,
        "age": payload.age,
        "gender": payload.gender,
        "height_cm": payload.height_cm,
        "weight_kg": payload.weight_kg,
        "days_per_week": payload.days_per_week,
        "session_duration_minutes": payload.session_duration_minutes,
        "goal": payload.goal,
        "fitness_level": payload.fitness_level,
        "environment": payload.environment,
        "restrictions": payload.restrictions,
        "equipment": payload.equipment,
    }
    save_profile(email, profile)

    session_token = issue_client_session(email, response)

    return {
        "success": True,
        "message": "Hoàn tất đăng ký tài khoản Google thành công!",
        "user": profile,
        "session_token": session_token,
    }


@router.post("/logout")
def logout(request: Request, response: Response):
    revoke_client_session(request, response)
    return {"success": True, "message": "Đã đăng xuất thành công."}
