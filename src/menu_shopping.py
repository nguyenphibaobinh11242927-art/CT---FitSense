"""Thực đơn, đề xuất món, phân tích thiếu hụt và giỏ mua sắm dự kiến (D3, D4).

Module thuộc đồ án Ratatouille:
- D3: Đề xuất món ăn dựa trên kho, khẩu vị, thiết bị bếp và giải pháp thay thế thiết bị thiếu.
- D4: Tính toán định lượng thiếu hụt, quy cách đóng gói siêu thị, voucher và giỏ mua hàng tối ưu.
"""

from datetime import datetime
import streamlit as st
import pandas as pd


def render_menu_shopping():
    """Giao diện chính cho Thực đơn & Mua sắm."""
    st.header("📋 Thực đơn & Giỏ mua sắm")
    st.caption("Gợi ý thực đơn, xử lý thiếu thiết bị bếp (D3) và tính toán giỏ hàng mua sắm tối ưu (D4).")

    sub_tab1, sub_tab2 = st.tabs([
        "🍽️ Đề xuất thực đơn & Xử lý thiết bị (D3)",
        "🛒 Định lượng thiếu hụt & Giỏ mua sắm (D4)",
    ])

    with sub_tab1:
        _render_menu_suggestions()

    with sub_tab2:
        _render_shopping_basket()


def _render_menu_suggestions():
    """Đề xuất món ăn, xử lý thiếu hụt thiết bị và chọn thực đơn."""
    profile = st.session_state.get("user_profile", {})
    utensils = st.session_state.get("kitchen_utensils", [])
    utensil_names = [u["name"].lower() for u in utensils]

    st.subheader("1. Lọc điều kiện đề xuất thực đơn")
    col_meal, col_people, col_time, col_budget = st.columns(4)
    with col_meal:
        meal_type = st.selectbox("Bữa ăn", ["Bữa tối", "Bữa trưa", "Bữa sáng", "Ăn phụ"])
    with col_people:
        servings = st.number_input("Số khẩu phần", min_value=1, max_value=10, value=profile.get("default_servings", 2))
    with col_time:
        max_time = st.number_input("Thời gian nấu tối đa", min_value=15, max_value=120, value=profile.get("max_cook_time_minutes", 45), step=5)
    with col_budget:
        budget = st.number_input("Ngân sách bữa ăn (VNĐ)", min_value=20000, max_value=500000, value=profile.get("meal_budget_limit", 80000), step=10000)

    st.write("---")
    st.subheader("2. Danh sách món ăn gợi ý thông minh")

    suggestions = st.session_state.get("menu_suggestions", [])

    for idx, dish in enumerate(suggestions):
        with st.container(border=True):
            col_info, col_action = st.columns([3, 1])
            with col_info:
                st.markdown(f"### 🍲 {dish['name']}")
                st.write(f"⏱️ **Thời gian:** {dish['est_time']} phút | 👥 **Khẩu phần:** {servings} người | 💰 **Dự kiến:** {dish['cost_estimate']:,} VNĐ")
                st.write(f"🥕 **Nguyên liệu chính:** {', '.join(dish['required_ingredients'])}")

                # Kiểm tra thiết bị bếp
                req_u = dish.get("required_utensils", [])
                missing_u = [u for u in req_u if not any(u.lower() in existing for existing in utensil_names)]

                if missing_u:
                    st.warning(f"⚠️ **Thiếu thiết bị:** Cần `{', '.join(missing_u)}`.")
                    st.info(f"💡 **Giải pháp thay thế:** {dish.get('alternative_solution', 'Có thể áp chảo hoặc luộc thay thế.')}")
                    if dish.get("utensil_purchase_recommendation"):
                        st.caption(f"🛒 **Gợi ý đầu tư:** {dish.get('utensil_purchase_recommendation')}")
                else:
                    st.success("✅ **Thiết bị bếp:** Đầy đủ dụng cụ nấu trong bếp của bạn.")

            with col_action:
                st.write("")
                st.write("")
                is_selected = st.session_state.get("selected_dish_id") == dish["dish_id"]
                btn_label = "✅ Đã chọn món này" if is_selected else "➕ Chọn vào thực đơn"
                if st.button(btn_label, key=f"btn_select_dish_{idx}", use_container_width=True, disabled=is_selected):
                    st.session_state["selected_dish_id"] = dish["dish_id"]
                    st.session_state["active_cooking_dish"] = dish
                    st.success(f"Đã chọn món '{dish['name']}' vào thực đơn hôm nay!")
                    st.rerun()


def _render_shopping_basket():
    """Tính lượng thiếu hụt, giỏ mua sắm Bách Hóa Xanh/siêu thị và voucher."""
    st.subheader("1. Bảng đối chiếu định lượng & Thiếu hụt nguyên liệu")
    st.caption("Công thức: Shortage = max(0, Lượng cần nấu - Tồn kho khả dụng). Đã chuẩn hóa đơn vị.")

    dish = st.session_state.get("active_cooking_dish", {})
    dish_name = dish.get("name", "Thực đơn mẫu: Canh bí đỏ thịt bằm & Gà áp chảo")

    st.markdown(f"Món đang tính toán giỏ hàng: **{dish_name}**")

    basket_items = st.session_state.get("shopping_basket_items", [])

    if basket_items:
        df_basket = pd.DataFrame(basket_items)
        st.dataframe(
            df_basket[["item_name", "required_qty", "inventory_qty", "shortage_qty", "unit", "package_spec", "packages_needed", "unit_price", "total_price", "surplus_qty"]].rename(columns={
                "item_name": "Tên nguyên liệu",
                "required_qty": "Cần dùng",
                "inventory_qty": "Tồn kho",
                "shortage_qty": "Thiếu hụt",
                "unit": "Đơn vị",
                "package_spec": "Quy cách đóng gói",
                "packages_needed": "Số gói mua",
                "unit_price": "Đơn giá (VNĐ)",
                "total_price": "Thành tiền (VNĐ)",
                "surplus_qty": "Lượng dư dự kiến",
            }),
            use_container_width=True,
            hide_index=True,
        )

        subtotal = sum(item["total_price"] for item in basket_items)

        st.write("---")
        st.subheader("2. Tối ưu giỏ hàng & Mã giảm giá (Voucher)")

        col_voucher, col_summary = st.columns([1, 1], gap="large")

        with col_voucher:
            st.markdown("#### 🎟️ Áp dụng voucher / Phí giao hàng")
            voucher_options = {
                "Không dùng mã": 0,
                "FREESHIP - Miễn phí vận chuyển": 15000,
                "TIETKIEM10 - Giảm 10% tiền hàng": int(subtotal * 0.1),
                "BHXNEW - Giảm 20.000 VNĐ cho đơn từ 100k": 20000 if subtotal >= 100000 else 0,
            }
            selected_voucher_label = st.selectbox("Chọn mã giảm giá", options=list(voucher_options.keys()))
            discount_amount = voucher_options[selected_voucher_label]
            shipping_fee = 15000 if selected_voucher_label != "FREESHIP - Miễn phí vận chuyển" else 0

            st.write(f"🚚 Phí giao hàng dự kiến: **{shipping_fee:,} VNĐ**")
            st.write(f"🏷️ Giảm giá voucher: **-{discount_amount:,} VNĐ**")

        with col_summary:
            st.markdown("#### 💳 Tóm tắt chi phí giỏ hàng")
            final_total = max(0, subtotal + shipping_fee - discount_amount)
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("Tiền nguyên liệu", f"{subtotal:,} đ")
            col_m2.metric("Tổng thanh toán", f"{final_total:,} đ")

            surplus_summary = ", ".join([f"{item['surplus_qty']} {item['unit']} {item['item_name']}" for item in basket_items if item.get("surplus_qty", 0) > 0])
            if surplus_summary:
                st.info(f"📦 **Lượng dư sau nấu dự kiến:** {surplus_summary} (sẽ được tự động nhập lại kho sau khi nấu).")

            if st.button("🛒 Xác nhận mua hàng & Cập nhật kho", type="primary", use_container_width=True):
                # 1. Ghi nhận giao dịch vào event_log
                evt_id = f"EVT-BUY-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                st.session_state["event_log"].append({
                    "event_id": evt_id,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "type": "GROCERY_PURCHASE",
                    "description": f"Mua hàng siêu thị: {len(basket_items)} món (Mã: {selected_voucher_label})",
                    "amount": final_total,
                    "status": "CONFIRMED",
                })

                # 2. Nhập các mặt hàng vào kho nguyên liệu
                for item in basket_items:
                    total_bought = item["packages_needed"] * float(item["package_spec"].split()[0]) if " " in item["package_spec"] else item["shortage_qty"]
                    st.session_state["ingredient_batches"].append({
                        "batch_id": f"LOT-{datetime.now().strftime('%m%d%H%M%S')}-{item['item_name'][:3].upper()}",
                        "name": item["item_name"],
                        "category": "Nguyên liệu mới mua",
                        "quantity": total_bought,
                        "unit": item["unit"],
                        "location": "Ngăn mát tủ lạnh",
                        "opening_date": datetime.now().strftime("%Y-%m-%d"),
                        "expiry_date": "2026-11-15",
                        "status": "Đã xác nhận",
                    })

                st.success(f"🎉 Đã ghi nhận giao dịch chi tiêu ({final_total:,} VNĐ) và cập nhật hàng mới vào kho!")
                st.rerun()
    else:
        st.info("Hiện không có nguyên liệu nào bị thiếu hụt. Kho của bạn đã đủ để nấu món đã chọn!")
