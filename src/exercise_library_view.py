"""SCRUM-17 Streamlit catalogue UI with visual, schematic muscle highlighting."""
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

import streamlit as st

from src.exercise_library import (EQUIPMENT, INJURIES, LEVELS, MUSCLES,
                                  load_catalog, search_exercises, suggest_alternatives)

ROOT = Path(__file__).resolve().parents[1]
# Diagram coordinates are illustrative regions, NOT anatomical precision.
POSITIONS = {
    'chest': (77, 83), 'shoulders': (45, 74), 'triceps': (36, 104),
    'biceps': (39, 95), 'core': (75, 120), 'back': (172, 103),
    'glutes': (172, 145), 'quads': (63, 178), 'hamstrings': (187, 178),
    'calves': (63, 230), 'hip_flexors': (88, 151),
}


def muscle_svg(primary: list[str], secondary: list[str]) -> bytes:
    """Original front/back stick-body overview. Emphasis is indicative only."""
    dots = []
    for muscle in secondary:
        x,y = POSITIONS[muscle]
        dots.append(f'<circle cx="{x}" cy="{y}" r="12" fill="#e6a950" fill-opacity="0.7"/>')
    for muscle in primary:
        x,y = POSITIONS[muscle]
        dots.append(f'<circle cx="{x}" cy="{y}" r="14" fill="#2878d0" fill-opacity="0.85"/>')
    # Two abstract symmetrical standing figures, no external image asset.
    figures = ''
    for cx in (75, 172):
        figures += (f'<circle cx="{cx}" cy="30" r="16" fill="none" stroke="#687b8b" stroke-width="5"/>'
                    f'<path d="M{cx} 51 V142 M{cx} 63 l-31 57 M{cx} 63 l31 57 '
                    f'M{cx} 142 l-18 98 M{cx} 142 l18 98" fill="none" '
                    f'stroke="#687b8b" stroke-width="12" stroke-linecap="round"/>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 250 275">'
           f'<rect width="250" height="275" rx="15" fill="#f0f5f9"/>'
           f'{figures}{"".join(dots)}'
           f'<text x="75" y="263" text-anchor="middle" font-size="12" fill="#263749">Mặt trước</text>'
           f'<text x="172" y="263" text-anchor="middle" font-size="12" fill="#263749">Mặt sau</text></svg>')
    return svg.encode('utf-8')


def _profile_filters() -> tuple[set[str] | None, set[str]]:
    """Best-effort mapping of existing user-profile labels, with no false clearance."""
    profile = st.session_state.get('user_profile') or {}
    raw_equip = profile.get('equipment')
    available = None
    if isinstance(raw_equip, list):
        available = set()
        for name in raw_equip:
            label = str(name).lower()
            if 'thảm' in label: available.add('mat')
            if 'ghế' in label or 'điểm tựa' in label: available.add('chair')
            if 'dây kháng lực' in label: available.add('band')
    restrictions = set()
    for tag in profile.get('restrictions', []) or []:
        label = str(tag).lower()
        if 'cổ tay' in label: restrictions.add('wrist')
        if 'gối' in label: restrictions.add('knee')
    return available, restrictions


def render_exercise_library_view() -> None:
    st.header('📚 Thư viện bài tập Calisthenics & Thể thao')
    st.caption('Tra cứu tên tiếng Việt/Anh, nhóm cơ chính/phụ, độ khó, dụng cụ và bài tập thay thế.')
    try:
        library = st.session_state.get('exercise_library') or load_catalog()
    except (OSError, ValueError) as exc:
        st.error(f'Không đọc được cơ sở dữ liệu bài tập: {exc}')
        return

    muscle_opts = {'Tất cả nhóm cơ': ''} | {v: k for k,v in MUSCLES.items()}
    equip_opts = {'Mọi dụng cụ': '', 'Không cần dụng cụ': '__none__'} | {v: k for k,v in EQUIPMENT.items()}
    groups = ['Tất cả loại'] + sorted(set(ex['category'] for ex in library))
    c1,c2,c3 = st.columns([2,1,1])
    with c1: query = st.text_input('🔍 Tìm theo tên hoặc nhóm cơ', placeholder='Push-up, hit dat, nguc, back...')
    with c2: muscle_label = st.selectbox('Nhóm cơ', list(muscle_opts))
    with c3: role_label = st.selectbox('Vai trò cơ', ['Chính hoặc phụ','Chính','Phụ'])
    c4,c5,c6 = st.columns(3)
    with c4: equip_label = st.selectbox('Dụng cụ', list(equip_opts))
    with c5: difficulty = st.selectbox('Độ khó', ['Tất cả']+list(LEVELS))
    with c6: category = st.selectbox('Loại bài tập', groups)
    role = {'Chính hoặc phụ': 'all', 'Chính':'primary', 'Phụ':'secondary'}[role_label]
    found = search_exercises(library, query=query, muscle=muscle_opts[muscle_label], role=role,
                             difficulty='' if difficulty == 'Tất cả' else difficulty,
                             category='' if category == 'Tất cả loại' else category)
    equipment_key = equip_opts[equip_label]
    found = [ex for ex in found if not equipment_key or
             (not ex['equipment'] if equipment_key == '__none__' else equipment_key in ex['equipment'])]
    st.write(f'**{len(found)} / {len(library)}** bài tập phù hợp')
    if not found:
        st.info('Không tìm thấy bài tập. Hãy thử bỏ bớt điều kiện lọc.')
        return
    available, limitations = _profile_filters()
    for pos in range(0,len(found),2):
        cols = st.columns(2)
        for col, ex in zip(cols, found[pos:pos+2]):
            with col:
                with st.container(border=True):
                    st.subheader(f"{ex['name']}")
                    st.caption(f"{ex['name_en']} · {ex['category']} · {ex['difficulty']}")
                    st.write('**Cơ chính:** '+', '.join(MUSCLES[k] for k in ex['primary_muscles']))
                    st.write('**Cơ phụ:** '+(', '.join(MUSCLES[k] for k in ex['secondary_muscles']) or 'Không khai báo'))
                    st.write('**Dụng cụ:** '+(', '.join(EQUIPMENT[k] for k in ex['equipment']) or 'Không cần'))
                    if limitations.intersection(ex['avoid_if']):
                        st.warning('Hồ sơ của bạn có hạn chế liên quan. Không nên tự thực hiện bài này khi chưa được chuyên gia đánh giá.')
                    st.image(muscle_svg(ex['primary_muscles'], ex['secondary_muscles']),
                             caption='Sơ đồ vị trí nhóm cơ (mang tính minh họa): Xanh = cơ chính, Cam = cơ phụ',
                             use_container_width=True)
                    media = ex.get('media_gif')
                    if media and (ROOT / media).is_file():
                        st.image(str(ROOT / media), caption='GIF chuyển động giản lược, không phải hướng dẫn kỹ thuật đầy đủ', use_container_width=True)
                    else:
                        st.caption('Chưa có GIF/video được kiểm chứng cho bài này; xem hướng dẫn bằng chữ bên dưới.')
                    with st.expander('📌 Hướng dẫn, lỗi thường gặp và lưu ý an toàn'):
                        for i, step in enumerate(ex['steps'], 1):
                            st.write(f'{i}. {step}')
                        for mistake in ex['common_mistakes']:
                            st.warning('Lỗi cần tránh: '+mistake)
                        st.info(ex['safety_notes'])
                    alts = suggest_alternatives(ex, library, available_equipment=available, limitations=limitations)
                    if alts:
                        st.write('**Gợi ý thay thế phù hợp với thông tin đã khai báo:** '+', '.join(x['name'] for x in alts))
                    else:
                        st.caption('Chưa có bài thay thế phù hợp trong danh sách đã kiểm duyệt.')
    st.caption('Sơ đồ chỉ minh họa khu vực nhóm cơ, không phải sơ đồ giải phẫu y khoa. Lưu ý an toàn không thay thế tư vấn chuyên môn.')
