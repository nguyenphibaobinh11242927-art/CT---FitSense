"""Entry point for the FitSense Fitness Web Application.

FitSense — AI Fitness & Calisthenics Workout Assistant.
Hệ thống web hỗ trợ tập luyện thể thao cá nhân hóa với AI Pose Tracking và Adaptive Overload.
"""

import streamlit as st
import html

# Import các màn hình nghiệp vụ
import importlib
from src.auth_view import render_auth_view
import src.profile_view as profile_view_mod
importlib.reload(profile_view_mod)
from src.profile_view import render_profile_view
from src.planner_view import render_planner_view
from src.library_view import render_library_view
from src.session_view import render_session_view
from src.evaluation_view import render_evaluation_view
from src.heatmap_view import render_heatmap_view
from src.progress_view import render_progress_view
import src.capybara_widget as capybara_widget
importlib.reload(capybara_widget)
from src.capybara_widget import render_capybara_companion


def init_app_state(force_reset: bool = False):
    """Khởi tạo trạng thái ban đầu của ứng dụng."""
    if "fitsense_initialized" in st.session_state and not force_reset:
        return

    st.session_state["fitsense_initialized"] = True

    # Trạng thái đăng nhập (Mặc định CHƯA đăng nhập)
    if "is_logged_in" not in st.session_state or force_reset:
        st.session_state["is_logged_in"] = False
        st.session_state["user_profile"] = None

    # Trạng thái hoàn thành bài tập hôm nay (Phục vụ biểu cảm của Capybara)
    if "has_worked_out_today" not in st.session_state or force_reset:
        st.session_state["has_worked_out_today"] = False

    # Chế độ giao diện (Mặc định Đen Xanh)
    if "app_theme" not in st.session_state or force_reset:
        st.session_state["app_theme"] = "dark"
    if "theme_mode_selector" not in st.session_state or force_reset:
        st.session_state["theme_mode_selector"] = "Dark"

    # Cơ sở dữ liệu tài khoản tạm thời
    if "registered_users" not in st.session_state or force_reset:
        st.session_state["registered_users"] = {}

    # Kế hoạch & Lịch tập rèn luyện (Template)
    st.session_state["weekly_schedule"] = [
        {
            "day": "Thứ 2",
            "focus": "Thân trên: Ngực & Tay sau (Push Focus)",
            "is_rest": False,
            "ai_reason": "Tập trung nhóm cơ đẩy; kích thích sợi cơ nhanh và xây dựng sức mạnh cơ bản.",
            "exercises": [
                {"name": "Standard Push-up (Hít đất chuẩn)", "sets": 3, "reps": 12, "rest_sec": 60, "primary_muscle": "Ngực (Chest)", "secondary_muscle": "Tay sau, Vai", "equipment": "Bodyweight", "difficulty": "Intermediate", "substitute": "Knee Push-up"},
                {"name": "Dips trên ghế (Bench Dips)", "sets": 3, "reps": 15, "rest_sec": 45, "primary_muscle": "Tay sau (Triceps)", "secondary_muscle": "Ngực dưới", "equipment": "Ghế / Giường", "difficulty": "Beginner", "substitute": "Diamond Push-up"},
                {"name": "Plank Tĩnh (Core Stability)", "sets": 3, "reps": "45s", "rest_sec": 45, "primary_muscle": "Bụng & Core", "secondary_muscle": "Lưng dưới", "equipment": "Thảm", "difficulty": "Beginner", "substitute": "Dead Bug"},
            ]
        },
        {
            "day": "Thứ 3",
            "focus": "Thân dưới & Mông (Lower Body)",
            "is_rest": False,
            "ai_reason": "Kiểm soát góc gối tối ưu để phát triển cơ đùi trước và cơ mông săn chắc.",
            "exercises": [
                {"name": "Squat Thể dục (Bodyweight Squat)", "sets": 4, "reps": 15, "rest_sec": 60, "primary_muscle": "Đùi trước (Quads)", "secondary_muscle": "Mông", "equipment": "Bodyweight", "difficulty": "Beginner", "substitute": "Wall Sit (Ngồi tựa tường)"},
                {"name": "Glute Bridge (Nâng mông trên thảm)", "sets": 3, "reps": 20, "rest_sec": 45, "primary_muscle": "Mông (Glutes)", "secondary_muscle": "Đùi sau", "equipment": "Thảm", "difficulty": "Beginner", "substitute": "Single Leg Bridge"},
                {"name": "Calf Raises (Nhón bắp chân)", "sets": 3, "reps": 25, "rest_sec": 30, "primary_muscle": "Bắp chân", "secondary_muscle": "Cổ chân", "equipment": "Bodyweight", "difficulty": "Beginner", "substitute": "Seated Calf Raise"},
            ]
        },
        {
            "day": "Thứ 4",
            "focus": "Nghỉ ngơi phục hồi cơ bắp (Rest Day)",
            "is_rest": True,
            "ai_reason": "Chu kỳ 48h để cơ bắp tổng hợp protein và tái tạo glycogen năng lượng.",
            "exercises": []
        },
        {
            "day": "Thứ 5",
            "focus": "Thân trên: Lưng xô & Tay trước (Pull Focus)",
            "is_rest": False,
            "ai_reason": "Cân bằng cơ đối kháng thân trên, cải thiện tư thế đứng thẳng chống gù lưng.",
            "exercises": [
                {"name": "Inverted Rows (Hít xà nghiêng)", "sets": 3, "reps": 10, "rest_sec": 60, "primary_muscle": "Lưng & Xô", "secondary_muscle": "Tay trước", "equipment": "Xà đơn / Khăn", "difficulty": "Intermediate", "substitute": "Band Pull-Apart"},
                {"name": "Dây kháng lực kéo xô (Lat Band Pulldown)", "sets": 3, "reps": 15, "rest_sec": 45, "primary_muscle": "Lưng & Xô", "secondary_muscle": "Vai sau", "equipment": "Dây kháng lực", "difficulty": "Beginner", "substitute": "Superman Hold"},
            ]
        },
        {
            "day": "Thứ 6",
            "focus": "Toàn thân & Sức bền tim mạch (Fullbody Endurance)",
            "is_rest": False,
            "ai_reason": "Đốt mỡ chuyển hóa và tăng cường dung tích thông khí của phổi.",
            "exercises": [
                {"name": "Jumping Jacks (Nhảy dang tay chân nhẹ)", "sets": 3, "reps": "40s", "rest_sec": 45, "primary_muscle": "Toàn thân & Tim mạch", "secondary_muscle": "Bắp chân", "equipment": "Bodyweight", "difficulty": "Beginner", "substitute": "Step Jacks"},
                {"name": "Mountain Climbers (Leo núi trên thảm)", "sets": 3, "reps": 20, "rest_sec": 45, "primary_muscle": "Bụng & Core", "secondary_muscle": "Vai", "equipment": "Thảm", "difficulty": "Intermediate", "substitute": "Plank Shoulder Tap"},
            ]
        },
        {
            "day": "Thứ 7",
            "focus": "Nghỉ ngơi phục hồi (Rest Day)",
            "is_rest": True,
            "ai_reason": "Thư giãn hệ thống thần kinh và dây chằng.",
            "exercises": []
        },
        {
            "day": "Chủ Nhật",
            "focus": "Giãn cơ & Khớp dẻo dai (Active Recovery)",
            "is_rest": True,
            "ai_reason": "Giải phóng căng cứng cơ bắp chuẩn bị năng lượng cho tuần mới.",
            "exercises": []
        }
    ]

    # SCRUM-17: Thư viện chuẩn hoá dùng chung, không hardcode trong UI.
    from src.exercise_library import load_catalog
    st.session_state["exercise_library"] = load_catalog()

    # Bảng nhiệt Phục hồi Cơ bắp
    st.session_state["muscle_recovery"] = {
        "Ngực (Chest)": {"recovery_pct": 95, "hours_left": 0},
        "Lưng & Xô": {"recovery_pct": 100, "hours_left": 0},
        "Đùi trước (Quads)": {"recovery_pct": 70, "hours_left": 10},
        "Mông (Glutes)": {"recovery_pct": 75, "hours_left": 8},
        "Vai (Shoulders)": {"recovery_pct": 90, "hours_left": 0},
        "Tay sau (Triceps)": {"recovery_pct": 85, "hours_left": 0},
        "Bụng & Core": {"recovery_pct": 80, "hours_left": 4},
        "Bắp chân": {"recovery_pct": 100, "hours_left": 0},
    }

    # Kỷ lục Cá nhân & Chuỗi ngày (Bắt đầu từ 0 cho tài khoản mới)
    st.session_state["personal_records"] = {
        "Squat liên tục": "0 Reps",
        "Push-up chuẩn": "0 Reps",
        "Plank giữ tối đa": "0 Giây",
        "Buổi tập dài nhất": "0 Phút",
    }

    st.session_state["streak_info"] = {
        "current_streak": 0,
        "longest_streak": 0,
        "min_threshold_pct": 70,
    }

    st.session_state["session_history"] = []


def apply_custom_styles(theme: str = "dark"):
    """Áp dụng bộ CSS động theo chế độ giao diện: Dark (Đen Xanh) hoặc Light (Trắng Vàng)."""
    if theme == "light":
        # CHẾ ĐỘ SÁNG: TRẮNG VÀNG (White & Sport Gold)
        css = """
        :root {
            --bg-app: #F8FAFC;
            --bg-sidebar: #FFFFFF;
            --bg-card: #FFFFFF;
            --border-card: #E2E8F0;
            --text-main: #0F172A;
            --text-muted: #64748B;
            --accent-primary: #EAB308;
            --accent-gradient: linear-gradient(135deg, #FACC15 0%, #EAB308 100%);
            --accent-glow: rgba(234, 179, 8, 0.4);
            --active-text: #0F172A;
            --card-hover: #FEF9C3;
        }
        .stApp {
            background-color: #F8FAFC !important;
            color: #0F172A !important;
        }
        header[data-testid="stHeader"] {
            background-color: #F8FAFC !important;
            color: #0F172A !important;
        }
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0 !important;
        }
        h1, h2, h3, h4, h5, h6, label, p, span {
            color: #0F172A !important;
        }

        /* 1. KHUNG NHẬP LIỆU: Nền sáng -> Chữ tối */
        div[data-baseweb="input"],
        div[data-baseweb="base-input"],
        div[data-baseweb="input"] input,
        textarea {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 10px !important;
            -webkit-text-fill-color: #0F172A !important;
        }
        div[data-baseweb="input"]:focus-within {
            border-color: #EAB308 !important;
            box-shadow: 0 0 0 2px rgba(234, 179, 8, 0.3) !important;
        }

        /* 2. SELECT & MULTISELECT (Light Theme): Khung sáng (#FFFFFF, viền #CBD5E1) -> Chữ tối (#0F172A) */
        div[data-testid="stSelectbox"],
        div[data-testid="stSelectbox"] > div:first-child,
        div[data-testid="stMultiSelect"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }

        /* Khung nhập liệu có viền rõ ràng, thanh lịch cho Selectbox và Multiselect */
        div[data-testid="stSelectbox"] div.react-aria-Group,
        div[data-testid="stSelectbox"] div[role="group"],
        div[data-testid="stSelectbox"] [class*="e1oobldh0"],
        div[data-testid="stSelectbox"] [data-focus-within],
        div[data-testid="stSelectbox"] > div:nth-child(2) > div,
        div[data-testid="stSelectbox"] > div:nth-child(2) > div > div,
        div[data-testid="stMultiSelect"] div.ew56mvo0,
        div[data-testid="stMultiSelect"] [class*="ew56mvo0"],
        div[data-testid="stMultiSelect"] div[role="group"],
        div[data-testid="stMultiSelect"] > div:nth-child(2),
        div[data-baseweb="select"],
        div[data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
            border: 1.5px solid #CBD5E1 !important;
            color: #0F172A !important;
            border-radius: 10px !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
            box-sizing: border-box !important;
        }

        div[data-testid="stSelectbox"] div.react-aria-Group:focus-within,
        div[data-testid="stSelectbox"] [class*="e1oobldh0"]:focus-within,
        div[data-testid="stMultiSelect"] div.ew56mvo0:focus-within,
        div[data-testid="stMultiSelect"] [class*="ew56mvo0"]:focus-within {
            border-color: #EAB308 !important;
            box-shadow: 0 0 0 2px rgba(234, 179, 8, 0.25) !important;
        }

        div[data-testid="stMultiSelect"] div[data-testid="stMultiSelectTagsContainer"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        div[data-testid="stSelectbox"] button,
        div[data-testid="stSelectbox"] button.react-aria-Button,
        div[data-testid="stSelectbox"] [class*="e1oobldh2"],
        div[data-testid="stSelectbox"] [class*="e1oobldh3"],
        div[data-testid="stMultiSelect"] [class*="ew56mvo7"],
        div[data-testid="stMultiSelect"] [class*="ew56mvo8"] {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        div[data-testid="stSelectbox"] input,
        div[data-testid="stSelectbox"] input.react-aria-Input,
        div[data-testid="stSelectbox"] [class*="e1oobldh1"],
        div[data-testid="stMultiSelect"] input,
        div[data-testid="stMultiSelect"] [class*="ew56mvo6"] {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #0F172A !important;
            -webkit-text-fill-color: #0F172A !important;
            font-size: 14px !important;
            font-weight: 500 !important;
        }
        div[data-testid="stSelectbox"] svg,
        div[data-testid="stMultiSelect"] svg {
            fill: #64748B !important;
        }
        div[data-testid="stMultiSelect"] .ew56mvo3,
        div[data-testid="stMultiSelect"] [data-testid="stMultiSelectTagsContainer"] > span,
        div[data-testid="stMultiSelect"] span:has(svg),
        div[data-baseweb="tag"] {
            background-color: #FEF9C3 !important;
            border: 1px solid #FACC15 !important;
            border-radius: 8px !important;
            color: #854D0E !important;
        }
        div[data-testid="stMultiSelect"] .ew56mvo3 span,
        div[data-testid="stMultiSelect"] [data-testid="stMultiSelectTagsContainer"] > span span,
        div[data-testid="stMultiSelect"] span:has(svg) span,
        div[data-baseweb="tag"] span {
            color: #854D0E !important;
            font-weight: 700 !important;
        }
        div[data-testid="stMultiSelect"] .ew56mvo3 svg,
        div[data-testid="stMultiSelect"] [data-testid="stMultiSelectTagsContainer"] > span svg,
        div[data-testid="stMultiSelect"] span:has(svg) svg,
        div[data-baseweb="tag"] svg {
            fill: #854D0E !important;
        }
        [class*="e1oobldh4"],
        .e1oobldh4,
        [class*="ew56mvo9"],
        .ew56mvo9,
        div[data-testid="stSelectboxVirtualDropdown"],
        div[data-testid="stMultiSelectDropdown"],
        div[data-baseweb="popover"],
        .react-aria-Popover,
        [data-overlay-container] .react-aria-Popover {
            background-color: #FFFFFF !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 10px !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1) !important;
            overflow: hidden !important;
        }
        [class*="e1oobldh5"],
        .e1oobldh5,
        [class*="ew56mvo10"],
        .ew56mvo10,
        .react-aria-ListBox,
        ul[role="listbox"] {
            background-color: #FFFFFF !important;
            border: none !important;
            padding: 4px !important;
        }
        [class*="e1oobldh7"],
        .e1oobldh7,
        [class*="e1oobldh8"],
        .e1oobldh8,
        [class*="ew56mvo12"],
        .ew56mvo12,
        [class*="ew56mvo13"],
        .ew56mvo13,
        li[role="option"],
        div[role="option"],
        .react-aria-ListBoxItem,
        [data-item-hl] {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            -webkit-text-fill-color: #0F172A !important;
            font-size: 14px !important;
            font-weight: 500 !important;
            border-radius: 6px !important;
            margin: 1px 0 !important;
        }
        [class*="e1oobldh7"] *,
        .e1oobldh7 *,
        [class*="ew56mvo12"] *,
        .ew56mvo12 *,
        li[role="option"] *,
        div[role="option"] *,
        .react-aria-ListBoxItem *,
        [data-item-hl] * {
            color: #0F172A !important;
            -webkit-text-fill-color: #0F172A !important;
        }
        [class*="e1oobldh7"]:hover,
        .e1oobldh7:hover,
        [class*="e1oobldh7"][data-hovered],
        [class*="e1oobldh7"][data-focused],
        [class*="e1oobldh7"][aria-selected="true"],
        [class*="ew56mvo12"]:hover,
        .ew56mvo12:hover,
        [class*="ew56mvo12"][data-hovered],
        [class*="ew56mvo12"][data-focused],
        [class*="ew56mvo12"][aria-selected="true"],
        li[role="option"]:hover,
        li[role="option"][aria-selected="true"],
        div[role="option"]:hover,
        div[role="option"][aria-selected="true"],
        .react-aria-ListBoxItem:hover,
        .react-aria-ListBoxItem[data-hovered],
        .react-aria-ListBoxItem[data-focused],
        .react-aria-ListBoxItem[aria-selected="true"] {
            background-color: #FEF9C3 !important;
            color: #854D0E !important;
            -webkit-text-fill-color: #854D0E !important;
        }
        [class*="e1oobldh7"]:hover *,
        .e1oobldh7:hover *,
        [class*="e1oobldh7"][data-hovered] *,
        [class*="e1oobldh7"][data-focused] *,
        [class*="e1oobldh7"][aria-selected="true"] *,
        [class*="ew56mvo12"]:hover *,
        .ew56mvo12:hover *,
        [class*="ew56mvo12"][data-hovered] *,
        [class*="ew56mvo12"][data-focused] *,
        [class*="ew56mvo12"][aria-selected="true"] *,
        li[role="option"]:hover *,
        li[role="option"][aria-selected="true"] *,
        div[role="option"]:hover *,
        div[role="option"][aria-selected="true"] *,
        .react-aria-ListBoxItem:hover *,
        .react-aria-ListBoxItem[data-hovered] *,
        .react-aria-ListBoxItem[data-focused] *,
        .react-aria-ListBoxItem[aria-selected="true"] * {
            color: #854D0E !important;
            -webkit-text-fill-color: #854D0E !important;
        }

        /* 3. ALERTS & NOTIFICATIONS (Light Theme): Khung sáng pastel -> Chữ màu sẫm tương phản cao */
        div.stAlert,
        div[data-testid="stAlert"],
        div[data-testid="stAlertContainer"],
        div[data-testid="stAlert"] > div {
            border-radius: 10px !important;
        }
        /* Alert Info */
        div.stAlert:has([data-testid="stAlertContentInfo"]),
        div[data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]),
        div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]),
        div.stAlert:not(:has([data-testid="stAlertContentSuccess"])):not(:has([data-testid="stAlertContentWarning"])):not(:has([data-testid="stAlertContentError"])),
        div[data-testid="stAlert"]:not(:has([data-testid="stAlertContentSuccess"])):not(:has([data-testid="stAlertContentWarning"])):not(:has([data-testid="stAlertContentError"])),
        div[data-testid="stAlertContainer"]:not(:has([data-testid="stAlertContentSuccess"])):not(:has([data-testid="stAlertContentWarning"])):not(:has([data-testid="stAlertContentError"])) {
            background-color: #EFF6FF !important;
            border: 1.5px solid #60A5FA !important;
        }
        div.stAlert:has([data-testid="stAlertContentInfo"]) *,
        div[data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]) *,
        div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) *,
        div.stAlert:not(:has([data-testid="stAlertContentSuccess"])):not(:has([data-testid="stAlertContentWarning"])):not(:has([data-testid="stAlertContentError"])) *,
        div[data-testid="stAlert"]:not(:has([data-testid="stAlertContentSuccess"])):not(:has([data-testid="stAlertContentWarning"])):not(:has([data-testid="stAlertContentError"])) *,
        div[data-testid="stAlertContainer"]:not(:has([data-testid="stAlertContentSuccess"])):not(:has([data-testid="stAlertContentWarning"])):not(:has([data-testid="stAlertContentError"])) * {
            color: #1E3A8A !important;
        }
        /* Alert Success */
        div.stAlert:has([data-testid="stAlertContentSuccess"]),
        div[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]),
        div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) {
            background-color: #F0FDF4 !important;
            border: 1.5px solid #4ADE80 !important;
        }
        div.stAlert:has([data-testid="stAlertContentSuccess"]) *,
        div[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) *,
        div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) * {
            color: #14532D !important;
        }
        /* Alert Warning */
        div.stAlert:has([data-testid="stAlertContentWarning"]),
        div[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]),
        div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) {
            background-color: #FEF9C3 !important;
            border: 1.5px solid #FACC15 !important;
        }
        div.stAlert:has([data-testid="stAlertContentWarning"]) *,
        div[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) *,
        div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) * {
            color: #713F12 !important;
        }
        /* Alert Error */
        div.stAlert:has([data-testid="stAlertContentError"]),
        div[data-testid="stAlert"]:has([data-testid="stAlertContentError"]),
        div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {
            background-color: #FEF2F2 !important;
            border: 1.5px solid #F87171 !important;
        }
        div.stAlert:has([data-testid="stAlertContentError"]) *,
        div[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) *,
        div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) * {
            color: #7F1D1D !important;
        }
        div[data-testid="stAlert"] code {
            background: rgba(0, 0, 0, 0.08) !important;
            color: #0F172A !important;
            border: 1px solid rgba(0, 0, 0, 0.15) !important;
            border-radius: 4px !important;
            padding: 2px 6px !important;
            font-weight: 700 !important;
        }

        /* 4. BUTTONS (Light Theme) */
        /* Secondary Button: Nền trắng -> Chữ tối */
        button[data-testid="stBaseButton-secondary"],
        div[data-testid="stButton"] > button:not([data-testid="stBaseButton-primary"]) {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
        }
        button[data-testid="stBaseButton-secondary"] *,
        div[data-testid="stButton"] > button:not([data-testid="stBaseButton-primary"]) * {
            color: #0F172A !important;
        }
        button[data-testid="stBaseButton-secondary"]:hover,
        div[data-testid="stButton"] > button:not([data-testid="stBaseButton-primary"]):hover {
            background-color: #FEF9C3 !important;
            border-color: #EAB308 !important;
            color: #854D0E !important;
        }
        button[data-testid="stBaseButton-secondary"]:hover *,
        div[data-testid="stButton"] > button:not([data-testid="stBaseButton-primary"]):hover * {
            color: #854D0E !important;
        }

        /* 5. METRICS (Light Theme) */
        div[data-testid="stMetricValue"] * {
            color: #0F172A !important;
        }
        div[data-testid="stMetricLabel"] * {
            color: #64748B !important;
        }
        div[data-testid="stMetricDelta"] {
            background-color: #DCFCE7 !important;
            border: 1px solid #86EFAC !important;
            border-radius: 12px !important;
            padding: 2px 8px !important;
            display: inline-flex !important;
            align-items: center !important;
        }
        div[data-testid="stMetricDelta"] * {
            color: #15803D !important;
            font-weight: 700 !important;
        }
        div[data-testid="stMetricDelta"] svg {
            fill: #15803D !important;
        }

        /* 6. THẺ & KHUNG CONTAINER (Light Theme) */
        .fitsense-stat-card {
            background: #FFFFFF !important;
            border: 1.5px solid #E2E8F0 !important;
            border-left: 4px solid #EAB308 !important;
            color: #0F172A !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
        }
        .fitsense-stat-card span,
        .fitsense-stat-card b {
            color: #0F172A !important;
        }
        .fitsense-stat-card .stat-highlight {
            background: #FEF9C3 !important;
            color: #854D0E !important;
            border: 1px solid #FACC15 !important;
            padding: 2px 8px !important;
            border-radius: 6px !important;
            font-weight: 800 !important;
        }
        .user-profile-card {
            background: #FFFFFF !important;
            border: 1.5px solid #E2E8F0 !important;
            box-shadow: 0 4px 14px rgba(0,0,0,0.06) !important;
            color: #0F172A !important;
        }
        .user-profile-card div,
        .user-profile-card p,
        .user-profile-card span {
            color: #0F172A !important;
        }
        .user-profile-card .streak-pill {
            background: #FEF9C3 !important;
            border: 1px solid #FACC15 !important;
            color: #854D0E !important;
        }
        div[data-testid="stForm"],
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #FFFFFF !important;
            border: 1.5px solid #E2E8F0 !important;
            border-radius: 14px !important;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05) !important;
        }

        /* EXPANDER (Light Mode): Nền trắng, thanh tóm tắt màu kem nhạt sang trọng */
        div[data-testid="stExpander"],
        div[data-testid="stExpander"] details,
        div[data-testid="stExpander"] div[data-testid="stExpanderDetails"],
        [class*="e1u8u9eb1"],
        [class*="e1u8u9eb2"],
        [class*="e1u8u9eb11"] {
            background-color: #FFFFFF !important;
            border: 1.5px solid #E2E8F0 !important;
            border-radius: 12px !important;
            color: #0F172A !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.03) !important;
        }
        div[data-testid="stExpander"] summary,
        div[data-testid="stExpander"] details summary,
        div[data-testid="stExpander"] details[open] summary,
        [class*="e1u8u9eb10"] {
            background-color: #F8FAFC !important;
            color: #0F172A !important;
            border-radius: 10px !important;
            border-bottom: 1px solid #E2E8F0 !important;
            padding: 10px 16px !important;
        }
        div[data-testid="stExpander"] summary:hover,
        [class*="e1u8u9eb10"]:hover {
            background-color: #FEF9C3 !important;
            color: #854D0E !important;
        }
        div[data-testid="stExpander"] summary *,
        div[data-testid="stExpander"] details *,
        [class*="e1u8u9eb10"] * {
            color: #0F172A !important;
        }
        div[data-testid="stExpander"] summary:hover *,
        [class*="e1u8u9eb10"]:hover * {
            color: #854D0E !important;
        }
        div[data-testid="stExpander"] summary svg,
        [class*="e1u8u9eb10"] svg {
            fill: #EAB308 !important;
        }

        /* 7. INLINE CODE / KEYWORD BADGES (Light Theme): Khung vàng pastel -> Chữ nâu vàng đậm */
        code,
        span[data-testid="stMarkdownContainer"] code,
        div[data-testid="stMarkdownContainer"] code,
        [data-testid="stCaptionContainer"] code,
        div.stCaption code,
        .stMarkdown code {
            background-color: #FEF9C3 !important;
            color: #854D0E !important;
            border: 1px solid #FACC15 !important;
            border-radius: 6px !important;
            padding: 2px 8px !important;
            font-weight: 700 !important;
            font-size: 13px !important;
            display: inline-block !important;
            margin: 1px 3px !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
        }
        /* 8. PROGRESS BARS (Light Theme): Khung viền và tương phản rõ ràng giữa phần đạt và chưa đạt */
        div.stProgress,
        div[data-testid="stProgress"],
        div.stProgress [role="progressbar"] {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        /* KHUNG TOÀN CÂY (Phần chưa đạt được): Nền xám bạc #E2E8F0, Viền xám đậm #64748B bao trọn thanh */
        div[data-testid="stProgressBarTrack"],
        .stProgress div[data-testid="stProgressBarTrack"],
        .e1ed21rz0 {
            background-color: #E2E8F0 !important;
            border: 1.5px solid #64748B !important;
            border-radius: 9999px !important;
            overflow: hidden !important;
            box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.12) !important;
            box-sizing: border-box !important;
            height: 12px !important;
            min-height: 12px !important;
            max-height: 12px !important;
            position: relative !important;
        }

        /* PHẦN ĐÃ ĐẠT ĐƯỢC (% tiến độ): Màu vàng kim thể thao, không viền, khớp hoàn hảo trong lòng thanh */
        div[data-testid="stProgressBarTrack"] > div,
        .stProgress div[data-testid="stProgressBarTrack"] > div,
        .e1ed21rz1 {
            background: linear-gradient(90deg, #FACC15 0%, #EAB308 100%) !important;
            background-color: #EAB308 !important;
            height: 100% !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* 9. NUMBER INPUT BUTTONS (Light Theme) */
        div[data-testid="stNumberInput"] button {
            background-color: #F8FAFC !important;
            color: #0F172A !important;
            border: 1px solid #CBD5E1 !important;
        }
        div[data-testid="stNumberInput"] button:hover {
            background-color: #FEF9C3 !important;
            color: #854D0E !important;
        }
        div[data-testid="stNumberInput"] button svg {
            fill: #0F172A !important;
        }

        button[data-baseweb="tab"] p,
        button[data-baseweb="tab"] {
            color: #475569 !important;
            font-weight: 600 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] p,
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #EAB308 !important;
            font-weight: 800 !important;
        }
        div[data-baseweb="tab-highlight"] {
            background-color: #EAB308 !important;
        }
        """
    else:
        # CHẾ ĐỘ TỐI: ĐEN XANH (Obsidian Black & Neon Blue / Cyan)
        css = """
        :root {
            --bg-app: #070A11;
            --bg-sidebar: #0B111E;
            --bg-card: #111C2E;
            --border-card: #1E2E48;
            --text-main: #F8FAFC;
            --text-muted: #94A3B8;
            --accent-primary: #38BDF8;
            --accent-gradient: linear-gradient(135deg, #38BDF8 0%, #0284C7 100%);
            --accent-glow: rgba(56, 189, 248, 0.45);
            --active-text: #070A11;
            --card-hover: #19273E;
        }
        .stApp {
            background-color: #070A11 !important;
            color: #F8FAFC !important;
        }
        header[data-testid="stHeader"] {
            background-color: #070A11 !important;
            color: #F8FAFC !important;
        }
        section[data-testid="stSidebar"] {
            background-color: #0B111E !important;
            border-right: 1px solid #1E2E48 !important;
        }
        h1, h2, h3, h4, h5, h6, label, p, span {
            color: #F8FAFC !important;
        }

        /* 1. KHUNG NHẬP LIỆU: Nền tối -> Chữ sáng */
        div[data-baseweb="input"],
        div[data-baseweb="base-input"],
        div[data-baseweb="input"] input,
        textarea {
            background-color: #111C2E !important;
            color: #F8FAFC !important;
            border: 1.5px solid #1E2E48 !important;
            border-radius: 10px !important;
            -webkit-text-fill-color: #F8FAFC !important;
        }
        div[data-baseweb="input"]:focus-within {
            border-color: #38BDF8 !important;
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.35) !important;
        }

        /* 2. SELECT & MULTISELECT (Dark Theme): Khung tối (#111C2E, viền #1E2E48) -> Chữ sáng (#F8FAFC) */
        div[data-testid="stSelectbox"],
        div[data-testid="stSelectbox"] > div:first-child,
        div[data-testid="stMultiSelect"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }

        /* Khung nhập liệu chính của Selectbox và Multiselect: Nền #111C2E, Viền tối #1E2E48 (KHÔNG CÓ VIỀN TRẮNG) */
        div[data-testid="stSelectbox"] div.react-aria-Group,
        div[data-testid="stSelectbox"] div[role="group"],
        div[data-testid="stSelectbox"] [class*="e1oobldh0"],
        div[data-testid="stSelectbox"] [data-focus-within],
        div[data-testid="stSelectbox"] > div:nth-child(2) > div,
        div[data-testid="stSelectbox"] > div:nth-child(2) > div > div,
        div[data-testid="stMultiSelect"] div.ew56mvo0,
        div[data-testid="stMultiSelect"] [class*="ew56mvo0"],
        div[data-testid="stMultiSelect"] div[role="group"],
        div[data-testid="stMultiSelect"] > div:nth-child(2),
        div[data-baseweb="select"],
        div[data-baseweb="select"] > div {
            background-color: #111C2E !important;
            border: 1.5px solid #1E2E48 !important;
            border-radius: 10px !important;
            box-shadow: none !important;
            box-sizing: border-box !important;
            color: #F8FAFC !important;
        }

        /* Trạng thái focus-within: Viền sáng xanh nhẹ */
        div[data-testid="stSelectbox"] div.react-aria-Group:focus-within,
        div[data-testid="stSelectbox"] [class*="e1oobldh0"]:focus-within,
        div[data-testid="stMultiSelect"] div.ew56mvo0:focus-within,
        div[data-testid="stMultiSelect"] [class*="ew56mvo0"]:focus-within {
            border-color: #38BDF8 !important;
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.35) !important;
        }

        div[data-testid="stMultiSelect"] div[data-testid="stMultiSelectTagsContainer"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }

        /* Nút mũi tên và nút bấm bên trong khung: Nền trong suốt, không viền */
        div[data-testid="stSelectbox"] button,
        div[data-testid="stSelectbox"] button.react-aria-Button,
        div[data-testid="stSelectbox"] [class*="e1oobldh2"],
        div[data-testid="stSelectbox"] [class*="e1oobldh3"],
        div[data-testid="stMultiSelect"] [class*="ew56mvo7"],
        div[data-testid="stMultiSelect"] [class*="ew56mvo8"] {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            cursor: pointer !important;
        }

        /* Ô text input bên trong Selectbox & Multiselect */
        div[data-testid="stSelectbox"] input,
        div[data-testid="stSelectbox"] input.react-aria-Input,
        div[data-testid="stSelectbox"] [class*="e1oobldh1"],
        div[data-testid="stMultiSelect"] input,
        div[data-testid="stMultiSelect"] [class*="ew56mvo6"] {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #F8FAFC !important;
            -webkit-text-fill-color: #F8FAFC !important;
            font-size: 14px !important;
            font-weight: 500 !important;
        }
        div[data-testid="stSelectbox"] input::placeholder,
        div[data-testid="stMultiSelect"] input::placeholder {
            color: #94A3B8 !important;
            -webkit-text-fill-color: #94A3B8 !important;
        }

        /* Mũi tên dropdown icon: Màu xanh cyan nhẹ nhàng */
        div[data-testid="stSelectbox"] svg,
        div[data-testid="stMultiSelect"] svg {
            fill: #38BDF8 !important;
            color: #38BDF8 !important;
        }

        /* Multiselect Tags (Dark Theme): Toàn bộ tag đổi sang Xanh Cyan */
        div[data-testid="stMultiSelect"] .ew56mvo3,
        div[data-testid="stMultiSelect"] [data-testid="stMultiSelectTagsContainer"] > span,
        div[data-testid="stMultiSelect"] span:has(svg),
        div[data-baseweb="tag"] {
            background-color: rgba(56, 189, 248, 0.2) !important;
            border: 1px solid rgba(56, 189, 248, 0.5) !important;
            border-radius: 8px !important;
            color: #38BDF8 !important;
        }
        div[data-testid="stMultiSelect"] .ew56mvo3 span,
        div[data-testid="stMultiSelect"] [data-testid="stMultiSelectTagsContainer"] > span span,
        div[data-testid="stMultiSelect"] span:has(svg) span,
        div[data-baseweb="tag"] span {
            color: #38BDF8 !important;
            font-weight: 700 !important;
        }
        div[data-testid="stMultiSelect"] .ew56mvo3 svg,
        div[data-testid="stMultiSelect"] [data-testid="stMultiSelectTagsContainer"] > span svg,
        div[data-testid="stMultiSelect"] span:has(svg) svg,
        div[data-baseweb="tag"] svg {
            fill: #38BDF8 !important;
            color: #38BDF8 !important;
        }

        /* KHUNG POPUP SỔ XUỐNG (DROPDOWN MENU): Nền tối #111C2E, Viền tối #1E2E48 (KHÔNG VIỀN TRẮNG) */
        [class*="e1oobldh4"],
        .e1oobldh4,
        [class*="ew56mvo9"],
        .ew56mvo9,
        div[data-testid="stSelectboxVirtualDropdown"],
        div[data-testid="stMultiSelectDropdown"],
        div[data-baseweb="popover"],
        .react-aria-Popover,
        [data-overlay-container] .react-aria-Popover {
            background-color: #111C2E !important;
            border: 1.5px solid #1E2E48 !important;
            border-radius: 10px !important;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6) !important;
            overflow: hidden !important;
        }

        /* Danh sách UL bên trong Popover */
        [class*="e1oobldh5"],
        .e1oobldh5,
        [class*="ew56mvo10"],
        .ew56mvo10,
        .react-aria-ListBox,
        ul[role="listbox"] {
            background-color: #111C2E !important;
            border: none !important;
            padding: 4px !important;
        }

        /* TỪNG MỤC SỔ XUỐNG (DROPDOWN ITEMS): Chữ sáng trắng bạc #F8FAFC trên nền tối */
        [class*="e1oobldh7"],
        .e1oobldh7,
        [class*="e1oobldh8"],
        .e1oobldh8,
        [class*="ew56mvo12"],
        .ew56mvo12,
        [class*="ew56mvo13"],
        .ew56mvo13,
        li[role="option"],
        div[role="option"],
        .react-aria-ListBoxItem,
        [data-item-hl] {
            background-color: #111C2E !important;
            color: #F8FAFC !important;
            -webkit-text-fill-color: #F8FAFC !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            border-radius: 6px !important;
            margin: 1px 0 !important;
        }

        /* Bắt buộc toàn bộ text bên trong mục sổ xuống hiển thị màu sáng */
        [class*="e1oobldh7"] *,
        .e1oobldh7 *,
        [class*="e1oobldh8"] *,
        .e1oobldh8 *,
        [class*="ew56mvo12"] *,
        .ew56mvo12 *,
        [class*="ew56mvo13"] *,
        .ew56mvo13 *,
        li[role="option"] *,
        div[role="option"] *,
        .react-aria-ListBoxItem *,
        [data-item-hl] * {
            color: #F8FAFC !important;
            -webkit-text-fill-color: #F8FAFC !important;
        }

        /* KHI RÊ CHUỘT (HOVER) HOẶC ĐANG CHỌN (SELECTED): Đổi nền sang #16243A, Chữ Xanh Cyan #38BDF8 */
        [class*="e1oobldh7"]:hover,
        .e1oobldh7:hover,
        [class*="e1oobldh7"][data-hovered],
        [class*="e1oobldh7"][data-focused],
        [class*="e1oobldh7"][aria-selected="true"],
        [class*="ew56mvo12"]:hover,
        .ew56mvo12:hover,
        [class*="ew56mvo12"][data-hovered],
        [class*="ew56mvo12"][data-focused],
        [class*="ew56mvo12"][aria-selected="true"],
        li[role="option"]:hover,
        li[role="option"][aria-selected="true"],
        div[role="option"]:hover,
        div[role="option"][aria-selected="true"],
        .react-aria-ListBoxItem:hover,
        .react-aria-ListBoxItem[data-hovered],
        .react-aria-ListBoxItem[data-focused],
        .react-aria-ListBoxItem[aria-selected="true"],
        [data-item-hl][data-hovered],
        [data-item-hl][data-focused] {
            background-color: #16243A !important;
            color: #38BDF8 !important;
            -webkit-text-fill-color: #38BDF8 !important;
        }

        [class*="e1oobldh7"]:hover *,
        .e1oobldh7:hover *,
        [class*="e1oobldh7"][data-hovered] *,
        [class*="e1oobldh7"][data-focused] *,
        [class*="e1oobldh7"][aria-selected="true"] *,
        [class*="ew56mvo12"]:hover *,
        .ew56mvo12:hover *,
        [class*="ew56mvo12"][data-hovered] *,
        [class*="ew56mvo12"][data-focused] *,
        [class*="ew56mvo12"][aria-selected="true"] *,
        li[role="option"]:hover *,
        li[role="option"][aria-selected="true"] *,
        div[role="option"]:hover *,
        div[role="option"][aria-selected="true"] *,
        .react-aria-ListBoxItem:hover *,
        .react-aria-ListBoxItem[data-hovered] *,
        .react-aria-ListBoxItem[data-focused] *,
        .react-aria-ListBoxItem[aria-selected="true"] * {
            color: #38BDF8 !important;
            -webkit-text-fill-color: #38BDF8 !important;
        }

        /* 2b. SLIDERS (Dark Theme): Chuyển toàn bộ núm vặn, thanh tiến độ và số hiển thị sang Xanh Cyan */
        div[data-testid="stSlider"] [role="slider"],
        div[data-testid="stSlider"] .efbyxod3,
        div[data-testid="stSlider"] div[tabindex="0"] {
            background-color: #38BDF8 !important;
            border-color: #38BDF8 !important;
            box-shadow: 0 0 12px rgba(56, 189, 248, 0.6) !important;
        }
        div[data-testid="stSlider"] .efbyxod4,
        div[data-testid="stSlider"] div[data-testid="stSliderThumbValue"],
        div[data-testid="stSlider"] [data-testid="stSliderTickBar"] {
            color: #38BDF8 !important;
            font-weight: 700 !important;
        }
        div[data-testid="stSlider"] .efbyxod5 {
            filter: hue-rotate(150deg) saturate(1.3) !important;
        }

        /* 2c. CHECKBOX (Dark Theme): Đổi ô tick màu vàng sang Xanh Cyan */
        div[data-testid="stCheckbox"] [role="checkbox"][aria-checked="true"],
        div[data-testid="stCheckbox"] .e1ap2qgk5:has(input:checked),
        div[data-testid="stCheckbox"] input:checked + div,
        div[data-testid="stCheckbox"] input:checked ~ div {
            background-color: #38BDF8 !important;
            border-color: #38BDF8 !important;
        }
        div[data-testid="stCheckbox"] [role="checkbox"][aria-checked="true"] svg,
        div[data-testid="stCheckbox"] input:checked + div svg,
        div[data-testid="stCheckbox"] input:checked ~ div svg {
            color: #070A11 !important;
            stroke: #070A11 !important;
            fill: #070A11 !important;
        }

        /* 3. ALERTS & NOTIFICATIONS (Dark Theme): Khung tối -> Chữ sáng */
        div.stAlert,
        div[data-testid="stAlert"],
        div[data-testid="stAlertContainer"],
        div[data-testid="stAlert"] > div {
            border-radius: 10px !important;
        }
        /* Alert Info */
        div.stAlert:has([data-testid="stAlertContentInfo"]),
        div[data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]),
        div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]),
        div.stAlert:not(:has([data-testid="stAlertContentSuccess"])):not(:has([data-testid="stAlertContentWarning"])):not(:has([data-testid="stAlertContentError"])),
        div[data-testid="stAlert"]:not(:has([data-testid="stAlertContentSuccess"])):not(:has([data-testid="stAlertContentWarning"])):not(:has([data-testid="stAlertContentError"])),
        div[data-testid="stAlertContainer"]:not(:has([data-testid="stAlertContentSuccess"])):not(:has([data-testid="stAlertContentWarning"])):not(:has([data-testid="stAlertContentError"])) {
            background-color: #0E1E36 !important;
            border: 1.5px solid #0284C7 !important;
        }
        div.stAlert:has([data-testid="stAlertContentInfo"]) *,
        div[data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]) *,
        div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) *,
        div.stAlert:not(:has([data-testid="stAlertContentSuccess"])):not(:has([data-testid="stAlertContentWarning"])):not(:has([data-testid="stAlertContentError"])) *,
        div[data-testid="stAlert"]:not(:has([data-testid="stAlertContentSuccess"])):not(:has([data-testid="stAlertContentWarning"])):not(:has([data-testid="stAlertContentError"])) *,
        div[data-testid="stAlertContainer"]:not(:has([data-testid="stAlertContentSuccess"])):not(:has([data-testid="stAlertContentWarning"])):not(:has([data-testid="stAlertContentError"])) * {
            color: #F0F9FF !important;
        }
        div[data-testid="stAlert"] strong,
        div[data-testid="stAlert"] b {
            color: #38BDF8 !important;
        }
        /* Alert Success */
        div.stAlert:has([data-testid="stAlertContentSuccess"]),
        div[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]),
        div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) {
            background-color: #0B2518 !important;
            border: 1.5px solid #16A34A !important;
        }
        div.stAlert:has([data-testid="stAlertContentSuccess"]) *,
        div[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) *,
        div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) * {
            color: #F0FDF4 !important;
        }
        /* Alert Warning */
        div.stAlert:has([data-testid="stAlertContentWarning"]),
        div[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]),
        div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) {
            background-color: #2D2206 !important;
            border: 1.5px solid #CA8A04 !important;
        }
        div.stAlert:has([data-testid="stAlertContentWarning"]) *,
        div[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) *,
        div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) * {
            color: #FEFCE8 !important;
        }
        /* Alert Error */
        div.stAlert:has([data-testid="stAlertContentError"]),
        div[data-testid="stAlert"]:has([data-testid="stAlertContentError"]),
        div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {
            background-color: #2A0E11 !important;
            border: 1.5px solid #DC2626 !important;
        }
        div.stAlert:has([data-testid="stAlertContentError"]) *,
        div[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) *,
        div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) * {
            color: #FEF2F2 !important;
        }
        div[data-testid="stAlert"] code {
            background: rgba(255, 255, 255, 0.15) !important;
            color: #38BDF8 !important;
            border: 1px solid rgba(56, 189, 248, 0.3) !important;
            border-radius: 4px !important;
            padding: 2px 6px !important;
            font-weight: 700 !important;
        }

        /* 4. BUTTONS (Dark Theme) */
        /* Secondary Button: Nền tối -> Chữ sáng */
        button[data-testid="stBaseButton-secondary"],
        div[data-testid="stButton"] > button:not([data-testid="stBaseButton-primary"]) {
            background-color: #111C2E !important;
            color: #F8FAFC !important;
            border: 1.5px solid #1E2E48 !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
        }
        button[data-testid="stBaseButton-secondary"] *,
        div[data-testid="stButton"] > button:not([data-testid="stBaseButton-primary"]) * {
            color: #F8FAFC !important;
        }
        button[data-testid="stBaseButton-secondary"]:hover,
        div[data-testid="stButton"] > button:not([data-testid="stBaseButton-primary"]):hover {
            background-color: #16243A !important;
            border-color: #38BDF8 !important;
            color: #38BDF8 !important;
        }
        button[data-testid="stBaseButton-secondary"]:hover *,
        div[data-testid="stButton"] > button:not([data-testid="stBaseButton-primary"]):hover * {
            color: #38BDF8 !important;
        }

        /* 5. METRICS (Dark Theme) */
        div[data-testid="stMetricValue"] * {
            color: #F8FAFC !important;
        }
        div[data-testid="stMetricLabel"] * {
            color: #94A3B8 !important;
        }
        div[data-testid="stMetricDelta"] {
            background-color: rgba(34, 197, 94, 0.2) !important;
            border: 1px solid #16A34A !important;
            border-radius: 12px !important;
            padding: 2px 8px !important;
            display: inline-flex !important;
            align-items: center !important;
        }
        div[data-testid="stMetricDelta"] * {
            color: #4ADE80 !important;
            font-weight: 700 !important;
        }
        div[data-testid="stMetricDelta"] svg {
            fill: #4ADE80 !important;
        }

        /* 6. THẺ & KHUNG CONTAINER (Dark Theme) */
        .fitsense-stat-card {
            background: #111C2E !important;
            border: 1.5px solid #1E2E48 !important;
            border-left: 4px solid #38BDF8 !important;
            color: #F8FAFC !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
        }
        .fitsense-stat-card span,
        .fitsense-stat-card b {
            color: #F8FAFC !important;
        }
        .fitsense-stat-card .stat-highlight {
            background: rgba(56, 189, 248, 0.2) !important;
            color: #38BDF8 !important;
            border: 1px solid rgba(56, 189, 248, 0.5) !important;
            padding: 2px 8px !important;
            border-radius: 6px !important;
            font-weight: 800 !important;
        }
        .user-profile-card {
            background: linear-gradient(145deg, #111C2E 0%, #0D1624 100%) !important;
            border: 1.5px solid #1E2E48 !important;
            box-shadow: 0 8px 20px rgba(0,0,0,0.4) !important;
            color: #F8FAFC !important;
        }
        .user-profile-card div,
        .user-profile-card p,
        .user-profile-card span {
            color: #F8FAFC !important;
        }
        .user-profile-card .streak-pill {
            background: rgba(56, 189, 248, 0.15) !important;
            border: 1px solid rgba(56, 189, 248, 0.4) !important;
            color: #38BDF8 !important;
        }
        div[data-testid="stForm"],
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #111C2E !important;
            border: 1.5px solid #1E2E48 !important;
            border-radius: 14px !important;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4) !important;
        }

        /* EXPANDER (Dark Mode): Nền tối, chống triệt để thanh màu trắng */
        div[data-testid="stExpander"],
        div[data-testid="stExpander"] details,
        div[data-testid="stExpander"] div[data-testid="stExpanderDetails"],
        [class*="e1u8u9eb1"],
        [class*="e1u8u9eb2"],
        [class*="e1u8u9eb11"] {
            background-color: #111C2E !important;
            border: 1.5px solid #1E2E48 !important;
            border-radius: 12px !important;
            color: #F8FAFC !important;
            box-shadow: 0 4px 14px rgba(0,0,0,0.3) !important;
        }
        div[data-testid="stExpander"] summary,
        div[data-testid="stExpander"] details summary,
        div[data-testid="stExpander"] details[open] summary,
        [class*="e1u8u9eb10"] {
            background-color: #16243A !important;
            color: #F8FAFC !important;
            border-radius: 10px !important;
            border-bottom: 1px solid #1E2E48 !important;
            padding: 10px 16px !important;
        }
        div[data-testid="stExpander"] summary:hover,
        [class*="e1u8u9eb10"]:hover {
            background-color: #1E2E48 !important;
            color: #38BDF8 !important;
        }
        div[data-testid="stExpander"] summary *,
        div[data-testid="stExpander"] details *,
        [class*="e1u8u9eb10"] * {
            color: #F8FAFC !important;
        }
        div[data-testid="stExpander"] summary:hover *,
        [class*="e1u8u9eb10"]:hover * {
            color: #38BDF8 !important;
        }
        div[data-testid="stExpander"] summary svg,
        [class*="e1u8u9eb10"] svg {
            fill: #38BDF8 !important;
        }

        /* 7. INLINE CODE / KEYWORD BADGES (Dark Theme): Khung neon cyan -> Chữ xanh ngọc sáng */
        code,
        span[data-testid="stMarkdownContainer"] code,
        div[data-testid="stMarkdownContainer"] code,
        [data-testid="stCaptionContainer"] code,
        div.stCaption code,
        .stMarkdown code {
            background-color: rgba(56, 189, 248, 0.15) !important;
            color: #38BDF8 !important;
            border: 1px solid rgba(56, 189, 248, 0.45) !important;
            border-radius: 6px !important;
            padding: 2px 8px !important;
            font-weight: 700 !important;
            font-size: 13px !important;
            display: inline-block !important;
            margin: 1px 3px !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.2) !important;
        }
        /* 8. PROGRESS BARS (Dark Theme): Khung viền và tương phản rõ ràng giữa phần đạt và chưa đạt */
        div.stProgress,
        div[data-testid="stProgress"],
        div.stProgress [role="progressbar"] {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        /* KHUNG TOÀN CÂY (Phần chưa đạt được): Nền tối đậm #0F172A, Viền xanh xám #334155 bao trọn thanh */
        div[data-testid="stProgressBarTrack"],
        .stProgress div[data-testid="stProgressBarTrack"],
        .e1ed21rz0 {
            background-color: #0F172A !important;
            border: 1.5px solid #334155 !important;
            border-radius: 9999px !important;
            overflow: hidden !important;
            box-shadow: inset 0 1px 4px rgba(0, 0, 0, 0.6) !important;
            box-sizing: border-box !important;
            height: 12px !important;
            min-height: 12px !important;
            max-height: 12px !important;
            position: relative !important;
        }

        /* PHẦN ĐÃ ĐẠT ĐƯỢC (% tiến độ): Xanh Neon Cyan phát quang, không viền, khớp hoàn hảo trong lòng thanh */
        div[data-testid="stProgressBarTrack"] > div,
        .stProgress div[data-testid="stProgressBarTrack"] > div,
        .e1ed21rz1 {
            background: linear-gradient(90deg, #0284C7 0%, #38BDF8 100%) !important;
            background-color: #38BDF8 !important;
            height: 100% !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* 9. NUMBER INPUT BUTTONS (Dark Theme) */
        div[data-testid="stNumberInput"] button {
            background-color: #16243A !important;
            color: #F8FAFC !important;
            border: 1px solid #1E2E48 !important;
        }
        div[data-testid="stNumberInput"] button:hover {
            background-color: #1E2E48 !important;
            color: #38BDF8 !important;
        }
        div[data-testid="stNumberInput"] button svg {
            fill: #F8FAFC !important;
        }

        button[data-baseweb="tab"] p,
        button[data-baseweb="tab"] {
            color: #94A3B8 !important;
            font-weight: 600 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] p,
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #38BDF8 !important;
            font-weight: 800 !important;
        }
        div[data-baseweb="tab-highlight"] {
            background-color: #38BDF8 !important;
        }
        """

    common_css = """
    /* ================= 1. XÓA BỎ DẤU SAO CHÉP LIÊN KẾT (ANCHOR ICONS) SAU HEADER ================= */
    [data-testid="stHeaderActionElements"],
    a[aria-label="Link to heading"],
    a[aria-label="Direct link to heading"],
    div[data-testid="stHeadingWithActionElements"] a,
    div[data-testid="stHeadingWithActionElements"] button,
    .st-emotion-cache-12uj6qz,
    .e12uj6qz1,
    .e12uj6qz4 {
        display: none !important;
        opacity: 0 !important;
        width: 0 !important;
        height: 0 !important;
        pointer-events: none !important;
        visibility: hidden !important;
    }

    /* ================= 2. XÓA BỎ TRIỆT ĐỂ Ô TRÒN RADIO TRÊN TOÀN BỘ WEB ================= */
    div[data-testid="stRadio"] div[data-testid="stRadioOption"] > div > div:first-child,
    div[data-testid="stRadio"] label[data-baseweb="radio"] > div > div:first-child,
    div[data-testid="stRadio"] label[data-testid="stRadioOption"] > div > div:first-child,
    div[data-testid="stRadio"] .e1dm8mpf4,
    div[data-testid="stRadio"] svg,
    div[data-testid="stRadio"] input[type="radio"],
    div[data-testid="stRadio"] [role="radiogroup"] label div:first-child:not(:last-child) {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        opacity: 0 !important;
        visibility: hidden !important;
    }

    /* ================= 3. BIẾN RADIO THÀNH HÌNH CHỮ NHẬT BO TRÒN ================= */
    div[data-testid="stRadio"] div[data-testid="stRadioOption"],
    div[data-testid="stRadio"] label[data-baseweb="radio"],
    div[data-testid="stRadio"] label[data-testid="stRadioOption"] {
        background: var(--bg-card) !important;
        border: 1.5px solid var(--border-card) !important;
        border-radius: 12px !important;
        padding: 12px 18px !important;
        margin: 4px 0 !important;
        cursor: pointer !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        width: 100% !important;
        box-sizing: border-box !important;
        min-height: 48px !important;
    }

    /* ================= 4. CĂN CHỮ NẰM CHÍNH GIỮA SHAPE ================= */
    div[data-testid="stRadio"] div[data-testid="stRadioOption"] > div,
    div[data-testid="stRadio"] label[data-baseweb="radio"] > div,
    div[data-testid="stRadio"] label[data-testid="stRadioOption"] > div {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
        text-align: center !important;
        gap: 8px !important;
    }

    div[data-testid="stRadio"] div[data-testid="stRadioOption"] p,
    div[data-testid="stRadio"] label[data-baseweb="radio"] p,
    div[data-testid="stRadio"] label[data-testid="stRadioOption"] p {
        color: var(--text-main) !important;
        font-size: 14.5px !important;
        font-weight: 600 !important;
        margin: 0 !important;
        text-align: center !important;
        width: 100% !important;
        line-height: 1.4 !important;
    }

    /* Rê chuột vào Shape (Hover) */
    div[data-testid="stRadio"] div[data-testid="stRadioOption"]:hover,
    div[data-testid="stRadio"] label[data-baseweb="radio"]:hover,
    div[data-testid="stRadio"] label[data-testid="stRadioOption"]:hover {
        background: var(--card-hover) !important;
        border-color: var(--accent-primary) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 14px var(--accent-glow) !important;
    }

    /* ================= 5. TRẠNG THÁI ACTIVE: SHAPE ĐỔ MÀU GRADIENT, CHỮ ĐẬM CHÍNH GIỮA ================= */
    div[data-testid="stRadio"] div[data-testid="stRadioOption"][data-selected="true"],
    div[data-testid="stRadio"] div[data-testid="stRadioOption"]:has(input:checked),
    div[data-testid="stRadio"] label[data-baseweb="radio"][data-checked="true"],
    div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked),
    div[data-testid="stRadio"] label[data-testid="stRadioOption"][data-selected="true"],
    div[data-testid="stRadio"] label[data-testid="stRadioOption"]:has(input:checked) {
        background: var(--accent-gradient) !important;
        border-color: var(--accent-primary) !important;
        box-shadow: 0 4px 18px var(--accent-glow) !important;
        transform: translateY(-1px) !important;
    }

    div[data-testid="stRadio"] div[data-testid="stRadioOption"][data-selected="true"] p,
    div[data-testid="stRadio"] div[data-testid="stRadioOption"]:has(input:checked) p,
    div[data-testid="stRadio"] label[data-baseweb="radio"][data-checked="true"] p,
    div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p,
    div[data-testid="stRadio"] label[data-testid="stRadioOption"][data-selected="true"] p,
    div[data-testid="stRadio"] label[data-testid="stRadioOption"]:has(input:checked) p {
        color: var(--active-text) !important;
        font-weight: 800 !important;
        font-size: 15px !important;
        text-align: center !important;
    }

    /* ================= 6. BỐ CỤC NHÓM NẰM NGANG CĂN GIỮA & CÂN XỨNG 50/50 ================= */
    div[data-testid="stRadioGroup"][aria-orientation="horizontal"],
    div[data-testid="stRadio"] div[role="radiogroup"][aria-orientation="horizontal"] {
        display: flex !important;
        flex-direction: row !important;
        justify-content: center !important;
        align-items: stretch !important;
        gap: 12px !important;
        width: 100% !important;
        margin: 0 auto !important;
    }

    div[data-testid="stRadioGroup"][aria-orientation="horizontal"] > div,
    div[data-testid="stRadio"] div[role="radiogroup"][aria-orientation="horizontal"] > div {
        flex: 1 1 0px !important;
        width: 100% !important;
        min-width: 0 !important;
        display: flex !important;
        margin: 0 !important;
    }

    div[data-testid="stRadioGroup"][aria-orientation="horizontal"] > div > label,
    div[data-testid="stRadioGroup"][aria-orientation="horizontal"] > div > div,
    div[data-testid="stRadioGroup"][aria-orientation="horizontal"] div[data-testid="stRadioOption"],
    div[data-testid="stRadioGroup"][aria-orientation="horizontal"] label[data-baseweb="radio"] {
        width: 100% !important;
        height: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        margin: 0 !important;
    }

    /* ================= 7. CHỐNG XUỐNG DÒNG TUYỆT ĐỐI CHO BỘ CHỌN THEME SIDEBAR ================= */
    section[data-testid="stSidebar"] div[data-testid="stRadioGroup"][aria-orientation="horizontal"] {
        display: flex !important;
        flex-direction: row !important;
        gap: 6px !important;
        width: 100% !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadioGroup"][aria-orientation="horizontal"] > div {
        flex: 1 1 0px !important;
        width: 50% !important;
        min-width: 0 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadioGroup"][aria-orientation="horizontal"] div[data-testid="stRadioOption"],
    section[data-testid="stSidebar"] div[data-testid="stRadioGroup"][aria-orientation="horizontal"] label[data-baseweb="radio"],
    section[data-testid="stSidebar"] div[data-testid="stRadioGroup"][aria-orientation="horizontal"] label[data-testid="stRadioOption"] {
        min-height: 38px !important;
        height: 38px !important;
        padding: 4px 6px !important;
        white-space: nowrap !important;
        box-sizing: border-box !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadioGroup"][aria-orientation="horizontal"] p {
        white-space: nowrap !important;
        word-break: keep-all !important;
        overflow-wrap: normal !important;
        font-size: 13.5px !important;
        line-height: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
        text-align: center !important;
        width: 100% !important;
    }

    /* ================= 8. NÚT BẤM CHÍNH (PRIMARY BUTTON): Khung sáng gradient -> Chữ đen đậm ================= */
    button[data-testid="stBaseButton-primary"],
    div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"],
    div.stButton > button[kind="primary"],
    div.stButton > button[type="primary"] {
        background: var(--accent-gradient) !important;
        color: var(--active-text) !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px 20px !important;
        box-shadow: 0 4px 14px var(--accent-glow) !important;
        transition: all 0.2s ease !important;
    }
    button[data-testid="stBaseButton-primary"] *,
    div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] *,
    div.stButton > button[kind="primary"] *,
    div.stButton > button[type="primary"] * {
        color: var(--active-text) !important;
    }
    button[data-testid="stBaseButton-primary"]:hover,
    div.stButton > button[kind="primary"]:hover,
    div.stButton > button[type="primary"]:hover {
        box-shadow: 0 6px 20px var(--accent-glow) !important;
        transform: translateY(-2px) !important;
    }

    .user-profile-card .avatar-badge {
        display: inline-block;
        background: var(--accent-primary);
        color: var(--active-text);
        font-weight: bold;
        font-size: 16px;
        width: 36px;
        height: 36px;
        line-height: 36px;
        border-radius: 50%;
        text-align: center;
        margin-right: 8px;
    }

    /* Biểu đồ trong suốt */
    div[data-testid="stVegaLiteChart"] {
        background: transparent !important;
    }
    """

    st.markdown(f"<style>{css}\n{common_css}</style>", unsafe_allow_html=True)


def on_theme_change():
    """Callback đồng bộ ngay khi người dùng bấm đổi Theme."""
    chosen = st.session_state.get("theme_mode_selector", "Dark")
    st.session_state["app_theme"] = chosen.lower()


def main():
    """Hàm chạy ứng dụng chính và điều phối các màn hình."""
    st.set_page_config(
        page_title="FitSense — AI Fitness & Calisthenics",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    init_app_state()

    theme = st.session_state.get("app_theme", "dark")
    apply_custom_styles(theme=theme)

    is_logged_in = st.session_state.get("is_logged_in", False)
    user = st.session_state.get("user_profile")

    # ================= KHU VỰC THANH ĐIỀU HƯỚNG SIDEBAR =================
    with st.sidebar:
        # Header Logo FitSense
        logo_bg = "#38BDF8" if theme == "dark" else "#EAB308"
        logo_text_color = "#070A11" if theme == "dark" else "#0F172A"
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                <div style="background: {logo_bg}; color: {logo_text_color}; font-size: 22px; font-weight: 900; width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center;">⚡</div>
                <div>
                    <h2 style="margin: 0; font-size: 22px; font-weight: 800;">FitSense</h2>
                    <span style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: {logo_bg};">Smart AI Fitness</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1px solid var(--border-card);'>", unsafe_allow_html=True)

        # 1. BỘ CHỌN CHẾ ĐỘ GIAO DIỆN (THEME: DARK, LIGHT)
        text_title_color = "#0F172A" if theme == "light" else "#F8FAFC"
        st.markdown(
            f"""
            <div style="font-size: 13px; font-weight: 700; letter-spacing: 0.3px; margin-bottom: 6px; color: {text_title_color};">
                Theme:
            </div>
            """,
            unsafe_allow_html=True
        )
        theme_labels = ["Dark", "Light"]
        st.radio(
            "Theme Mode",
            options=theme_labels,
            key="theme_mode_selector",
            on_change=on_theme_change,
            horizontal=True,
            label_visibility="collapsed"
        )

        st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1px solid var(--border-card);'>", unsafe_allow_html=True)

        # 2. KHỐI THÔNG TIN NGƯỜI DÙNG HOẶC TRẠNG THÁI CHƯA ĐĂNG NHẬP
        if is_logged_in and user:
            # Khử nhiễm XSS (Sanitize input an toàn tuyệt đối)
            raw_name = str(user.get("name", "Vận động viên"))
            safe_name = html.escape(raw_name)
            first_char = raw_name[0].upper() if raw_name else "U"
            safe_first_letter = html.escape(first_char)
            safe_goal = html.escape(str(user.get("goal", "Calisthenics")))
            streak_days = int(st.session_state.get("streak_info", {}).get("current_streak", 0))

            st.markdown(
                f"""
                <div class="user-profile-card" style="padding: 14px; border-radius: 12px; margin-bottom: 12px;">
                    <div style="display: flex; align-items: center; margin-bottom: 6px;">
                        <span class="avatar-badge">{safe_first_letter}</span>
                        <div>
                            <div style="font-weight: 700; font-size: 15px;">{safe_name}</div>
                            <div style="font-size: 12px; opacity: 0.8;">{safe_goal}</div>
                        </div>
                    </div>
                    <div class="streak-pill" style="padding: 3px 10px; border-radius: 14px; font-size: 12px; font-weight: bold;">
                        🔥 Streak: {streak_days} ngày
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button("🚪 Đăng xuất", use_container_width=True):
                st.session_state["is_logged_in"] = False
                st.session_state["user_profile"] = None
                st.session_state["has_worked_out_today"] = False
                st.session_state["streak_info"] = {"current_streak": 0, "longest_streak": 0, "min_threshold_pct": 70}
                st.session_state["session_history"] = []
                st.rerun()

            st.markdown("<div style='font-size: 11px; font-weight: 700; text-transform: uppercase; margin: 12px 0 8px 0; letter-spacing: 0.5px;'>MENU TÍNH NĂNG</div>", unsafe_allow_html=True)

            nav_options = [
                "⚡ Phòng tập Trực tiếp (HUD)",
                "📋 Kế hoạch Tập luyện Tuần",
                "📚 Thư viện Động tác",
                "👤 Hồ sơ & Chỉ số Thể chất",
                "📝 Đánh giá Sau Buổi tập",
                "🔥 Bảng nhiệt Phục hồi Cơ bắp",
                "📈 Tiến độ & Kỷ lục Cá nhân",
            ]

            default_idx = 0
            if "nav_selection" in st.session_state and st.session_state["nav_selection"] in nav_options:
                default_idx = nav_options.index(st.session_state["nav_selection"])

            selected_nav = st.radio(
                "App Menu",
                options=nav_options,
                index=default_idx,
                label_visibility="collapsed",
                key="main_navigation_radio"
            )
            st.session_state["nav_selection"] = selected_nav

        else:
            # KHI CHƯA ĐĂNG NHẬP: CHỈ HIỂN THỊ THÔNG BÁO VÀ KHÔNG HIỂN THỊ BẤT KỲ TÍNH NĂNG NÀO CỦA WEB
            st.markdown(
                """
                <div class="user-profile-card" style="padding: 14px; border-radius: 12px; text-align: center;">
                    <div style="font-weight: 700; font-size: 15px; margin-bottom: 4px;">Cổng Đăng Nhập</div>
                    <div style="font-size: 12px; opacity: 0.8;">Vui lòng đăng nhập hoặc tạo tài khoản mới để mở khóa toàn bộ tính năng FitSense.</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # ================= KHU VỰC NỘI DUNG CHÍNH (MAIN AREA) =================
    if not is_logged_in:
        # Khi chưa đăng nhập: DUY NHẤT chỉ hiển thị form Đăng nhập / Đăng ký!
        render_auth_view()
    else:
        # Khi đã đăng nhập: Hiển thị màn hình theo lựa chọn của menu
        current_screen = st.session_state.get("nav_selection", "⚡ Phòng tập Trực tiếp (HUD)")

        if current_screen == "⚡ Phòng tập Trực tiếp (HUD)":
            render_session_view()
        elif current_screen == "📋 Kế hoạch Tập luyện Tuần":
            render_planner_view()
        elif current_screen == "📚 Thư viện Động tác":
            render_library_view()
        elif current_screen == "👤 Hồ sơ & Chỉ số Thể chất":
            render_profile_view()
        elif current_screen == "📝 Đánh giá Sau Buổi tập":
            render_evaluation_view()
        elif current_screen == "🔥 Bảng nhiệt Phục hồi Cơ bắp":
            render_heatmap_view()
        elif current_screen == "📈 Tiến độ & Kỷ lục Cá nhân":
            render_progress_view()

    # ================= CHÚ CHUỘT TÚI CAPYBARA ĐỒNG HÀNH Ở GÓC MÀN HÌNH =================
    render_capybara_companion(
        theme=theme,
        has_worked_out_today=st.session_state.get("has_worked_out_today", False),
        user_name=user.get("name", "bạn") if user else "bạn",
        is_logged_in=is_logged_in
    )


if __name__ == "__main__":
    main()
