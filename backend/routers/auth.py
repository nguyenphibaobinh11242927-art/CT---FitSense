"""Authentication and User Session Router."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, Request, Response
from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token

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
SESSION_COOKIE_NAME = "fitsense_session"
SESSION_TTL_SECONDS = 12 * 60 * 60
_DEVELOPMENT_SESSION_SECRET = secrets.token_bytes(32)


@router.get("/config")
def get_auth_config():
    """Return public authentication configuration."""
    client_id = _google_client_id()
    return {
        "google_client_id": client_id,
        "google_auth_enabled": bool(client_id),
    }


def _google_client_id() -> str:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id and OAUTH_CONFIG_FILE.exists():
        try:
            with OAUTH_CONFIG_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
                client_id = data.get("google_client_id", "").strip()
        except (OSError, ValueError, AttributeError):
            client_id = ""
    return client_id or DEFAULT_GOOGLE_CLIENT_ID


def verify_google_credential(credential: str) -> dict[str, Any]:
    try:
        identity = id_token.verify_oauth2_token(
            credential,
            GoogleRequest(),
            audience=_google_client_id(),
        )
    except TransportError as exc:
        raise HTTPException(status_code=503, detail="Không thể kết nối để xác minh tài khoản Google. Vui lòng thử lại.") from exc
    except (GoogleAuthError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Thông tin xác thực Google không hợp lệ hoặc đã hết hạn.") from exc

    if not isinstance(identity, dict):
        raise HTTPException(status_code=401, detail="Google không trả về danh tính hợp lệ.")
    email = str(identity.get("email", "")).strip().lower()
    if not identity.get("email_verified") or not is_valid_email(email) or not identity.get("sub"):
        raise HTTPException(status_code=401, detail="Tài khoản Google chưa xác minh email hoặc thiếu thông tin hợp lệ.")
    return {
        "email": email,
        "name": str(identity.get("name") or email.split("@")[0]).strip(),
        "avatar_url": identity.get("picture"),
        "google_id": str(identity["sub"]),
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

# In-memory session store for current active session (Default: NOT logged in)
CURRENT_SESSION = {
    "user_email": None,
    "is_logged_in": False,
}


def _session_signing_key() -> bytes:
    secret = os.getenv("FITNESS_SESSION_SECRET", "").strip()
    if not secret:
        return _DEVELOPMENT_SESSION_SECRET
    key = secret.encode("utf-8")
    if len(key) < 32:
        raise RuntimeError("FITNESS_SESSION_SECRET must be at least 32 bytes.")
    return key


def create_session_token(email: str, now: int | None = None) -> str:
    expires_at = (int(time.time()) if now is None else now) + SESSION_TTL_SECONDS
    payload = f"{email.strip().lower()}\n{expires_at}".encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(_session_signing_key(), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{encoded_payload}.{encoded_signature}"


def authenticated_email(request: Request, now: int | None = None) -> str | None:
    token = request.cookies.get(SESSION_COOKIE_NAME, "")
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        payload = base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
        signature = base64.urlsafe_b64decode(encoded_signature + "=" * (-len(encoded_signature) % 4))
        expected = hmac.new(_session_signing_key(), encoded_payload.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            return None
        email_bytes, expires_bytes = payload.rsplit(b"\n", 1)
        email = email_bytes.decode("utf-8").strip().lower()
        expires_at = int(expires_bytes)
        current_time = int(time.time()) if now is None else now
        if not email or expires_at <= current_time:
            return None
        return email
    except (ValueError, UnicodeDecodeError, TypeError):
        return None


def set_session_cookie(response: Response, request: Request, email: str) -> None:
    secure_cookie = request.url.scheme == "https" or os.getenv("FITNESS_COOKIE_SECURE", "").lower() in {
        "1", "true", "yes",
    }
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(email),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        path="/",
    )


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
    email = authenticated_email(request)
    if not email:
        return {
            "is_logged_in": False,
            "user": None,
        }

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

    return {
        "is_logged_in": True,
        "user": profile,
    }


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response):
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
        if not isinstance(expected_hash, str) or not hmac.compare_digest(expected_hash, _hash_password(password)):
            raise HTTPException(status_code=401, detail="Mật khẩu không chính xác. Vui lòng thử lại!")
    else:
        # Check if this user had a profile created previously
        profile_exists = load_profile(email)
        if profile_exists:
            raise HTTPException(
                status_code=401,
                detail="Tài khoản chưa có thông tin đăng nhập. Hãy dùng đúng phương thức đăng nhập đã đăng ký.",
            )
        # Preserve the demo flow for an email that has no existing account or profile.
        user_record = {
            "name": email.split("@")[0].capitalize(),
            "email": email,
            "password_hash": _hash_password(password),
            "auth_provider": "local",
        }
        users[email] = user_record
        save_users(users)

    set_session_cookie(response, request, email)
    CURRENT_SESSION["user_email"] = email
    CURRENT_SESSION["is_logged_in"] = True

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
    }


@router.post("/register")
def register(payload: RegisterRequest, request: Request, response: Response):
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

    set_session_cookie(response, request, email)
    CURRENT_SESSION["user_email"] = email
    CURRENT_SESSION["is_logged_in"] = True

    return {
        "success": True,
        "message": "Đăng ký tài khoản FitSense thành công!",
        "user": profile,
    }


@router.post("/google")
def google_auth(payload: GoogleAuthRequest, request: Request, response: Response):
    """Google Sign-In. Direct login if user exists; otherwise flags as new user."""
    identity = verify_google_credential(payload.credential)
    email = identity["email"]

    users = load_users()
    existing_profile = load_profile(email)

    if email in users or existing_profile:
        # Existing account -> Sign in immediately
        set_session_cookie(response, request, email)
        CURRENT_SESSION["user_email"] = email
        CURRENT_SESSION["is_logged_in"] = True

        profile = existing_profile or {
            "name": identity["name"],
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
        if identity["avatar_url"]:
            profile["avatar_url"] = identity["avatar_url"]
            save_profile(email, profile)
        elif not existing_profile:
            save_profile(email, profile)

        return {
            "success": True,
            "is_new_user": False,
            "message": f"Đăng nhập thành công với tài khoản Google ({email})!",
            "user": profile,
        }

    # Brand new Google user -> Request onboarding information
    return {
        "success": True,
        "is_new_user": True,
        "google_data": {
            "email": email,
            "name": identity["name"],
            "avatar_url": identity["avatar_url"],
        },
    }


@router.post("/google/complete-registration")
def google_complete_registration(payload: GoogleCompleteRegistrationRequest, request: Request, response: Response):
    """Completes registration for a new Google authenticated user."""
    identity = verify_google_credential(payload.credential)
    email = identity["email"]
    name = payload.name.strip() or identity["name"]

    users = load_users()
    users[email] = {
        "name": name,
        "email": email,
        "auth_provider": "google",
        "avatar_url": identity["avatar_url"],
    }
    save_users(users)

    profile = {
        "name": name,
        "email": email,
        "avatar_url": identity["avatar_url"],
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

    set_session_cookie(response, request, email)
    CURRENT_SESSION["user_email"] = email
    CURRENT_SESSION["is_logged_in"] = True

    return {
        "success": True,
        "message": "Hoàn tất đăng ký tài khoản Google thành công!",
        "user": profile,
    }


@router.post("/logout")
def logout(response: Response):
    CURRENT_SESSION["user_email"] = None
    CURRENT_SESSION["is_logged_in"] = False
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/", samesite="lax")
    return {"success": True, "message": "Đã đăng xuất thành công."}
