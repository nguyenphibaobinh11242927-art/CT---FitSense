"""Exercise Catalog and Search API Router."""

from fastapi import APIRouter, HTTPException, Query, Response
from typing import Optional
from src.exercise_library import (
    CATALOG_PATH,
    EQUIPMENT,
    INJURIES,
    LEVELS,
    MUSCLES,
    load_catalog,
    search_exercises,
    suggest_alternatives,
)
from src.exercise_library_view import muscle_svg
from src.profile import load_profile
from backend.routers.auth import CURRENT_SESSION

router = APIRouter(prefix="/api/exercises", tags=["Exercises"])

_CATALOG = None


def extract_profile_filters(profile: dict | None) -> tuple[set[str] | None, set[str]]:
    if not profile:
        return None, set()
    raw_equip = profile.get("equipment")
    available = None
    if isinstance(raw_equip, list):
        available = set()
        for name in raw_equip:
            label = str(name).lower()
            if "thảm" in label:
                available.add("mat")
            if "ghế" in label or "điểm tựa" in label:
                available.add("chair")
            if "dây kháng lực" in label:
                available.add("band")
    restrictions = set()
    for tag in profile.get("restrictions", []) or []:
        label = str(tag).lower()
        if "cổ tay" in label:
            restrictions.add("wrist")
        if "gối" in label:
            restrictions.add("knee")
        if "vai" in label:
            restrictions.add("shoulder")
    return available, restrictions



def get_catalog():
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = load_catalog(CATALOG_PATH)
    return _CATALOG


@router.get("/meta")
def get_metadata():
    catalog = get_catalog()
    categories = sorted(list(set(ex["category"] for ex in catalog)))
    return {
        "muscles": MUSCLES,
        "equipment": EQUIPMENT,
        "injuries": INJURIES,
        "levels": list(LEVELS),
        "categories": categories,
        "total_exercises": len(catalog),
    }


@router.get("")
def list_exercises(
    query: str = Query(default=""),
    muscle: str = Query(default=""),
    role: str = Query(default="all"),
    equipment: str = Query(default=""),
    difficulty: str = Query(default=""),
    category: str = Query(default=""),
):
    catalog = get_catalog()
    try:
        selected_muscles = [m.strip() for m in muscle.split(",") if m.strip()] if muscle else []
        search_equip = "" if equipment == "__none__" else equipment

        if len(selected_muscles) > 1:
            base_results = search_exercises(
                catalog=catalog,
                query=query,
                muscle="",
                role=role,
                equipment=search_equip,
                difficulty=difficulty,
                category=category,
            )
            results = []
            for ex in base_results:
                ex_muscles = (
                    ex["primary_muscles"] if role == "primary" else
                    ex["secondary_muscles"] if role == "secondary" else
                    ex["primary_muscles"] + ex["secondary_muscles"]
                )
                if any(m in ex_muscles for m in selected_muscles):
                    results.append(ex)
        else:
            single_muscle = selected_muscles[0] if selected_muscles else ""
            results = search_exercises(
                catalog=catalog,
                query=query,
                muscle=single_muscle,
                role=role,
                equipment=search_equip,
                difficulty=difficulty,
                category=category,
            )

        if equipment == "__none__":
            results = [ex for ex in results if not ex.get("equipment")]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    
    # Check user limitations from active profile
    email = CURRENT_SESSION.get("user_email")
    profile = load_profile(email) if email else {}
    available, limitations = extract_profile_filters(profile)
    
    enriched = []
    for ex in results:
        avoid_if = set(ex.get("avoid_if", []))
        has_warning = bool(limitations.intersection(avoid_if))
        enriched.append({
            **ex,
            "has_personal_warning": has_warning,
            "warning_tag": "⚠️ Hạn chế cá nhân" if has_warning else None,
        })
    
    return {
        "count": len(enriched),
        "exercises": enriched,
    }


@router.get("/{exercise_id}")
def get_exercise_detail(exercise_id: str):
    catalog = get_catalog()
    for ex in catalog:
        if ex["id"] == exercise_id:
            email = CURRENT_SESSION.get("user_email")
            profile = load_profile(email) if email else {}
            available, limitations = extract_profile_filters(profile)
            
            avoid_if = set(ex.get("avoid_if", []))
            has_warning = bool(limitations.intersection(avoid_if))
            alts = suggest_alternatives(ex, catalog, available_equipment=available, limitations=limitations)
            svg_content = muscle_svg(ex.get("primary_muscles", []), ex.get("secondary_muscles", []))
            
            return {
                **ex,
                "muscle_svg": svg_content,
                "has_personal_warning": has_warning,
                "personal_warning_message": (
                    "⚠️ Hồ sơ của bạn có ghi nhận hạn chế liên quan (như khớp gối/cổ tay). "
                    "Không nên tự thực hiện bài này khi chưa được chuyên gia đánh giá hoặc hãy chọn bài thay thế bên dưới."
                    if has_warning else None
                ),
                "suggested_alternatives": [
                    {"id": a["id"], "name": a["name"], "difficulty": a.get("difficulty", "Beginner")}
                    for a in alts
                ],
            }
    raise HTTPException(status_code=404, detail=f"Không tìm thấy bài tập với mã: {exercise_id}")


@router.get("/{exercise_id}/svg")
def get_exercise_svg(exercise_id: str):
    catalog = get_catalog()
    ex = next((e for e in catalog if e["id"] == exercise_id), None)
    if not ex:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập")
    svg_content = muscle_svg(ex.get("primary_muscles", []), ex.get("secondary_muscles", []))
    return Response(content=svg_content, media_type="image/svg+xml")



@router.get("/{exercise_id}/alternatives")
def get_exercise_alternatives(exercise_id: str):
    catalog = get_catalog()
    exercise = next((ex for ex in catalog if ex["id"] == exercise_id), None)
    if not exercise:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập")
    
    # Check user limitations from active profile
    email = CURRENT_SESSION.get("user_email", "user@fitsense.local")
    profile = load_profile(email) or {}
    
    # Map user profile restrictions to injury keys
    limitations = set()
    for r in profile.get("restrictions", []):
        r_low = r.lower()
        if "gối" in r_low or "knee" in r_low:
            limitations.add("knee")
        if "cổ tay" in r_low or "wrist" in r_low:
            limitations.add("wrist")
            
    alternatives = suggest_alternatives(
        exercise=exercise,
        catalog=catalog,
        limitations=limitations,
    )
    
    return {
        "exercise_id": exercise_id,
        "exercise_name": exercise["name"],
        "count": len(alternatives),
        "alternatives": alternatives,
    }
