"""Entry point for the Ratatouille Streamlit starter."""

import streamlit as st

st.set_page_config(page_title="Ratatouille", page_icon="🍳", layout="wide")
st.title("Ratatouille")
st.caption("Khung khởi đầu của nhóm — chưa tích hợp AI và các chức năng nghiệp vụ.")

tabs = st.tabs([
    "Hồ sơ · Bếp · Nguyên liệu",
    "Thực đơn · Mua sắm",
    "Nấu ăn",
    "Nhật ký · Thống kê",
    "Thói quen · Tập luyện",
])
modules = [
    ("profile_inventory", "Quản lý hồ sơ, thiết bị bếp và các lô nguyên liệu."),
    ("menu_shopping", "Đề xuất thực đơn, tính lượng thiếu và giỏ mua dự kiến."),
    ("cooking", "Hướng dẫn nấu theo thực đơn đã xác nhận."),
    ("diary_statistics", "Ghi nhận thực tế và thống kê chi tiêu, ăn uống."),
    ("habits_exercise", "Theo dõi streak và hỗ trợ gợi ý buổi tập."),
]
for tab, (module, description) in zip(tabs, modules):
    with tab:
        st.subheader(description)
        st.info(f"Chưa triển khai. Module phụ trách: src/{module}.py")
