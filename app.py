"""Entry point for the Ratatouille Streamlit starter.

Đồ án Tư duy Tính toán (Computational Thinking) - Nhóm 3: Ratatouille.
Xây dựng khung giao diện mô phỏng chính bằng thư viện Streamlit (SCRUM-11).
Phụ trách chính (Lead): Nguyễn Nhật Thùy Khanh (M02)
Phối hợp (Support): Trương Cẩm Tú Nga (M05)
"""

from datetime import date, timedelta
import streamlit as st

# Import các module chức năng từ thư mục src
from src.profile_inventory import render_profile_inventory
from src.menu_shopping import render_menu_shopping
from src.cooking import render_cooking
from src.diary_statistics import render_diary_statistics
from src.habits_exercise import render_habits_exercise


def init_app_state(force_reset: bool = False):
    """Khởi tạo trạng thái dữ liệu mô phỏng ban đầu cho toàn bộ ứng dụng."""
    if "initialized" in st.session_state and not force_reset:
        return

    st.session_state["initialized"] = True

    # 1. D1: Hồ sơ người dùng & Khẩu vị
    st.session_state["user_profile"] = {
        "name": "Nguyễn Nhật Thùy Khanh",
        "role": "Homemaker / Sinh viên",
        "default_servings": 2,
        "max_cook_time_minutes": 45,
        "meal_budget_limit": 80000,
        "weekly_budget": 700000,
        "dietary_preference": "Eat Clean",
        "allergies": ["Đậu phộng", "Hải sản có vỏ"],
        "other_diners": "Em trai (Không ăn cay)",
        "measurements": {
            "weight_kg": 54.0,
            "height_cm": 162.0,
            "waist_cm": 68.0,
            "last_updated": str(date.today()),
        },
    }

    # 2. D1: Thiết bị nhà bếp hiện có
    st.session_state["kitchen_utensils"] = [
        {"id": "U01", "name": "Bếp từ 2 vùng nấu", "type": "Bếp nấu", "capacity": "2000W / vùng", "status": "Sẵn sàng", "source": "Khai báo ban đầu"},
        {"id": "U02", "name": "Nồi chiên không dầu", "type": "Nấu / Chiên", "capacity": "5.5 lít, 1800W", "status": "Sẵn sàng", "source": "Khai báo ban đầu"},
        {"id": "U03", "name": "Nồi cơm điện tử", "type": "Nấu / Chiên", "capacity": "1.8 lít", "status": "Sẵn sàng", "source": "Khai báo ban đầu"},
        {"id": "U04", "name": "Lò vi sóng có nướng", "type": "Lò nướng / Vi sóng", "capacity": "20 lít, 800W", "status": "Sẵn sàng", "source": "Khai báo ban đầu"},
        {"id": "U05", "name": "Chảo chống dính sâu lòng", "type": "Nấu / Chiên", "capacity": "Đường kính 28cm", "status": "Sẵn sàng", "source": "Khai báo ban đầu"},
        {"id": "U06", "name": "Máy xay sinh tố đa năng", "type": "Máy xay / Chế biến", "capacity": "1.5 lít, 600W", "status": "Sẵn sàng", "source": "Khai báo ban đầu"},
    ]

    # 3. D2: Các lô nguyên liệu tồn kho (FEFO: một số lô có hạn dùng gần)
    today = date.today()
    st.session_state["ingredient_batches"] = [
        {
            "batch_id": "LOT-001",
            "name": "Thịt heo ba chỉ",
            "category": "Thịt & Thủy hải sản",
            "quantity": 500.0,
            "unit": "g",
            "location": "Ngăn mát tủ lạnh",
            "opening_date": str(today - timedelta(days=1)),
            "expiry_date": str(today + timedelta(days=2)),  # Sắp hết hạn trong 2 ngày
            "status": "Đã xác nhận",
        },
        {
            "batch_id": "LOT-002",
            "name": "Trứng cút tươi",
            "category": "Trứng & Sữa",
            "quantity": 20.0,
            "unit": "quả",
            "location": "Ngăn mát tủ lạnh",
            "opening_date": str(today - timedelta(days=2)),
            "expiry_date": str(today + timedelta(days=5)),
            "status": "Đã xác nhận",
        },
        {
            "batch_id": "LOT-003",
            "name": "Cà rốt Đà Lạt",
            "category": "Rau củ quả",
            "quantity": 300.0,
            "unit": "g",
            "location": "Ngăn mát tủ lạnh",
            "opening_date": str(today - timedelta(days=3)),
            "expiry_date": str(today + timedelta(days=1)),  # Sắp hết hạn trong 1 ngày!
            "status": "Đã xác nhận",
        },
        {
            "batch_id": "LOT-004",
            "name": "Bí đỏ hồ lô",
            "category": "Rau củ quả",
            "quantity": 400.0,
            "unit": "g",
            "location": "Ngăn mát tủ lạnh",
            "opening_date": str(today - timedelta(days=1)),
            "expiry_date": str(today + timedelta(days=6)),
            "status": "Đã xác nhận",
        },
        {
            "batch_id": "LOT-005",
            "name": "Gạo thơm ST25",
            "category": "Gia vị & Khô",
            "quantity": 3.5,
            "unit": "kg",
            "location": "Tủ gia vị & đồ khô",
            "opening_date": str(today - timedelta(days=10)),
            "expiry_date": str(today + timedelta(days=90)),
            "status": "Đã xác nhận",
        },
        {
            "batch_id": "LOT-006",
            "name": "Nước mắm cá cơm 40 độ đạm",
            "category": "Gia vị & Khô",
            "quantity": 450.0,
            "unit": "ml",
            "location": "Tủ gia vị & đồ khô",
            "opening_date": str(today - timedelta(days=20)),
            "expiry_date": str(today + timedelta(days=180)),
            "status": "Đã xác nhận",
        },
    ]

    # 4. D3: Đề xuất thực đơn mẫu
    st.session_state["menu_suggestions"] = [
        {
            "dish_id": "DISH-01",
            "name": "Thịt kho trứng cút nước dừa",
            "est_time": 35,
            "cost_estimate": 65000,
            "required_ingredients": ["Thịt heo ba chỉ (300g)", "Trứng cút (10 quả)", "Nước dừa tươi", "Gia vị"],
            "required_utensils": ["Bếp từ 2 vùng nấu", "Nồi chiên không dầu"],
            "missing_utensils": [],
            "alternative_solution": "Đủ thiết bị và nguyên liệu.",
        },
        {
            "dish_id": "DISH-02",
            "name": "Canh bí đỏ thịt bằm & Cà rốt xào",
            "est_time": 25,
            "cost_estimate": 45000,
            "required_ingredients": ["Bí đỏ (400g)", "Cà rốt (200g)", "Thịt nạc xay (150g)", "Hành ngò"],
            "required_utensils": ["Bếp từ 2 vùng nấu", "Chảo chống dính sâu lòng"],
            "missing_utensils": [],
            "alternative_solution": "Thiếu 150g thịt nạc xay -> Chuyển sang giỏ mua sắm dự kiến.",
        },
        {
            "dish_id": "DISH-03",
            "name": "Gà nướng thảo mộc mật ong",
            "est_time": 40,
            "cost_estimate": 85000,
            "required_ingredients": ["Đùi gà góc tư (500g)", "Mật ong", "Tiêu", "Tỏi", "Hương thảo"],
            "required_utensils": ["Lò nướng đối lưu chuyên dụng"],
            "missing_utensils": ["Lò nướng đối lưu chuyên dụng"],
            "alternative_solution": "Dùng Nồi chiên không dầu có sẵn (180°C trong 25 phút) hoặc áp chảo chảo sâu lòng.",
            "utensil_purchase_recommendation": "Mua thêm Lò nướng đối lưu 35L giúp bạn nấu thêm 14 món nướng và bánh ngọt yêu thích!",
        },
    ]

    st.session_state["selected_dish_id"] = "DISH-01"
    st.session_state["active_cooking_dish"] = st.session_state["menu_suggestions"][0]

    # 5. D4: Giỏ mua sắm mẫu
    st.session_state["shopping_basket_items"] = [
        {
            "item_name": "Thịt heo xay tươi (MEATDeli)",
            "required_qty": 150.0,
            "inventory_qty": 0.0,
            "shortage_qty": 150.0,
            "unit": "g",
            "package_spec": "300 g / khay",
            "packages_needed": 1,
            "unit_price": 38000,
            "total_price": 38000,
            "surplus_qty": 150.0,
        },
        {
            "item_name": "Nước dừa tươi đóng lon CocoXim",
            "required_qty": 330.0,
            "inventory_qty": 0.0,
            "shortage_qty": 330.0,
            "unit": "ml",
            "package_spec": "330 ml / lon",
            "packages_needed": 1,
            "unit_price": 16000,
            "total_price": 16000,
            "surplus_qty": 0.0,
        },
        {
            "item_name": "Hành lá & Ngò rí Đà Lạt",
            "required_qty": 50.0,
            "inventory_qty": 0.0,
            "shortage_qty": 50.0,
            "unit": "g",
            "package_spec": "100 g / bó",
            "packages_needed": 1,
            "unit_price": 8000,
            "total_price": 8000,
            "surplus_qty": 50.0,
        },
    ]

    # 6. D6: Lịch sử sự kiện (Event Storage deduplicated)
    st.session_state["event_log"] = [
        {
            "event_id": "EVT-BUY-202611020930",
            "timestamp": "2026-11-02 09:30",
            "type": "GROCERY_PURCHASE",
            "description": "Mua sắm Bách Hóa Xanh: Thịt ba chỉ, trứng cút, rau củ",
            "amount": 210000,
            "status": "CONFIRMED",
        },
        {
            "event_id": "EVT-COOK-202611021845",
            "timestamp": "2026-11-02 18:45",
            "type": "COOKING",
            "description": "Nấu bữa tối tại nhà: Canh chua cá điêu hồng",
            "amount": 0,
            "status": "CONFIRMED",
        },
        {
            "event_id": "EVT-OUT-202611031215",
            "timestamp": "2026-11-03 12:15",
            "type": "EAT_OUT",
            "description": "Ăn trưa ngoài: Bún bò Huế An Hòa",
            "amount": 55000,
            "status": "CONFIRMED",
        },
        {
            "event_id": "EVT-OUT-202611041230",
            "timestamp": "2026-11-04 12:30",
            "type": "EAT_OUT",
            "description": "Ăn trưa ngoài: Cơm tấm sườn trứng",
            "amount": 55000,
            "status": "CONFIRMED",
        },
    ]

    # 7. D7: Chuỗi thói quen độc lập
    st.session_state["habits_streaks"] = {
        "cook_at_home": {"current_streak": 4, "longest_streak": 12, "today_status": True},
        "healthy_eating": {"current_streak": 3, "longest_streak": 7, "today_status": True},
        "under_budget": {"current_streak": 6, "longest_streak": 14, "today_status": False},
        "daily_exercise": {"current_streak": 2, "longest_streak": 5, "today_status": False},
    }

    # 8. D8: Hồ sơ bài tập thể thao
    st.session_state["exercise_profile"] = {
        "style": "Calisthenics / Bodyweight tại nhà",
        "available_time": 25,
        "experience_level": "Mới bắt đầu",
        "limitations": "Khớp cổ tay yếu (hạn chế chống đẩy nặng)",
        "equipment": ["Thảm yoga"],
    }

    # 9. Bữa ăn trong ngày
    st.session_state["food_diary"] = [
        {"timestamp": "2026-11-04 07:30", "meal_type": "Bữa sáng", "dish_name": "Yến mạch sữa chua hoa quả", "source": "Tại nhà", "calories": 320, "cost": 15000},
        {"timestamp": "2026-11-04 12:30", "meal_type": "Bữa trưa", "dish_name": "Cơm tấm sườn nướng", "source": "Ăn ngoài", "calories": 620, "cost": 55000},
    ]


def main():
    """Hàm chính khởi chạy giao diện ứng dụng Streamlit."""
    st.set_page_config(
        page_title="Ratatouille — Trợ lý Nấu ăn & Thói quen",
        page_icon="🍳",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Khởi tạo state
    init_app_state()

    # Sidebar: Thông tin hệ thống và tổng quan nhanh
    with st.sidebar:
        st.markdown("# 🍳 Ratatouille")
        st.caption("Trợ lý ẩm thực, chi tiêu và thói quen cá nhân")
        st.markdown("---")

        # Thẻ ngữ cảnh Jira Task SCRUM-11
        st.markdown("### 📌 Ngữ cảnh Sprint & Task")
        with st.container(border=True):
            st.markdown("**Jira Task:** `SCRUM-11`")
            st.markdown("**Sprint:** Sprint 1 (Khung hệ thống)")
            st.markdown("**Lead:** M02 – Nguyễn Nhật Thùy Khanh *(Yu)*")
            st.markdown("**Support:** M05 – Trương Cẩm Tú Nga")
            st.markdown("**Trạng thái:** 🟡 `In Review` (Sẵn sàng nghiệm thu)")

        st.markdown("---")

        # Tình trạng mô phỏng
        st.success("🟢 **Chế độ:** Mô phỏng Localhost\n\n*Không cần AI API Key bên ngoài để chạy khung.*")

        st.markdown("### 📊 Chỉ số nhanh trong ngày")
        batches = st.session_state.get("ingredient_batches", [])
        events = st.session_state.get("event_log", [])
        habits = st.session_state.get("habits_streaks", {})

        col_sb1, col_sb2 = st.columns(2)
        with col_sb1:
            st.metric("Tồn kho", f"{len(batches)} lô", "1 sắp hết hạn", delta_color="inverse")
        with col_sb2:
            spent = sum(e["amount"] for e in events if e.get("type") in ["GROCERY_PURCHASE", "EAT_OUT"])
            st.metric("Đã chi tuần", f"{spent:,} đ")

        cook_streak = habits.get("cook_at_home", {}).get("current_streak", 0)
        st.info(f"🔥 Streak nấu tại nhà: **{cook_streak} ngày liên tiếp**")

        st.markdown("---")
        if st.button("🔄 Nạp lại dữ liệu mẫu (Reset Data)", use_container_width=True):
            init_app_state(force_reset=True)
            st.rerun()

        with st.expander("ℹ️ Hướng dẫn & Liên kết"):
            st.markdown("""
            - **GitHub Repo:** [nguyenphibaobinh11242927-art/CT---Ratatouille](https://github.com/nguyenphibaobinh11242927-art/CT---Ratatouille.git)
            - **Jira Project:** [Ratatouille Jira Board](https://ratatouille2026.atlassian.net)
            - **Môn học:** CSC10014 - Tư duy Tính toán (ĐH KHTN - ĐHQG-HCM)
            """)

    # Main Area Header
    st.title("🍳 Ratatouille — Trợ lý Thông minh")
    st.markdown(
        "Chào mừng bạn đến với **Ratatouille** — Nền tảng kết nối thông minh giữa quản lý nguyên liệu, "
        "đề xuất thực đơn tiết kiệm, hướng dẫn nấu ăn thực tế và duy trì chuỗi thói quen lành mạnh."
    )

    # 5 Tab giao diện chính theo đúng cấu trúc module kiến trúc dự án
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👤 Hồ sơ · Bếp · Kho nguyên liệu (D1, D2)",
        "📋 Thực đơn · Giỏ mua sắm (D3, D4)",
        "🍳 Hướng dẫn nấu ăn (D5)",
        "📊 Nhật ký · Thống kê (D6)",
        "🏃 Thói quen · Tập luyện (D7, D8)",
    ])

    with tab1:
        render_profile_inventory()

    with tab2:
        render_menu_shopping()

    with tab3:
        render_cooking()

    with tab4:
        render_diary_statistics()

    with tab5:
        render_habits_exercise()

    st.markdown("---")
    st.caption("Ratatouille | Đồ án môn Tư duy Tính toán (CSC10014) | Trường ĐH Khoa học Tự nhiên, ĐHQG-HCM.")


if __name__ == "__main__":
    main()
