"""Module Lập Kế hoạch Tập luyện Thông minh (Planner View).

Lập lịch tập tuần, tải lên & tự chỉnh sửa kế hoạch cá nhân, chọn bài tập thay thế.
"""

import csv
from datetime import datetime
import io
import json
import pandas as pd
import streamlit as st

from src.planner_generation import DEFAULT_DAYS, generate_ai_schedule, profile_goal_id
from src.school_ai import complete_with_school_ai
from src.workout_planner import GOALS, WorkoutPlanError


def get_today_weekday_name(now: datetime | None = None) -> str:
    """Lấy tên Thứ tiếng Việt theo đồng hồ hiện tại trên máy tính."""
    dt = now or datetime.now()
    return DEFAULT_DAYS[dt.weekday()]


def get_today_schedule_day(
    weekly_schedule: list[dict] | None,
    now: datetime | None = None,
) -> dict | None:
    """Tìm buổi tập của hôm nay trong `weekly_schedule` dựa trên Thứ của máy tính."""
    if not isinstance(weekly_schedule, list) or not weekly_schedule:
        return None
    dt = now or datetime.now()
    idx = dt.weekday()
    today_name = DEFAULT_DAYS[idx]
    for entry in weekly_schedule:
        if isinstance(entry, dict) and str(entry.get("day", "")).strip().lower() == today_name.lower():
            return entry
    if 0 <= idx < len(weekly_schedule) and isinstance(weekly_schedule[idx], dict):
        return weekly_schedule[idx]
    return None


def get_next_active_schedule_day(weekly_schedule: list[dict] | None) -> dict | None:
    """Tìm buổi tập (không phải Rest Day) đầu tiên trong tuần để gợi ý tập bù."""
    if not isinstance(weekly_schedule, list):
        return None
    for entry in weekly_schedule:
        if isinstance(entry, dict) and not entry.get("is_rest") and entry.get("exercises"):
            return entry
    return None


def count_day_target_reps(day_data: dict | None) -> int:
    """Tính tổng số reps mục tiêu từ các bài tập đếm rep trong ngày."""
    if not isinstance(day_data, dict) or day_data.get("is_rest"):
        return 0
    total = 0
    for ex in day_data.get("exercises", []):
        if not isinstance(ex, dict):
            continue
        sets_raw = ex.get("sets", 3)
        sets = int(sets_raw) if isinstance(sets_raw, (int, float)) or str(sets_raw).isdigit() else 3
        reps_raw = ex.get("reps")
        if isinstance(reps_raw, (int, float)):
            total += sets * int(reps_raw)
        elif isinstance(reps_raw, str) and reps_raw.strip().isdigit():
            total += sets * int(reps_raw.strip())
    return max(0, total)


def _normalize_schedule(raw_days: list[dict]) -> list[dict]:
    """Chuẩn hóa danh sách buổi tập thành đúng 7 ngày (Thứ 2 -> Chủ Nhật)."""
    by_day = {}
    for idx, entry in enumerate(raw_days):
        if not isinstance(entry, dict):
            raise ValueError("Mỗi ngày trong kế hoạch phải là một object hợp lệ.")
        day_label = str(entry.get("day") or DEFAULT_DAYS[idx % 7]).strip()
        exercises = entry.get("exercises") or []
        if not isinstance(exercises, list):
            raise ValueError(f"Danh sách bài tập của '{day_label}' phải là một mảng.")
        clean_exercises = []
        for ex in exercises:
            if not isinstance(ex, dict) or not str(ex.get("name", "")).strip():
                raise ValueError(f"Mỗi bài tập trong '{day_label}' cần có tên bài tập (`name`).")
            sets_val = ex.get("sets", 3)
            rest_val = ex.get("rest_sec", 60)
            clean_exercises.append({
                "name": str(ex["name"]).strip(),
                "sets": int(sets_val) if str(sets_val).isdigit() else 3,
                "reps": ex.get("reps", 12),
                "rest_sec": int(rest_val) if str(rest_val).isdigit() else 60,
                "primary_muscle": str(ex.get("primary_muscle", "Toàn thân")),
                "secondary_muscle": str(ex.get("secondary_muscle", "Core")),
                "equipment": str(ex.get("equipment", "Bodyweight")),
                "difficulty": str(ex.get("difficulty", "Beginner")),
                "substitute": str(ex.get("substitute", "Plank Tĩnh (Core Plank)")),
                "form_tip": str(ex.get("form_tip", "Giữ thẳng lưng, gồng chặt cơ bụng.")),
            })
        is_rest = bool(entry.get("is_rest", len(clean_exercises) == 0))
        by_day[day_label] = {
            "day": day_label,
            "focus": str(entry.get("focus") or ("Nghỉ ngơi phục hồi (Rest Day)" if is_rest else "Buổi tập Tự chọn")),
            "is_rest": is_rest,
            "ai_reason": str(entry.get("ai_reason") or "Kế hoạch cá nhân do bạn tải lên / tự chỉnh sửa."),
            "exercises": clean_exercises,
        }

    normalized = []
    for default_day in DEFAULT_DAYS:
        if default_day in by_day:
            normalized.append(by_day[default_day])
        else:
            normalized.append({
                "day": default_day,
                "focus": "Nghỉ ngơi phục hồi (Rest Day)",
                "is_rest": True,
                "ai_reason": "Ngày nghỉ bổ sung mặc định trong tuần.",
                "exercises": [],
            })
    return normalized


def parse_uploaded_plan(file_bytes: bytes, filename: str) -> list[dict]:
    """Đọc và xác thực file kế hoạch cá nhân (.json hoặc .csv) thành `weekly_schedule`."""
    ext = (filename or "").lower().rsplit(".", 1)[-1]
    text = file_bytes.decode("utf-8-sig")

    if ext == "json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"File JSON không hợp lệ: {exc.msg}") from exc
        if isinstance(payload, dict):
            payload = payload.get("weekly_schedule") or payload.get("schedule") or payload.get("days")
        if not isinstance(payload, list) or not payload:
            raise ValueError("File JSON phải chứa danh sách các ngày tập (mảng non-empty).")
        return _normalize_schedule(payload)

    if ext == "csv":
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or "day" not in reader.fieldnames:
            raise ValueError("File CSV cần có ít nhất cột 'day' và 'name' (hoặc 'focus').")
        grouped: dict[str, dict] = {}
        row_count = 0
        for row in reader:
            row_count += 1
            day = (row.get("day") or "").strip()
            if not day:
                continue
            focus = (row.get("focus") or "Kế hoạch Tự chọn").strip()
            ex_name = (row.get("name") or "").strip()
            entry = grouped.setdefault(day, {
                "day": day,
                "focus": focus,
                "is_rest": False,
                "ai_reason": "Nhập từ file kế hoạch CSV cá nhân.",
                "exercises": [],
            })
            if ex_name:
                reps_raw = (row.get("reps") or "12").strip()
                reps_val = int(reps_raw) if reps_raw.isdigit() else reps_raw
                entry["exercises"].append({
                    "name": ex_name,
                    "sets": row.get("sets") or 3,
                    "reps": reps_val,
                    "rest_sec": row.get("rest_sec") or 60,
                    "primary_muscle": (row.get("primary_muscle") or "Toàn thân").strip(),
                    "secondary_muscle": (row.get("secondary_muscle") or "Core").strip(),
                    "equipment": (row.get("equipment") or "Bodyweight").strip(),
                    "difficulty": (row.get("difficulty") or "Beginner").strip(),
                    "substitute": (row.get("substitute") or "Plank Tĩnh (Core Plank)").strip(),
                })
        if row_count == 0 or not grouped:
            raise ValueError("File CSV không có dòng dữ liệu buổi tập nào.")
        for entry in grouped.values():
            entry["is_rest"] = len(entry["exercises"]) == 0
        return _normalize_schedule(list(grouped.values()))

    raise ValueError("Định dạng chưa hỗ trợ. Vui lòng dùng file .json hoặc .csv.")


def _get_exercise_alternatives(current_ex: dict, library: list[dict]) -> list[str]:
    """Lấy danh sách các bài tập thay thế hợp lệ cho hộp chọn."""
    current_name = current_ex.get("name", "")
    options: list[str] = []
    sub = current_ex.get("substitute")
    if isinstance(sub, str) and sub.strip() and sub.strip() != current_name:
        options.append(sub.strip())
    for item in library or []:
        lib_name = item.get("name", "").strip()
        if lib_name and lib_name != current_name and lib_name not in options:
            options.append(lib_name)
    for fallback in [
        "Squat Thể dục (Bodyweight Squat)",
        "Standard Push-up (Hít đất chuẩn)",
        "Glute Bridge (Nâng mông trên thảm)",
        "Plank Tĩnh (Core Plank)",
    ]:
        if fallback != current_name and fallback not in options:
            options.append(fallback)
    return options


def render_planner_view():
    """Hiển thị giao diện lịch tập tuần và giáo án thể thao cá nhân hóa."""
    st.header("📋 Kế hoạch Tập luyện & Lịch tuần Thông minh")
    st.caption("AI tối ưu hóa lịch phân bổ nhóm cơ, đồng thời cho phép bạn tự tải lên & chỉnh sửa giáo án cá nhân.")

    profile = st.session_state.get("user_profile") or {}
    schedule = st.session_state.get("weekly_schedule", [])
    library = st.session_state.get("exercise_library", [])

    c_top1, c_top2 = st.columns([3, 1])
    with c_top1:
        today_name = get_today_weekday_name()
        today_entry = get_today_schedule_day(schedule)
        today_focus = today_entry.get("focus", "Chưa thiết lập") if today_entry else "Chưa thiết lập"
        st.info(
            f"🎯 **Mục tiêu:** {profile.get('goal', 'Tăng cơ Calisthenics')} | "
            f"**Thời lượng:** {profile.get('session_duration_minutes', 45)} phút/buổi | "
            f"**Hôm nay ({today_name}):** {today_focus}"
        )
    with c_top2:
        goals = list(GOALS)
        saved_goal = profile_goal_id(profile.get("goal") or "")
        goal = st.selectbox(
            "Mục tiêu giáo án AI", goals, format_func=GOALS.__getitem__,
            index=goals.index(saved_goal) if saved_goal else None, placeholder="Chọn mục tiêu",
        )
        if st.button("🔄 Tái lập Kế hoạch AI", disabled=goal is None, use_container_width=True):
            try:
                with st.spinner("Đang tạo giáo án tuần bằng AI…"):
                    generated = generate_ai_schedule(profile, goal, library, complete_with_school_ai)
            except WorkoutPlanError as error:
                st.error(str(error))
            else:
                st.session_state["weekly_schedule"] = generated
                st.session_state.pop("custom_plan_source", None)
                for key in list(st.session_state):
                    if key.startswith(("edit_focus_", "edit_rest_", "editor_df_", "select_sub_")):
                        del st.session_state[key]
                st.toast("Đã tạo giáo án AI cho tuần này.", icon="✅")
                st.rerun()

    # Tải lên kế hoạch cá nhân (.json / .csv)
    with st.expander("📤 Tự Tải lên Kế hoạch Tập luyện Cá nhân (JSON / CSV)", expanded=False):
        st.caption("Bạn có thể tải lên giáo án tự thiết kế (JSON hoặc CSV) rồi chỉnh sửa trực tiếp từng ngày bên dưới.")
        sample_plan_json = json.dumps(schedule[:2] if schedule else [
            {
                "day": "Thứ 2",
                "focus": "Thân trên & Core",
                "is_rest": False,
                "exercises": [
                    {"name": "Standard Push-up (Hít đất chuẩn)", "sets": 3, "reps": 12, "rest_sec": 60, "primary_muscle": "Ngực"}
                ],
            }
        ], ensure_ascii=False, indent=2)
        dl_col1, dl_col2 = st.columns([2.2, 1])
        with dl_col1:
            uploaded_plan = st.file_uploader(
                "Chọn file kế hoạch (.json hoặc .csv):",
                type=["json", "csv"],
                key="planner_custom_upload",
            )
            if uploaded_plan is not None:
                if st.button("✅ Nạp kế hoạch từ file này", key="planner_apply_upload_btn", type="primary"):
                    try:
                        parsed = parse_uploaded_plan(uploaded_plan.getvalue(), uploaded_plan.name)
                        st.session_state["weekly_schedule"] = parsed
                        st.session_state["custom_plan_source"] = uploaded_plan.name
                        st.success(f"Đã tải kế hoạch cá nhân từ `{uploaded_plan.name}` thành công! Bạn có thể chỉnh sửa tự do từng ngày ở các tab bên dưới.")
                        st.rerun()
                    except ValueError as err:
                        st.error(f"Không thể đọc file kế hoạch: {err}")
        with dl_col2:
            st.download_button(
                label="⬇️ Tải file JSON mẫu",
                data=sample_plan_json.encode("utf-8"),
                file_name="fitsense_plan_template.json",
                mime="application/json",
                use_container_width=True,
            )

    if st.session_state.get("custom_plan_source"):
        st.caption(f"📁 Đang sử dụng kế hoạch cá nhân: `{st.session_state['custom_plan_source']}` (có thể chỉnh sửa bất kỳ ngày nào).")

    st.subheader("Lịch phân bổ nhóm cơ trong tuần")

    tabs = st.tabs([f"Thứ {i+2}" if i < 6 else "Chủ Nhật" for i in range(7)])

    for i, tab in enumerate(tabs):
        with tab:
            day_label = f"Thứ {i+2}" if i < 6 else "Chủ Nhật"
            day_data = schedule[i] if i < len(schedule) else {"day": day_label, "focus": "Nghỉ ngơi phục hồi", "is_rest": True, "exercises": []}

            if day_data.get("is_rest", False):
                st.success("🌱 **Ngày Nghỉ Phục Hồi Hoàn Toàn (Rest & Active Recovery)**")
                st.write("- Hoạt động khuyến nghị: Đi bộ nhẹ nhàng 20 phút, giãn cơ toàn thân hoặc tập hít thở.")
                st.caption("💡 Cơ bắp không phát triển trong lúc tập, chúng phục hồi và phát triển khi bạn nghỉ ngơi!")
            else:
                col_f1, col_f2 = st.columns([3, 1])
                with col_f1:
                    st.markdown(f"**Trọng tâm buổi tập:** `{day_data.get('focus', 'Toàn thân')}`")
                    st.caption(f"💡 **Lý do / Ghi chú:** {day_data.get('ai_reason', 'Tối ưu kích thích cơ bắp an toàn cho khớp.')}")
                with col_f2:
                    if st.button("🚀 Tập ngay buổi này", key=f"start_btn_{i}", type="primary", use_container_width=True):
                        st.session_state["selected_session_day"] = day_data.get("day", day_label)
                        st.session_state["active_workout"] = day_data
                        st.session_state["pending_navigation"] = "⚡ Phòng tập Trực tiếp (HUD)"
                        st.session_state["nav_selection"] = "⚡ Phòng tập Trực tiếp (HUD)"
                        st.rerun()

                st.markdown("#### Danh sách bài tập phân bổ:")
                exercises = day_data.get("exercises", [])
                for ex_idx, ex in enumerate(exercises):
                    hold = ex.get("hold_seconds", 0)
                    hold_label = f", giữ {hold}s mỗi rep" if hold else ""
                    exercise_label = (
                        f"Bài {ex_idx + 1}: {ex.get('name')} — {ex.get('sets')} Sets × {ex.get('reps')} Reps "
                        f"(Nghỉ {ex.get('rest_sec')}s{hold_label})"
                    )
                    with st.expander(exercise_label, expanded=True):
                        c1, c2, c3 = st.columns([1.8, 1.1, 1.5])
                        with c1:
                            st.write(f"- **Nhóm cơ chính:** `{ex.get('primary_muscle')}`")
                            st.write(f"- **Nhóm cơ bổ trợ:** `{ex.get('secondary_muscle', 'Không')}`")
                            st.write(f"- **Lưu ý form:** {ex.get('form_tip', 'Giữ thẳng lưng, gồng chặt cơ bụng.')}")
                        with c2:
                            st.write(f"- **Dụng cụ:** `{ex.get('equipment', 'Bodyweight')}`")
                            st.write(f"- **Độ khó:** `{ex.get('difficulty', 'Intermediate')}`")
                        with c3:
                            if "ai_alternative" in ex:
                                alternative = ex["ai_alternative"]
                                if alternative and st.button(
                                    f"Đổi sang {alternative['name']}", key=f"apply_swap_{i}_{ex_idx}",
                                ):
                                    previous = {key: value for key, value in ex.items() if key != "ai_alternative"}
                                    updated = list(exercises)
                                    updated[ex_idx] = {**alternative, "ai_alternative": previous}
                                    st.session_state["weekly_schedule"] = [
                                        *schedule[:i], {**day_data, "exercises": updated}, *schedule[i + 1:],
                                    ]
                                    st.rerun()
                                continue
                            alt_options = _get_exercise_alternatives(ex, library)
                            chosen_sub = st.selectbox(
                                "Chọn bài tập thay thế:",
                                options=alt_options,
                                key=f"select_sub_{i}_{ex_idx}",
                            )
                            if st.button("✅ Đổi bài", key=f"apply_swap_{i}_{ex_idx}", use_container_width=True):
                                updated_schedule = list(schedule)
                                updated_day = dict(updated_schedule[i])
                                updated_exs = [dict(item) for item in updated_day.get("exercises", [])]
                                old_name = updated_exs[ex_idx].get("name")
                                updated_exs[ex_idx]["substitute"] = old_name
                                updated_exs[ex_idx]["name"] = chosen_sub
                                for lib_item in library:
                                    if lib_item.get("name") == chosen_sub:
                                        pm = lib_item.get("primary_muscle")
                                        if not pm and isinstance(lib_item.get("primary_muscles"), list):
                                            from src.exercise_library import MUSCLES
                                            pm = ", ".join(MUSCLES.get(m, m) for m in lib_item["primary_muscles"])
                                        eq = lib_item.get("equipment")
                                        if isinstance(eq, list):
                                            from src.exercise_library import EQUIPMENT
                                            eq = ", ".join(EQUIPMENT.get(e, e) for e in eq) or "Bodyweight"
                                        updated_exs[ex_idx]["primary_muscle"] = pm or updated_exs[ex_idx].get("primary_muscle")
                                        updated_exs[ex_idx]["equipment"] = eq or updated_exs[ex_idx].get("equipment")
                                        updated_exs[ex_idx]["difficulty"] = lib_item.get("difficulty", updated_exs[ex_idx].get("difficulty"))
                                        break
                                updated_day["exercises"] = updated_exs
                                updated_schedule[i] = updated_day
                                st.session_state["weekly_schedule"] = updated_schedule
                                st.toast(f"Đã đổi sang bài: {chosen_sub}", icon="✅")
                                st.rerun()

            # Trình chỉnh sửa kế hoạch trực tiếp cho từng ngày
            with st.expander(f"✏️ Tự chỉnh sửa giáo án {day_label}", expanded=False):
                new_focus = st.text_input(
                    "Trọng tâm buổi tập:",
                    value=day_data.get("focus", ""),
                    key=f"edit_focus_{i}",
                )
                is_rest_edit = st.checkbox(
                    "Đặt ngày này thành Nghỉ phục hồi (Rest Day)",
                    value=bool(day_data.get("is_rest", False)),
                    key=f"edit_rest_{i}",
                )
                edit_rows = [
                    {
                        "Bài tập": ex.get("name", ""),
                        "Số Hiệp (Sets)": int(ex.get("sets", 3)) if str(ex.get("sets", 3)).isdigit() else 3,
                        "Số Reps / Thời gian": str(ex.get("reps", 12)),
                        "Nghỉ (giây)": int(ex.get("rest_sec", 60)) if str(ex.get("rest_sec", 60)).isdigit() else 60,
                        "Nhóm cơ": ex.get("primary_muscle", "Toàn thân"),
                    }
                    for ex in day_data.get("exercises", [])
                ]
                df_editor = pd.DataFrame(
                    edit_rows or [{"Bài tập": "Squat Thể dục (Bodyweight Squat)", "Số Hiệp (Sets)": 3, "Số Reps / Thời gian": "12", "Nghỉ (giây)": 60, "Nhóm cơ": "Đùi & Mông"}]
                )
                edited_df = st.data_editor(
                    df_editor,
                    num_rows="dynamic",
                    use_container_width=True,
                    key=f"editor_df_{i}",
                )
                if st.button(f"💾 Lưu chỉnh sửa {day_label}", key=f"save_day_edit_{i}", type="primary"):
                    updated_schedule = list(schedule)
                    while len(updated_schedule) <= i:
                        updated_schedule.append({"day": DEFAULT_DAYS[len(updated_schedule)], "focus": "Nghỉ", "is_rest": True, "exercises": []})
                    if is_rest_edit:
                        updated_schedule[i] = {
                            "day": day_data.get("day", day_label),
                            "focus": new_focus or "Nghỉ ngơi phục hồi (Rest Day)",
                            "is_rest": True,
                            "ai_reason": "Chỉnh sửa thủ công bởi người dùng.",
                            "exercises": [],
                        }
                    else:
                        new_exs = []
                        for _, r in edited_df.iterrows():
                            ex_title = str(r.get("Bài tập", "")).strip()
                            if not ex_title:
                                continue
                            reps_s = str(r.get("Số Reps / Thời gian", "12")).strip()
                            reps_val = int(reps_s) if reps_s.isdigit() else reps_s
                            sets_raw = r.get("Số Hiệp (Sets)", 3)
                            rest_raw = r.get("Nghỉ (giây)", 60)
                            new_exs.append({
                                "name": ex_title,
                                "sets": int(sets_raw) if pd.notna(sets_raw) else 3,
                                "reps": reps_val,
                                "rest_sec": int(rest_raw) if pd.notna(rest_raw) else 60,
                                "primary_muscle": str(r.get("Nhóm cơ", "Toàn thân") or "Toàn thân"),
                                "secondary_muscle": "Core",
                                "equipment": "Bodyweight",
                                "difficulty": "Beginner",
                                "substitute": "Plank Tĩnh (Core Plank)",
                            })
                        updated_schedule[i] = {
                            "day": day_data.get("day", day_label),
                            "focus": new_focus or "Buổi tập Tự chỉnh sửa",
                            "is_rest": len(new_exs) == 0,
                            "ai_reason": "Kế hoạch đã được bạn tự chỉnh sửa.",
                            "exercises": new_exs,
                        }
                    st.session_state["weekly_schedule"] = updated_schedule
                    st.success(f"Đã lưu thay đổi cho {day_label}!")
                    st.rerun()
