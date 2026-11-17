#!/usr/bin/env python3
"""Run FitSense Web Server (Decoupled Backend + Frontend)."""

import os
import sys
import subprocess

def ensure_dependencies():
    """Kiểm tra và tự động cài đặt thư viện cần thiết nếu còn thiếu."""
    missing = []
    try:
        import fastapi
    except ImportError:
        missing.append("fastapi")
    try:
        import uvicorn
    except ImportError:
        missing.append("uvicorn")

    if missing:
        print("⚠️ Phát hiện thiếu thư viện:", ", ".join(missing))
        print("🔄 Đang tự động cài đặt các thư viện cần thiết vào môi trường Python...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print("✅ Đã cài đặt thành công:", ", ".join(missing))
        except Exception as exc:
            print("❌ Không thể tự động cài đặt. Vui lòng chạy lệnh sau trên PowerShell/CMD:")
            print(f"   pip install -r requirements.txt")
            print(f"   (hoặc: {sys.executable} -m pip install fastapi uvicorn)")
            sys.exit(1)

if __name__ == "__main__":
    ensure_dependencies()
    import uvicorn

    print("=" * 60)
    print("⚡ Starting FitSense Platform (FastAPI + Modern HTML/CSS/JS)")
    print("🌐 Web Application:  http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("=" * 60)
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
