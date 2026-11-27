"""FitSense Modern Decoupled Backend Application.

FastAPI Application serving REST endpoints for Profile, Exercises, Smart Planner,
Live Workout HUD with FSM rep counter, Muscle Recovery Heatmap, and Capybara Mascot.
Also serves modern client-side frontend (HTML5/CSS3/ES6 JS) and static assets.
"""

from pathlib import Path
import mimetypes
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.routers import auth, profile, exercises, planner, session, progress, capybara

ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT_DIR / "frontend"
ASSETS_DIR = ROOT_DIR / "assets"
MODELS_DIR = ROOT_DIR / "models"

# Windows MIME registries may map .mjs to text/plain, which browsers reject for modules.
mimetypes.add_type("text/javascript", ".mjs")

app = FastAPI(
    title="FitSense Calisthenics Platform",
    description="Hệ thống Huấn luyện viên Calisthenics Cá nhân hóa & AI Pose Tracking (Kiến trúc Decoupled Backend + Frontend)",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for local cross-origin development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_no_cache_header(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.endswith((".js", ".mjs", ".css", ".html")) or path == "/" or "/api/" in path:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Include API Routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(exercises.router)
app.include_router(planner.router)
app.include_router(session.router)
app.include_router(progress.router)
app.include_router(capybara.router)


@app.get("/api/health", tags=["System"])
def health_check():
    return {
        "status": "online",
        "platform": "FitSense Calisthenics",
        "version": "2.0.0",
        "architecture": "Decoupled FastAPI + Modern Frontend",
        "ai_model": "FitSense AI Core",
    }


# Mount Static Assets Directory
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

# Mount Static Models Directory (e.g. MediaPipe PoseLandmarker tasks)
if MODELS_DIR.exists():
    app.mount("/models", StaticFiles(directory=str(MODELS_DIR)), name="models")

# Mount Static Frontend Directory (HTML, CSS, JS) at root
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
