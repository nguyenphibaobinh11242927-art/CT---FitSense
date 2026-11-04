"""Hướng dẫn nấu ăn theo thực đơn và ghi nhận ăn ngoài (D5).

Module thuộc đồ án Ratatouille:
- D5 Nấu tại nhà: Hướng dẫn theo phiên bản thực đơn đã xác nhận, đồng hồ nấu, trừ kho thực tế.
- D5 Ăn ngoài: Ghi nhận bữa ăn bên ngoài, ảnh/hóa đơn, ước tính dinh dưỡng [CK] và cập nhật chi tiêu độc lập.
"""

from datetime import datetime
import streamlit as st


def render_cooking():
    """Giao diện chính cho Nấu ăn & Bữa ăn ngoài."""
    st.header("🍳 Nấu ăn & Ghi nhận bữa ăn")
    st.caption("Hướng dẫn nấu từng bước (D5) và ghi nhận hoạt động ăn ngoài kèm hóa đơn chi tiêu.")

    sub_tab1, sub_tab2 = st.tabs([
        "👩‍🍳 Hướng dẫn nấu ăn tại nhà (D5)",
        "🍜 Ghi nhận ăn ngoài & Hóa đơn (D5)",
    ])

    with sub_tab1:
        _render_home_cooking()

    with sub_tab2:
        _render_eating_out()


def _render_home_cooking():
    """Hướng dẫn nấu ăn từng bước, trừ kho thực tế và cập nhật streak."""
    dish = st.session_state.get("active_cooking_dish", {})
    dish_name = dish.get("name", "Thịt kho trứng cút nước dừa")

    col_title, col_status = st.columns([3, 1])
    with col_title:
        st.subheader(f"🍲 Đang chuẩn bị nấu: {dish_name}")
        st.write(f"⏱️ Thời gian dự kiến: **{dish.get('est_time', 35)} phút** | 👥 Khẩu phần: **2 người**")
    with col_status:
        st.success("🟢 Thực đơn đã duyệt")

    st.write("---")

    col_steps, col_tools = st.columns([2, 1], gap="large")

    with col_steps:
        st.markdown("#### 📝 Các bước thực hiện")
        steps = [
            ("Bước 1: Sơ chế", "Rửa sạch thịt heo, cắt miếng vuông vừa ăn. Luộc trứng cút và bóc vỏ. Hành tỏi băm nhỏ."),
            ("Bước 2: Ướp gia vị", "Ướp thịt với 2 muỗng nước mắm, 1 muỗng đường, tiêu, hạt nêm và hành tỏi trong 15 phút."),
            ("Bước 3: Thắng nước màu & Xào săn", "Cho 1 thìa đường vào nồi, đun lửa vừa đến khi ngả màu cánh gián, cho thịt vào đảo săn."),
            ("Bước 4: Nấu nhỏ lửa", "Đổ nước dừa tươi ngập thịt, cho trứng cút vào. Đun sôi rồi hạ lửa nhỏ om trong 25 phút."),
            ("Bước 5: Hoàn thiện", "Nêm nếm lại cho vừa miệng, rắc thêm tiêu và hành lá. Tắt bếp và dọn ra đĩa."),
        ]

        completed_steps = []
        for i, (title, desc) in enumerate(steps):
            is_checked = st.checkbox(f"**{title}**: {desc}", key=f"step_cook_{i}")
            if is_checked:
                completed_steps.append(i)

        progress_val = len(completed_steps) / len(steps)
        st.progress(progress_val, text=f"Tiến độ hoàn thành: {int(progress_val * 100)}%")

        st.write("")
        if st.button("🎉 Xác nhận đã nấu xong & Cập nhật trừ kho", type="primary", use_container_width=True):
            # 1. Trừ kho nguyên liệu mô phỏng
            batches = st.session_state.get("ingredient_batches", [])
            for b in batches:
                if "thịt" in b["name"].lower() and b["quantity"] > 200:
                    b["quantity"] = max(0.0, b["quantity"] - 300)
                    break

            # 2. Ghi nhận sự kiện nấu ăn
            evt_id = f"EVT-COOK-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            st.session_state["event_log"].append({
                "event_id": evt_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "type": "COOKING",
                "description": f"Hoàn thành nấu món '{dish_name}' tại nhà",
                "amount": 0,
                "status": "CONFIRMED",
            })

            # 3. Tăng streak nấu ăn tại nhà
            habits = st.session_state.get("habits_streaks", {})
            if "cook_at_home" in habits:
                habits["cook_at_home"]["current_streak"] += 1
                habits["cook_at_home"]["today_status"] = True

            st.balloons()
            st.success(f"👏 Chúc mừng bạn đã hoàn thành món '{dish_name}'! Tồn kho đã được cập nhật trừ và streak nấu ăn đã tăng thêm 1 ngày.")
            st.rerun()

    with col_tools:
        st.markdown("#### ⏱️ Đồng hồ bấm giờ nấu ăn")
        st.info("Sử dụng đồng hồ để căn chuẩn thời gian ninh nấu từng bước.", icon="⏲️")

        timer_col1, timer_col2 = st.columns(2)
        with timer_col1:
            st.metric("Thời gian bấm giờ", "25:00", "Đang đếm ngược")
        with timer_col2:
            st.button("▶️ Bắt đầu", use_container_width=True)
            st.button("⏸️ Tạm dừng", use_container_width=True)

        st.divider()
        st.markdown("#### 🥫 Nguyên liệu xuất kho cho món")
        st.caption("Nguyên liệu ưu tiên lấy từ các lô có hạn dùng gần nhất (FEFO):")
        st.write("• 300g Thịt ba chỉ *(Lô LOT-01 - Ngăn mát)*")
        st.write("• 10 quả Trứng cút *(Lô LOT-04 - Ngăn mát)*")
        st.write("• 1 trái Nước dừa tươi *(Lô LOT-08)*")
        st.write("• Gia vị: Nước mắm, đường, tiêu, hành tỏi")


def _render_eating_out():
    """Ghi nhận hoạt động ăn ngoài, hóa đơn và ước tính dinh dưỡng."""
    st.subheader("🍜 Ghi nhận bữa ăn bên ngoài")
    st.caption("Ghi nhận chi tiêu thực tế và lưu vết nhật ký dinh dưỡng mà không làm ảnh hưởng đến tồn kho nguyên liệu.")

    with st.form("form_eating_out"):
        col_name, col_meal = st.columns(2)
        with col_name:
            out_dish = st.text_input("Tên quán ăn / Món ăn", placeholder="Ví dụ: Phở bò tái lăn Quán 10, Cơm tấm...")
        with col_meal:
            out_meal = st.selectbox("Bữa ăn", ["Bữa trưa", "Bữa tối", "Bữa sáng", "Ăn nhẹ / Cà phê"])

        col_cost, col_cal = st.columns(2)
        with col_cost:
            out_cost = st.number_input("Số tiền chi tiêu thực tế (VNĐ)", min_value=0, max_value=2000000, value=55000, step=5000)
        with col_cal:
            out_calories = st.number_input("Ước tính năng lượng [CK] (kcal)", min_value=0, max_value=2000, value=580, step=10)

        uploaded_bill = st.file_uploader("Đính kèm ảnh món ăn hoặc hóa đơn (nếu có)", type=["png", "jpg", "jpeg"])
        if uploaded_bill:
            st.image(uploaded_bill, caption="Ảnh hóa đơn đã tải lên (mô phỏng OCR)", width=250)

        st.info("ℹ️ **[CK]**: Dữ liệu dinh dưỡng được ước tính từ tên món ăn và cần người dùng kiểm tra xác nhận.", icon="🏷️")

        submitted = st.form_submit_button("💾 Lưu nhật ký ăn ngoài & Chi tiêu", use_container_width=True)
        if submitted:
            if out_dish.strip():
                # 1. Ghi nhận sự kiện ăn ngoài
                evt_id = f"EVT-OUT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                st.session_state["event_log"].append({
                    "event_id": evt_id,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "EAT_OUT",
                    "description": f"Ăn ngoài: {out_dish} ({out_meal})",
                    "amount": int(out_cost),
                    "status": "CONFIRMED",
                })

                # 2. Thêm vào nhật ký bữa ăn
                if "food_diary" not in st.session_state:
                    st.session_state["food_diary"] = []
                st.session_state["food_diary"].append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "meal_type": out_meal,
                    "dish_name": out_dish,
                    "source": "Ăn ngoài",
                    "calories": out_calories,
                    "cost": int(out_cost),
                })

                st.success(f"✅ Đã ghi nhận bữa ăn ngoài '{out_dish}' chi phí {out_cost:,} VNĐ vào nhật ký và thống kê chi tiêu!")
                st.rerun()
            else:
                st.error("Vui lòng nhập tên quán hoặc món ăn.")
