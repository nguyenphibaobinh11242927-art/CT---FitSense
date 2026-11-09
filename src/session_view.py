"""Module Phòng tập Rảnh tay & Điều hành Phiên tập Thời gian thực (Session HUD View).

Quản lý chế độ Camera AI Vision (MediaPipe, đếm reps FSM, cử chỉ kép) và Chế độ Tự do Không Camera.
"""

import base64
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components


ROOT = Path(__file__).resolve().parents[1]
webcam = components.declare_component("fitsense_webcam", path=str(ROOT / "assets" / "webcam"))


@st.cache_data
def webcam_model():
    model = ROOT / "models" / "pose_landmarker_lite.task"
    return base64.b64encode(model.read_bytes()).decode("ascii")


def render_session_view():
    """Hiển thị HUD điều hành buổi tập trực tiếp rảnh tay hoặc tự nhập sau khi tập."""
    st.header("⚡ Phòng tập Trực tiếp (Workout HUD)")

    c_empty_l, c_center, c_empty_r = st.columns([1, 2.8, 1])
    with c_center:
        st.markdown("<div style='text-align: center; font-weight: 700; font-size: 15px; margin-bottom: 8px;'>Lựa chọn Chế độ Giám sát:</div>", unsafe_allow_html=True)
        mode = st.radio(
            "Lựa chọn Chế độ Giám sát:",
            options=["🤖 Chế độ AI Vision (Camera Rảnh tay)", "📝 Chế độ Tự do (Không dùng Camera)"],
            horizontal=True,
            label_visibility="collapsed",
            key="session_mode_selector"
        )

    col_left, col_right = st.columns([1.6, 1], gap="medium")

    if mode == "🤖 Chế độ AI Vision (Camera Rảnh tay)":
        with col_left:
            st.subheader("Màn hình Giám sát Chuyển động AI (Live Feed)")
            webcam(model=webcam_model(), key="live_pose")

        with col_right:
            st.subheader("Bảng Điều hành Phiên tập (HUD)")

            with st.container(border=True):
                st.markdown("### Bài tập Hiện tại: **Squat Thể dục (Bodyweight)**")
                st.caption("Mục tiêu buổi tập: 3 Sets × 12 Reps")

                c1, c2 = st.columns(2)
                with c1:
                    st.metric(label="Hiệp hiện tại", value="Set 2 / 3")
                with c2:
                    st.metric(label="Số Reps AI đếm", value="12 Reps", delta="Đạt chuẩn")

            with st.container(border=True):
                st.markdown("### ⏱️ Đồng hồ Nghỉ Giữa Hiệp (Rest Timer)")
                st.progress(60 / 60, text="Thời gian nghỉ: 60s còn lại")
                st.caption("🔊 Trợ lý Giọng nói sẽ đếm ngược 3... 2... 1... khi sắp hết giờ nghỉ!")

            with st.container(border=True):
                st.markdown("### 📋 Danh sách Bài kế tiếp (Up Next)")
                st.write("1. **Push-up (Hít đất)** — 3 sets × 10 reps")
                st.write("2. **Plank Tĩnh** — 3 sets × 45s")
                st.write("3. **Glute Bridge** — 3 sets × 15 reps")

            st.markdown("---")
            if st.button("🏁 Hoàn tất Buổi tập & Sang Đánh giá", type="primary", use_container_width=True):
                st.session_state["has_worked_out_today"] = True
                st.session_state["nav_selection"] = "📝 Đánh giá Sau Buổi tập"
                st.rerun()

    else:
        # Chế độ Tự do Không Camera
        with col_left:
            st.subheader("Ghi nhận Kết quả Buổi tập (Không Camera)")
            st.success("🌱 Bạn đang ở Chế độ Tự do: Thoải mái tập luyện ngoài công viên hoặc không gian riêng tư mà không cần bật webcam.")

            with st.form("manual_session_form"):
                st.markdown("#### Nhập kết quả thực tế từng bài:")
                st.number_input("1. Squat Thể dục — Số reps hoàn thành:", min_value=0, max_value=100, value=36)
                st.number_input("2. Push-up — Số reps hoàn thành:", min_value=0, max_value=100, value=30)
                st.number_input("3. Plank tĩnh — Tổng giây giữ được:", min_value=0, max_value=300, value=120)

                submitted = st.form_submit_button("Lưu & Kết thúc Buổi tập", type="primary")
                if submitted:
                    st.session_state["has_worked_out_today"] = True
                    st.success("Đã ghi nhận toàn bộ kết quả vào nhật ký!")
                    st.session_state["nav_selection"] = "📝 Đánh giá Sau Buổi tập"
                    st.rerun()

        with col_right:
            st.subheader("Hướng dẫn buổi tập")
            st.info("Hãy hoàn thành bài tập theo khả năng của bạn. Nếu mệt giữa chừng, bạn có thể nghỉ sớm; AI sẽ dựa vào tỉ lệ hoàn thành thực tế để điều chỉnh kế hoạch tiếp theo.")
