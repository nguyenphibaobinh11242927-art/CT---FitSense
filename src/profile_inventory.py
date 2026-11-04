"""Hồ sơ cá nhân, thiết bị bếp và quản lý nguyên liệu theo lô (D1, D2).

Module thuộc đồ án Ratatouille - Quản lý hồ sơ, tình trạng bếp, số đo cơ thể,
và theo dõi nguyên liệu tồn kho theo phương pháp FEFO (First Expired, First Out).
"""

from datetime import date, datetime
import streamlit as st
import pandas as pd


def render_profile_inventory():
    """Giao diện chính cho Hồ sơ, Bếp và Kho nguyên liệu."""
    st.header("👤 Hồ sơ, Thiết bị bếp & Kho nguyên liệu")
    st.caption("Quản lý thông tin cá nhân, hạn chế ăn uống, thiết bị bếp (D1) và các lô nguyên liệu (D2).")

    sub_tab1, sub_tab2 = st.tabs([
        "🏡 Hồ sơ cá nhân & Thiết bị bếp (D1)",
        "🥫 Kho nguyên liệu & Hạn dùng theo lô (D2)",
    ])

    with sub_tab1:
        _render_profile_and_kitchen()

    with sub_tab2:
        _render_inventory_batches()


def _render_profile_and_kitchen():
    """Quản lý thông tin cá nhân, dị ứng, người ăn cùng, thiết bị bếp và số đo."""
    profile = st.session_state.get("user_profile", {})

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.subheader("1. Thông tin cá nhân & Khẩu vị")
        with st.form("form_profile_settings"):
            user_name = st.text_input("Họ và tên người dùng", value=profile.get("name", "Nguyễn Nhật Thùy Khanh"))
            col_servings, col_time = st.columns(2)
            with col_servings:
                servings = st.number_input("Khẩu phần mặc định (người)", min_value=1, max_value=10, value=profile.get("default_servings", 2))
            with col_time:
                max_time = st.number_input("Thời gian nấu tối đa (phút)", min_value=10, max_value=180, value=profile.get("max_cook_time_minutes", 45))

            col_budget, col_diet = st.columns(2)
            with col_budget:
                meal_budget = st.number_input("Hạn mức ngân sách/bữa (VNĐ)", min_value=10000, max_value=1000000, step=10000, value=profile.get("meal_budget_limit", 80000))
            with col_diet:
                diet_options = ["Bình thường / Cân bằng", "Eat Clean", "Keto", "Thuần chay (Vegan)", "Ăn chay có trứng sữa", "Ít tinh bột (Low carb)"]
                current_diet = profile.get("dietary_preference", "Eat Clean")
                diet_idx = diet_options.index(current_diet) if current_diet in diet_options else 0
                diet_pref = st.selectbox("Chế độ ăn ưu tiên", options=diet_options, index=diet_idx)

            allergies_list = ["Đậu phộng", "Hải sản có vỏ", "Cá biển", "Sữa & Lactose", "Gluten / Bột mì", "Trứng", "Đậu nành", "Ớt / Cay"]
            current_allergies = [a for a in profile.get("allergies", []) if a in allergies_list]
            selected_allergies = st.multiselect("Dị ứng / Thành phần kiêng khem", options=allergies_list, default=current_allergies)

            other_diners = st.text_input("Thông tin người ăn cùng (nếu có)", value=profile.get("other_diners", "Em trai (Không ăn cay)"))

            submitted = st.form_submit_button("💾 Cập nhật hồ sơ khẩu vị", use_container_width=True)
            if submitted:
                st.session_state["user_profile"].update({
                    "name": user_name,
                    "default_servings": int(servings),
                    "max_cook_time_minutes": int(max_time),
                    "meal_budget_limit": int(meal_budget),
                    "dietary_preference": diet_pref,
                    "allergies": selected_allergies,
                    "other_diners": other_diners,
                })
                st.success("✅ Đã lưu cập nhật hồ sơ cá nhân và khẩu vị thành công!")

        st.divider()

        st.subheader("2. Số đo cơ thể gần nhất")
        st.info("ℹ️ **[CK]**: Số đo do người dùng nhập hoặc xác nhận từ hình ảnh thước đo/cân điện tử. Hệ thống không tự động đo cơ thể qua ảnh.", icon="📏")

        measurements = profile.get("measurements", {})
        col_m1, col_m2, col_m3 = st.columns(3)
        weight = measurements.get("weight_kg", 54.0)
        height = measurements.get("height_cm", 162.0)
        bmi = round(weight / ((height / 100) ** 2), 1) if height > 0 else 0

        col_m1.metric("Cân nặng", f"{weight} kg")
        col_m2.metric("Chiều cao", f"{height} cm")
        col_m3.metric("Chỉ số BMI", f"{bmi}", help="Phân loại: Bình thường (18.5 - 22.9)")

        with st.expander("📝 Cập nhật chỉ số thể chất mới"):
            with st.form("form_update_measurements"):
                new_weight = st.number_input("Cân nặng mới (kg)", min_value=30.0, max_value=200.0, value=float(weight), step=0.1)
                new_height = st.number_input("Chiều cao (cm)", min_value=100.0, max_value=230.0, value=float(height), step=0.5)
                new_waist = st.number_input("Vòng eo (cm)", min_value=40.0, max_value=150.0, value=float(measurements.get("waist_cm", 68.0)), step=0.5)
                measure_date = st.date_input("Ngày đo", value=date.today())

                if st.form_submit_button("Ghi nhận số đo"):
                    st.session_state["user_profile"]["measurements"] = {
                        "weight_kg": new_weight,
                        "height_cm": new_height,
                        "waist_cm": new_waist,
                        "last_updated": str(measure_date),
                    }
                    # Log event
                    if "event_log" in st.session_state:
                        st.session_state["event_log"].append({
                            "event_id": f"EVT-MEAS-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "type": "BODY_MEASUREMENT",
                            "description": f"Cập nhật số đo: Cân nặng {new_weight}kg, Eo {new_waist}cm",
                            "amount": 0,
                            "status": "CONFIRMED",
                        })
                    st.success("✅ Đã cập nhật chỉ số thể chất thành công!")
                    st.rerun()

    with col_right:
        st.subheader("3. Thiết bị nhà bếp hiện có")
        st.caption("Danh sách thiết bị dùng để đối chiếu khi đề xuất món ăn và cách nấu thay thế.")

        utensils = st.session_state.get("kitchen_utensils", [])
        if utensils:
            df_utensils = pd.DataFrame(utensils)
            st.dataframe(
                df_utensils[["name", "type", "capacity", "status", "source"]].rename(columns={
                    "name": "Tên thiết bị",
                    "type": "Loại",
                    "capacity": "Thông số / Công suất",
                    "status": "Trạng thái",
                    "source": "Nguồn xác nhận",
                }),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning("Chưa có thiết bị nào được lưu.")

        with st.expander("➕ Thêm thiết bị mới vào bếp"):
            with st.form("form_add_utensil"):
                u_name = st.text_input("Tên thiết bị", placeholder="Ví dụ: Nồi chiên không dầu Philips")
                col_utype, col_ucap = st.columns(2)
                with col_utype:
                    u_type = st.selectbox("Phân loại", ["Nấu / Chiên", "Lò nướng / Vi sóng", "Máy xay / Chế biến", "Bếp nấu", "Khác"])
                with col_ucap:
                    u_cap = st.text_input("Công suất / Dung tích", placeholder="Ví dụ: 5.5 lít, 1800W")
                u_status = st.selectbox("Tình trạng hoạt động", ["Sẵn sàng", "Cần bảo trì / Hỏng nhẹ", "Đang sửa chữa"])

                if st.form_submit_button("Thêm thiết bị"):
                    if u_name.strip():
                        new_u = {
                            "id": f"U{len(utensils) + 1:02d}",
                            "name": u_name.strip(),
                            "type": u_type,
                            "capacity": u_cap.strip() if u_cap else "Tiêu chuẩn",
                            "status": u_status,
                            "source": "Người dùng thêm thủ công",
                        }
                        st.session_state["kitchen_utensils"].append(new_u)
                        st.success(f"✅ Đã thêm thiết bị '{u_name}' vào bếp!")
                        st.rerun()
                    else:
                        st.error("Vui lòng nhập tên thiết bị.")


def _render_inventory_batches():
    """Quản lý các lô nguyên liệu, cảnh báo hạn dùng theo FEFO."""
    batches = st.session_state.get("ingredient_batches", [])

    # Cảnh báo hạn dùng FEFO
    today = date.today()
    expiring_soon = []
    for b in batches:
        exp_str = b.get("expiry_date")
        if exp_str and exp_str != "Chưa rõ":
            try:
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
                days_left = (exp_date - today).days
                if days_left <= 3:
                    expiring_soon.append((b, days_left))
            except ValueError:
                pass

    if expiring_soon:
        st.warning(f"⚠️ **CẢNH BÁO HẠN DÙNG (FEFO):** Có {len(expiring_soon)} lô nguyên liệu sắp hoặc đã hết hạn trong 3 ngày tới! Cần ưu tiên dùng trước.")
        cols = st.columns(min(len(expiring_soon), 3))
        for idx, (b, days) in enumerate(expiring_soon[:3]):
            col = cols[idx % len(cols)]
            with col:
                status_txt = "Đã hết hạn hôm nay!" if days == 0 else (f"Quá hạn {-days} ngày!" if days < 0 else f"Còn {days} ngày")
                st.error(f"**{b['name']}** ({b['quantity']} {b['unit']})\n\n📅 HSD: {b['expiry_date']} ({status_txt})")

    st.write("---")

    # Bộ lọc kho
    col_filter1, col_filter2, col_count = st.columns([2, 2, 2])
    with col_filter1:
        loc_filter = st.selectbox("📍 Vị trí lưu trữ:", ["Tất cả vị trí", "Ngăn mát tủ lạnh", "Ngăn đông đá", "Tủ gia vị & đồ khô"])
    with col_filter2:
        cat_filter = st.selectbox("🏷️ Phân loại:", ["Tất cả danh mục", "Thịt & Thủy hải sản", "Rau củ quả", "Trứng & Sữa", "Gia vị & Khô"])
    with col_count:
        st.metric("Tổng số lô lưu kho", len(batches))

    # Lọc danh sách
    filtered_batches = batches
    if loc_filter != "Tất cả vị trí":
        filtered_batches = [b for b in filtered_batches if b.get("location") == loc_filter]
    if cat_filter != "Tất cả danh mục":
        filtered_batches = [b for b in filtered_batches if b.get("category") == cat_filter]

    if filtered_batches:
        df_batches = pd.DataFrame(filtered_batches)
        st.dataframe(
            df_batches[["batch_id", "name", "category", "quantity", "unit", "location", "opening_date", "expiry_date", "status"]].rename(columns={
                "batch_id": "Mã lô",
                "name": "Tên nguyên liệu",
                "category": "Phân loại",
                "quantity": "Số lượng",
                "unit": "Đơn vị",
                "location": "Vị trí",
                "opening_date": "Ngày mở",
                "expiry_date": "Hạn dùng",
                "status": "Trạng thái",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Không có lô nguyên liệu nào khớp với bộ lọc.")

    # Form thêm nguyên liệu mới
    st.subheader("➕ Thêm lô nguyên liệu vào kho")
    with st.form("form_add_batch"):
        col_name, col_cat = st.columns(2)
        with col_name:
            b_name = st.text_input("Tên nguyên liệu", placeholder="Ví dụ: Thịt heo ba chỉ, Cà rốt...")
        with col_cat:
            b_cat = st.selectbox("Phân loại", ["Thịt & Thủy hải sản", "Rau củ quả", "Trứng & Sữa", "Gia vị & Khô"])

        col_q, col_u, col_loc = st.columns(3)
        with col_q:
            b_qty = st.number_input("Số lượng còn lại", min_value=0.1, value=500.0, step=10.0)
        with col_u:
            b_unit = st.selectbox("Đơn vị", ["g", "kg", "ml", "lít", "quả", "củ", "gói", "hộp"])
        with col_loc:
            b_loc = st.selectbox("Vị trí bảo quản", ["Ngăn mát tủ lạnh", "Ngăn đông đá", "Tủ gia vị & đồ khô"])

        col_open, col_exp = st.columns(2)
        with col_open:
            b_open = st.date_input("Ngày mở gói / bắt đầu bảo quản", value=date.today())
        with col_exp:
            b_exp = st.date_input("Hạn sử dụng", value=date.today())

        if st.form_submit_button("📥 Lưu lô nguyên liệu vào kho", use_container_width=True):
            if b_name.strip():
                new_batch = {
                    "batch_id": f"LOT-{datetime.now().strftime('%m%d%H%M%S')}",
                    "name": b_name.strip(),
                    "category": b_cat,
                    "quantity": float(b_qty),
                    "unit": b_unit,
                    "location": b_loc,
                    "opening_date": str(b_open),
                    "expiry_date": str(b_exp),
                    "status": "Đã xác nhận",
                }
                st.session_state["ingredient_batches"].append(new_batch)
                st.success(f"✅ Đã thêm lô '{b_name}' ({b_qty} {b_unit}) vào kho thành công!")
                st.rerun()
            else:
                st.error("Vui lòng nhập tên nguyên liệu.")
