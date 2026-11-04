"""Nhật ký hoạt động, lưu trữ sự kiện và thống kê chi tiêu, dinh dưỡng (D6).

Module thuộc đồ án Ratatouille:
- D6: Hệ thống sự kiện có định danh duy nhất (Event ID) chống trùng lặp.
- Thống kê chi tiêu theo kỳ (mua nguyên liệu, ăn ngoài, dụng cụ tách biệt).
- Nhật ký bữa ăn, dinh dưỡng ước tính [CK] và lịch sử số đo cơ thể.
"""

import streamlit as st
import pandas as pd


def render_diary_statistics():
    """Giao diện chính cho Nhật ký sự kiện & Thống kê."""
    st.header("📊 Nhật ký & Thống kê")
    st.caption("Quản lý lưu trữ sự kiện hệ thống (D6), phân tích chi tiêu theo ngân sách và theo dõi dinh dưỡng.")

    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        "💰 Thống kê chi tiêu & Ngân sách",
        "🗂️ Nhật ký sự kiện hệ thống (D6)",
        "🥗 Nhật ký dinh dưỡng & Thể chất",
    ])

    with sub_tab1:
        _render_spending_statistics()

    with sub_tab2:
        _render_event_storage()

    with sub_tab3:
        _render_nutrition_and_body()


def _render_spending_statistics():
    """Bảng điều khiển chi tiêu tài chính và ngân sách."""
    profile = st.session_state.get("user_profile", {})
    weekly_budget = profile.get("weekly_budget", 700000)

    events = st.session_state.get("event_log", [])
    grocery_spent = sum(e["amount"] for e in events if e.get("type") == "GROCERY_PURCHASE")
    eat_out_spent = sum(e["amount"] for e in events if e.get("type") == "EAT_OUT")
    total_spent = grocery_spent + eat_out_spent

    remaining_budget = weekly_budget - total_spent
    pct_used = min(100.0, (total_spent / weekly_budget * 100)) if weekly_budget > 0 else 0

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Tổng chi trong tuần", f"{total_spent:,} đ", f"{pct_used:.1f}% ngân sách", delta_color="inverse")
    col_m2.metric("Mua nguyên liệu", f"{grocery_spent:,} đ")
    col_m3.metric("Chi ăn ngoài", f"{eat_out_spent:,} đ")
    col_m4.metric("Ngân sách còn lại", f"{remaining_budget:,} đ", "Còn trong hạn mức" if remaining_budget >= 0 else "Vượt ngân sách!")

    st.write("---")
    st.markdown("#### 📈 Tiến độ sử dụng ngân sách tuần")
    progress_val = min(1.0, total_spent / weekly_budget) if weekly_budget > 0 else 0
    st.progress(progress_val, text=f"Đã chi tiêu {total_spent:,} / {weekly_budget:,} VNĐ ({pct_used:.1f}%)")

    st.write("---")
    st.markdown("#### 💳 Phân bổ chi tiêu chi tiết")
    breakdown_data = [
        {"Danh mục": "🛒 Mua sắm nguyên liệu nấu tại nhà", "Số tiền (VNĐ)": grocery_spent, "Tỷ trọng": f"{(grocery_spent / total_spent * 100):.1f}%" if total_spent > 0 else "0%"},
        {"Danh mục": "🍜 Bữa ăn ngoài tiệm", "Số tiền (VNĐ)": eat_out_spent, "Tỷ trọng": f"{(eat_out_spent / total_spent * 100):.1f}%" if total_spent > 0 else "0%"},
        {"Danh mục": "🍳 Thiết bị & Dụng cụ bếp", "Số tiền (VNĐ)": 0, "Tỷ trọng": "0% (Khoản đầu tư riêng)"},
    ]
    st.dataframe(pd.DataFrame(breakdown_data), use_container_width=True, hide_index=True)


def _render_event_storage():
    """Lưu trữ sự kiện có ID duy nhất chống trùng lặp (P6/P7)."""
    st.subheader("🗂️ Danh sách sự kiện đã lưu vết (Event Log)")
    st.caption("Mỗi hoạt động (mua hàng, nấu ăn, ăn ngoài, số đo) được cấp một Event ID riêng để tránh ghi trùng lặp.")

    events = st.session_state.get("event_log", [])

    col_filter, col_total = st.columns([3, 1])
    with col_filter:
        evt_types = ["Tất cả loại", "GROCERY_PURCHASE", "COOKING", "EAT_OUT", "BODY_MEASUREMENT"]
        selected_type = st.selectbox("Lọc theo loại sự kiện:", evt_types)
    with col_total:
        st.metric("Tổng số sự kiện", len(events))

    filtered_events = events
    if selected_type != "Tất cả loại":
        filtered_events = [e for e in filtered_events if e.get("type") == selected_type]

    if filtered_events:
        df_events = pd.DataFrame(filtered_events)
        st.dataframe(
            df_events[["event_id", "timestamp", "type", "description", "amount", "status"]].rename(columns={
                "event_id": "Mã sự kiện",
                "timestamp": "Thời gian",
                "type": "Loại sự kiện",
                "description": "Mô tả chi tiết",
                "amount": "Số tiền (VNĐ)",
                "status": "Trạng thái",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Chưa có sự kiện nào khớp với bộ lọc.")


def _render_nutrition_and_body():
    """Nhật ký bữa ăn và theo dõi số đo cơ thể."""
    st.subheader("🥗 Nhật ký bữa ăn trong ngày")
    st.caption("Dữ liệu tổng hợp từ các bữa nấu tại nhà và ăn ngoài. Ước tính calo mang nhãn [CK].")

    food_diary = st.session_state.get("food_diary", [])
    if food_diary:
        df_diary = pd.DataFrame(food_diary)
        st.dataframe(
            df_diary[["timestamp", "meal_type", "dish_name", "source", "calories", "cost"]].rename(columns={
                "timestamp": "Thời gian",
                "meal_type": "Bữa ăn",
                "dish_name": "Tên món",
                "source": "Nguồn",
                "calories": "Năng lượng [CK] (kcal)",
                "cost": "Chi phí (VNĐ)",
            }),
            use_container_width=True,
            hide_index=True,
        )
        total_cal = sum(item.get("calories", 0) for item in food_diary)
        st.info(f"🔥 Tổng năng lượng nạp vào ước tính hôm nay: **{total_cal:,} kcal** [CK]")
    else:
        st.info("Chưa có bữa ăn nào được ghi nhận hôm nay.")

    st.write("---")
    st.subheader("📏 Lịch sử chỉ số thể chất")
    profile = st.session_state.get("user_profile", {})
    measurements = profile.get("measurements", {})

    history_data = [
        {"Ngày đo": "2026-10-25", "Cân nặng (kg)": 54.5, "Chiều cao (cm)": 162.0, "Vòng eo (cm)": 69.0, "BMI": 20.8},
        {"Ngày đo": "2026-10-30", "Cân nặng (kg)": 54.2, "Chiều cao (cm)": 162.0, "Vòng eo (cm)": 68.5, "BMI": 20.7},
        {"Ngày đo": measurements.get("last_updated", "2026-11-04"), "Cân nặng (kg)": measurements.get("weight_kg", 54.0), "Chiều cao (cm)": measurements.get("height_cm", 162.0), "Vòng eo (cm)": measurements.get("waist_cm", 68.0), "BMI": 20.6},
    ]
    st.dataframe(pd.DataFrame(history_data), use_container_width=True, hide_index=True)
