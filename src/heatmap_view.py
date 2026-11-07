"""Module Bảng nhiệt Phục hồi Nhóm cơ (Muscle Heatmap View).

Trực quan hóa trạng thái mỏi và thời gian phục hồi sinh học của các nhóm cơ bắp sau khi rèn luyện.
"""

import streamlit as st


def render_heatmap_view():
    """Hiển thị bảng nhiệt cơ bắp và ma trận thời gian phục hồi theo mô hình khoa học thể thao."""
    st.header("🔥 Bảng nhiệt Phục hồi Nhóm cơ (Muscle Heatmap Matrix)")
    st.caption("Theo dõi mức độ sẵn sàng của từng nhóm cơ dựa trên thời gian phục hồi sinh học (24h - 48h - 72h).")

    recovery_data = st.session_state.get("muscle_recovery", {})

    st.subheader("1. Tổng quan Trạng thái Cơ bắp Toàn thân")

    # Hiển thị các khối metrics
    cols = st.columns(4)
    muscles = list(recovery_data.items())

    for idx, (muscle_name, data) in enumerate(muscles):
        col = cols[idx % 4]
        pct = data.get("recovery_pct", 100)
        hours_left = data.get("hours_left", 0)

        # Màu sắc theo mức hồi phục
        if pct >= 90:
            status_text = "Sẵn sàng tập"
            badge = "🟢"
        elif pct >= 60:
            status_text = "Đang hồi phục"
            badge = "🟡"
        else:
            status_text = "Mỏi cơ / Cần nghỉ"
            badge = "🔴"

        with col:
            with st.container(border=True):
                st.markdown(f"### {badge} {muscle_name}")
                st.progress(pct / 100.0)
                st.write(f"Mức hồi phục: **{pct}%**")
                st.caption(f"Tình trạng: **{status_text}**")
                if hours_left > 0:
                    st.caption(f"Cần thêm: `{hours_left}h` nghỉ")
                else:
                    st.caption("Đã hồi phục 100%")

    st.markdown("---")
    st.subheader("2. Khuyến nghị Phân bổ Nhóm cơ Hôm nay")

    ready_muscles = [m for m, d in recovery_data.items() if d.get("recovery_pct", 100) >= 80]
    fatigued_muscles = [m for m, d in recovery_data.items() if d.get("recovery_pct", 100) < 80]

    c_rec1, c_rec2 = st.columns(2)
    with c_rec1:
        st.success(f"✅ **Nhóm cơ đã phục hồi hoàn toàn — NÊN TẬP HÔM NAY:**\n\n" + ", ".join([f"`{m}`" for m in ready_muscles]))
    with c_rec2:
        st.warning(f"⚠️ **Nhóm cơ đang mỏi — CẦN NGHỈ NGƠI:**\n\n" + ", ".join([f"`{m}`" for m in fatigued_muscles]))
