"""Module Theo dõi Tiến độ, Kỷ lục & Chuỗi ngày (Progress View).

Biểu đồ tăng tiến thể lực, quản lý kỷ lục cá nhân (PRs) và thuật toán tính Streak với điều kiện tối thiểu 70%.
"""

import altair as alt
import pandas as pd
import streamlit as st


def render_progress_view():
    """Hiển thị bảng điều khiển tiến độ, biểu đồ volume, kỷ lục cá nhân và streak duy trì tập luyện."""
    st.header("📈 Thống kê Tiến độ, Kỷ lục Cá nhân & Chuỗi ngày (Streak)")
    st.caption("Ghi nhận sự kiên trì và tiến bộ thể lực của bạn qua từng tuần.")

    streak_info = st.session_state.get("streak_info", {})
    records = st.session_state.get("personal_records", {})
    history = st.session_state.get("session_history", [])

    # Khối thẻ tổng quan đầu trang
    cur_streak = streak_info.get("current_streak", 0)
    longest_streak = streak_info.get("longest_streak", 0)
    delta_str = "+1 hôm nay" if cur_streak > 0 else None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(label="🔥 Chuỗi ngày liên tục (Streak)", value=f"{cur_streak} Ngày", delta=delta_str)
    with c2:
        st.metric(label="🏆 Chuỗi kỷ lục dài nhất", value=f"{longest_streak} Ngày")
    with c3:
        st.metric(label="✅ Tổng số buổi đã tập", value=f"{len(history)} Buổi")
    with c4:
        st.metric(label="⚡ Tỉ lệ hoàn thành TB", value="88.5%")

    st.info("💡 **Quy tắc tính Streak thể thao công bằng:** Để tránh áp lực và bảo vệ sức khỏe, bạn không bắt buộc phải hoàn thành 100% buổi tập. Chỉ cần hoàn thành từ **70% khối lượng bài tập trở lên**, hệ thống sẽ tự động ghi nhận duy trì Chuỗi ngày (Streak) thành công!")

    st.markdown("---")
    st.subheader("1. Kỷ lục Động tác Tốt nhất (Personal Records - PRs)")

    p_cols = st.columns(4)
    for idx, (ex_name, pr_val) in enumerate(records.items()):
        col = p_cols[idx % 4]
        with col:
            with st.container(border=True):
                st.markdown(f"**{ex_name}**")
                st.subheader(f"🥇 {pr_val}")
                st.caption("Kỷ lục cao nhất")

    st.markdown("---")
    st.subheader("2. Biểu đồ Khối lượng Rèn luyện theo Tuần")

    chart_data = pd.DataFrame({
        "Tuần": ["Tuần 1", "Tuần 2", "Tuần 3", "Tuần 4", "Tuần này"],
        "Tổng số Reps": [180, 220, 260, 290, 340],
        "Thời lượng (Phút)": [90, 110, 135, 140, 165]
    })

    theme = st.session_state.get("app_theme", "dark")
    bar_color = "#EAB308" if theme == "light" else "#38BDF8"
    text_color = "#0F172A" if theme == "light" else "#F8FAFC"
    grid_color = "#E2E8F0" if theme == "light" else "#1E2E48"

    chart = (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("Tuần:N", sort=None, axis=alt.Axis(labelColor=text_color, titleColor=text_color, grid=False, labelAngle=0)),
            y=alt.Y("Tổng số Reps:Q", axis=alt.Axis(labelColor=text_color, titleColor=text_color, gridColor=grid_color)),
            color=alt.value(bar_color),
            tooltip=["Tuần", "Tổng số Reps", "Thời lượng (Phút)"]
        )
        .properties(background="transparent", height=320)
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(chart, use_container_width=True)

    st.markdown("---")
    st.subheader("3. Nhật ký Lịch sử Tập luyện")
    if history:
        df_hist = pd.DataFrame(history)
        st.dataframe(df_hist, use_container_width=True)
    else:
        st.write("Chưa có lịch sử buổi tập nào được ghi nhận.")
