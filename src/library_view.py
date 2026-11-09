"""Module Thư viện Bài tập Thể thao & Calisthenics (Library View).

Tra cứu, tìm kiếm và lọc bài tập chuẩn hóa theo nhóm cơ, dụng cụ, độ khó và hướng dẫn kỹ thuật.
"""

import streamlit as st


def render_library_view():
    """Hiển thị danh mục động tác, bộ lọc nâng cao và chi tiết hướng dẫn kỹ thuật."""
    st.header("📚 Thư viện Động tác Calisthenics & Thể thao")
    st.caption("Khám phá kỹ thuật chuẩn hóa, các lỗi sai phổ biến và bài tập thay thế tương đương.")

    library = st.session_state.get("exercise_library", [])

    c_s, c_m, c_e, c_d = st.columns([2, 1.2, 1.2, 1.2])
    with c_s:
        search_query = st.text_input("🔍 Tìm kiếm bài tập theo tên:", placeholder="Ví dụ: Squat, Push-up, Hít xà...")
    with c_m:
        muscle_filter = st.selectbox("Nhóm cơ chính:", options=["Tất cả nhóm cơ", "Ngực (Chest)", "Lưng & Xô (Back/Lats)", "Đùi & Mông (Quads/Glutes)", "Bụng & Core", "Vai (Shoulders)", "Tay sau (Triceps)"])
    with c_e:
        equip_filter = st.selectbox("Dụng cụ:", options=["Tất cả dụng cụ", "Bodyweight", "Xà đơn", "Dây kháng lực", "Thảm"])
    with c_d:
        diff_filter = st.selectbox("Độ khó:", options=["Tất cả cấp độ", "Beginner", "Intermediate", "Advanced"])

    # Lọc danh sách
    filtered = []
    for ex in library:
        if search_query and search_query.lower() not in ex["name"].lower():
            continue
        if muscle_filter != "Tất cả nhóm cơ" and ex["primary_muscle"] not in muscle_filter:
            continue
        if equip_filter != "Tất cả dụng cụ" and ex["equipment"] != equip_filter:
            continue
        if diff_filter != "Tất cả cấp độ" and ex["difficulty"] != diff_filter:
            continue
        filtered.append(ex)

    st.write(f"Tìm thấy **{len(filtered)}** bài tập phù hợp:")

    # Hiển thị dạng lưới thẻ 2 cột
    col1, col2 = st.columns(2)
    for idx, ex in enumerate(filtered):
        target_col = col1 if idx % 2 == 0 else col2
        with target_col:
            with st.container(border=True):
                st.subheader(f"{ex.get('icon', '🤸')} {ex.get('name')}")
                st.markdown(f"**Độ khó:** `{ex.get('difficulty')}` &nbsp;|&nbsp; **Dụng cụ:** `{ex.get('equipment')}`")

                st.markdown(f"**Cơ tác động chính:** `{ex.get('primary_muscle')}` &nbsp;|&nbsp; **Cơ phụ:** `{ex.get('secondary_muscle')}`")
                st.markdown(f"**Mô tả:** {ex.get('description')}")

                with st.expander("📌 Kỹ thuật chuẩn & Lỗi thường gặp:"):
                    st.write("**Các bước thực hiện:**")
                    for step in ex.get("steps", []):
                        st.write(f"- {step}")
                    st.error(f"⚠️ **Lỗi sai thường gặp:** {ex.get('common_mistake', 'Võng lưng, sai nhịp thở.')}")
                    st.success(f"💡 **Bài tập thay thế (Substitute):** {ex.get('substitute', 'Plank tĩnh')}")
