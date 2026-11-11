"""FitSense Exercise Library — replacement view with reliable rendering.

Install optional live-search dependency: pip install streamlit-keyup
The module reads the existing st.session_state['exercise_library'] catalog.
"""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse

import streamlit as st

try:
    from st_keyup import st_keyup  # pip install streamlit-keyup
except ImportError:
    st_keyup = None


def _field(exercise: dict, *names: str, default=""):
    for name in names:
        result = exercise.get(name)
        if result is not None and result != "":
            return result
    return default


def _text(value) -> str:
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(v) for v in value)
    return str(value or "")


def _normalize(value: str) -> str:
    import unicodedata
    value = unicodedata.normalize("NFD", _text(value).casefold())
    return re.sub(r"\s+", " ", "".join(c for c in value if unicodedata.category(c) != "Mn")).strip()


def _svg_muscles(primary, secondary) -> str:
    """Render a trusted inline SVG; never pass this XML to st.image()."""
    primary_names = _normalize(primary)
    secondary_names = _normalize(secondary)
    def paint(*words):
        joined = " ".join(words)
        if any(w in primary_names for w in words):
            return "#22c55e"
        if any(w in secondary_names for w in words):
            return "#fb923c"
        return "#25354b"
    chest = paint("nguc", "chest", "pectoral")
    arms = paint("tay", "arm", "bicep", "tricep", "vai", "shoulder")
    core = paint("bung", "core", "abs", "abdom")
    legs = paint("dui", "chan", "leg", "quad", "glute", "hamstring", "calf", "bap chan", "mong")
    back = paint("lung", "back", "lat")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 280" role="img" aria-label="Sơ đồ nhóm cơ minh họa" style="max-height:250px;max-width:100%;">
      <circle cx="110" cy="30" r="21" fill="#6b7d95"/>
      <rect x="82" y="57" width="56" height="90" rx="20" fill="{back}"/>
      <path d="M82 71 Q109 59 138 71 L134 100 L86 100Z" fill="{chest}"/>
      <rect x="94" y="104" width="32" height="39" rx="8" fill="{core}"/>
      <rect x="54" y="63" width="25" height="97" rx="12" fill="{arms}" transform="rotate(9 66 110)"/>
      <rect x="141" y="63" width="25" height="97" rx="12" fill="{arms}" transform="rotate(-9 154 110)"/>
      <rect x="83" y="143" width="25" height="107" rx="12" fill="{legs}"/>
      <rect x="112" y="143" width="25" height="107" rx="12" fill="{legs}"/>
      <rect x="79" y="246" width="30" height="11" rx="5" fill="#738399"/>
      <rect x="111" y="246" width="30" height="11" rx="5" fill="#738399"/>
      <text x="110" y="273" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#aab8ca">Minh họa nhóm cơ</text>
    </svg>'''


def _draw_muscle_svg(ex: dict):
    svg = _svg_muscles(_field(ex, "primary_muscles", "primary_muscle"),
                       _field(ex, "secondary_muscles", "secondary_muscle"))
    # st.html supports raw HTML/SVG; the SVG above is internally generated,
    # not user-provided markup. Fallback for earlier versions of Streamlit.
    if hasattr(st, "html"):
        st.html(svg)
    else:
        st.markdown(svg, unsafe_allow_html=True)


def _safe_media(value) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    if value.startswith("data:"):
        return value.startswith("data:image/gif;base64,")
    parts = urlparse(value)
    return (parts.scheme in ("http", "https") and bool(parts.netloc)) or (
        not parts.scheme and not value.startswith(("/", "\\")) and ".." not in value.replace("\\", "/").split("/")
    )


def _details(ex: dict):
    st.markdown(f"### {_text(_field(ex, 'name', 'name_vi', 'title', default='Bài tập'))}")
    st.write(_text(_field(ex, "description", "instruction", "overview", default="Chưa có mô tả.")))
    a, b = st.columns([1, 2])
    with a:
        st.caption("Sơ đồ nhóm cơ (mang tính minh họa)")
        _draw_muscle_svg(ex)
    with b:
        st.write("**Cơ chính:**", _text(_field(ex, "primary_muscles", "primary_muscle", default="Chưa cập nhật")))
        st.write("**Cơ phụ:**", _text(_field(ex, "secondary_muscles", "secondary_muscle", default="Chưa cập nhật")))
        st.write("**Dụng cụ:**", _text(_field(ex, "equipment", default="Không cần")))
        st.write("**Độ khó:**", _text(_field(ex, "difficulty", default="Chưa cập nhật")))
    steps = _field(ex, "steps", "instructions", "how_to", default=[])
    if isinstance(steps, str):
        steps = [x.strip() for x in steps.split("\n") if x.strip()]
    if steps:
        st.markdown("**Các bước thực hiện:**")
        for i, step in enumerate(steps, 1):
            st.write(f"{i}. {step}")
    mistake = _field(ex, "common_mistake", "common_mistakes")
    if mistake:
        st.warning(f"Lỗi thường gặp: {_text(mistake)}")
    substitute = _field(ex, "substitute", "alternative")
    if substitute:
        st.info(f"Bài tập thay thế: {_text(substitute)}")
    media = _field(ex, "gif_url", "gif", "animation_url", "video_gif", "image_url", "image")
    if _safe_media(media):
        try:
            st.image(media, caption="Hướng dẫn động tác", use_container_width=True)
        except Exception:
            st.caption("Không tải được ảnh/GIF hướng dẫn. Vui lòng kiểm tra đường dẫn media.")
    else:
        st.caption("Bài tập này chưa được gắn GIF hướng dẫn hợp lệ.")


def _live_query() -> str:
    if st_keyup is not None:
        # Unlike st.text_input, streamlit-keyup sends changes as the user types.
        return st_keyup("🔍 Tìm kiếm bài tập", key="fitsense_library_live_search", debounce=250) or ""
    st.caption("Để tìm kiếm ngay khi gõ, cài: pip install streamlit-keyup")
    return st.text_input("🔍 Tìm kiếm bài tập", key="fitsense_library_fallback_search")


def render_exercise_library_view():
    st.header("📚 Thư viện Động tác Calisthenics & Thể thao")
    st.caption("Tìm kiếm, lọc và chọn bài tập để xem GIF, nhóm cơ, kỹ thuật thực hiện.")
    library = st.session_state.get("exercise_library") or []
    if not library:
        st.info("Thư viện chưa có dữ liệu. Hãy kiểm tra bước load_catalog() trong app.py.")
        return

    query = _normalize(_live_query())
    c1, c2, c3 = st.columns(3)
    with c1:
        equipment = st.selectbox("Dụng cụ", ["Mọi dụng cụ"] + sorted({
            _text(_field(ex, "equipment", default="Không cần")) for ex in library
        }), key="fitsense_lib_equipment")
    with c2:
        difficulty = st.selectbox("Độ khó", ["Tất cả"] + sorted({
            _text(_field(ex, "difficulty", default="Chưa phân loại")) for ex in library
        }), key="fitsense_lib_difficulty")
    with c3:
        kind = st.selectbox("Loại bài tập", ["Tất cả"] + sorted({
            _text(_field(ex, "category", "type", "exercise_type", default="Chưa phân loại"))
            for ex in library
        }), key="fitsense_lib_category")

    result = []
    for idx, ex in enumerate(library):
        haystack = _normalize(" ".join(_text(_field(ex, k)) for k in (
            "name", "name_vi", "name_en", "title", "description", "primary_muscle", "primary_muscles",
            "secondary_muscle", "secondary_muscles", "category", "type", "equipment")))
        if query and query not in haystack:
            continue
        if equipment != "Mọi dụng cụ" and _text(_field(ex, "equipment", default="Không cần")) != equipment:
            continue
        if difficulty != "Tất cả" and _text(_field(ex, "difficulty", default="Chưa phân loại")) != difficulty:
            continue
        if kind != "Tất cả" and _text(_field(ex, "category", "type", "exercise_type", default="Chưa phân loại")) != kind:
            continue
        result.append((idx, ex))

    st.markdown(f"**{len(result)} / {len(library)} bài tập phù hợp**")
    if not result:
        st.info("Không tìm thấy bài tập phù hợp. Hãy thay đổi từ khóa hoặc bộ lọc.")
        return

    # Show ALL matching summaries first; expensive GIF/media loads only after selection.
    for offset in range(0, len(result), 2):
        columns = st.columns(2)
        for column, (idx, ex) in zip(columns, result[offset:offset + 2]):
            with column:
                with st.container(border=True):
                    name = _text(_field(ex, "name", "name_vi", "title", default=f"Bài tập {idx+1}"))
                    st.subheader(name)
                    st.caption(" · ".join(filter(None, [
                        _text(_field(ex, "category", "type", "exercise_type")),
                        _text(_field(ex, "difficulty")),
                    ])))
                    st.write("**Cơ chính:**", _text(_field(ex, "primary_muscles", "primary_muscle", default="Chưa cập nhật")))
                    st.write("**Dụng cụ:**", _text(_field(ex, "equipment", default="Không cần")))
                    if st.button("Xem hướng dẫn & GIF", key=f"fitsense_library_open_{idx}", use_container_width=True):
                        st.session_state["fitsense_library_selected"] = idx
                        st.rerun()

    selected = st.session_state.get("fitsense_library_selected")
    if selected is not None and isinstance(selected, int) and 0 <= selected < len(library):
        st.divider()
        if st.button("Đóng hướng dẫn", key="fitsense_library_close"):
            st.session_state["fitsense_library_selected"] = None
            st.rerun()
        _details(library[selected])


# Compatibility with the original import entrypoint if needed.
def render_library_view():
    return render_exercise_library_view()
