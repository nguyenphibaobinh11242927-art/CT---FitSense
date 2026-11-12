"""SCRUM-17 Streamlit catalogue UI with visual, schematic muscle highlighting."""
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

import streamlit as st

from src.exercise_library import (EQUIPMENT, INJURIES, LEVELS, MUSCLES,
                                  load_catalog, search_exercises, suggest_alternatives)

ROOT = Path(__file__).resolve().parents[1]
# Anatomical silhouette with continuous human contours, not stick figures.
# Illustration is indicative, not a medical anatomy reference.
# Each front/back figure has recognizable torso, shoulders, hands, pelvis, legs and feet.
# Regions are highlighted by colour according to the active exercise.
ANATOMICAL_REGIONS = {
    'chest': [(126,164,32,19)], 'shoulders': [(88,143,19,23),(165,143,19,23)],
    'triceps': [(180,200,12,33)], 'biceps': [(77,195,12,31)],
    'core': [(127,214,24,47)], 'back': [(377,182,38,42)],
    'glutes': [(377,274,34,19)], 'quads': [(111,337,20,48),(146,337,20,48)],
    'hamstrings': [(361,345,19,48),(392,345,19,48)],
    'calves': [(108,433,13,36),(397,431,13,37)],
    'hip_flexors': [(125,293,22,18)],
}


def muscle_svg(primary: list[str], secondary: list[str]) -> str:
    """Front/back detailed body-shape illustration without stick-figure limbs."""
    def body(cx: int) -> str:
        # Symmetric human silhouette, with physically joined torso and limbs.
        torso = (f'<path d="M{cx-30} 128 Q{cx-11} 115 {cx} 122 Q{cx+11} 115 {cx+30} 128 '
                 f'L{cx+38} 158 Q{cx+33} 191 {cx+27} 215 L{cx+33} 270 '
                 f'Q{cx} 292 {cx-33} 270 L{cx-27} 215 Q{cx-33} 191 {cx-38} 158 Z"/>')
        head = f'<ellipse cx="{cx}" cy="91" rx="23" ry="30"/>'
        neck = f'<path d="M{cx-13} 112 L{cx-13} 136 L{cx+13} 136 L{cx+13} 112 Z"/>'
        limbs = (f'<path d="M{cx-29} 129 Q{cx-57} 128 {cx-64} 168 '
                 f'L{cx-87} 251 Q{cx-89} 267 {cx-77} 272 Q{cx-68} 272 {cx-63} 258 '
                 f'L{cx-35} 188 L{cx-20} 157 Z"/>'
                 f'<path d="M{cx+29} 129 Q{cx+57} 128 {cx+64} 168 '
                 f'L{cx+87} 251 Q{cx+89} 267 {cx+77} 272 Q{cx+68} 272 {cx+63} 258 '
                 f'L{cx+35} 188 L{cx+20} 157 Z"/>'
                 f'<path d="M{cx-33} 269 Q{cx-43} 290 {cx-40} 335 '
                 f'L{cx-26} 452 Q{cx-22} 476 {cx-10} 474 L{cx-4} 460 '
                 f'L{cx-4} 354 Q{cx-2} 317 {cx} 303 L{cx} 278 Z"/>'
                 f'<path d="M{cx+33} 269 Q{cx+43} 290 {cx+40} 335 '
                 f'L{cx+26} 452 Q{cx+22} 476 {cx+10} 474 L{cx+4} 460 '
                 f'L{cx+4} 354 Q{cx+2} 317 {cx} 303 L{cx} 278 Z"/>')
        detail = (f'<path d="M{cx} 145 V267 M{cx-30} 165 Q{cx} 185 {cx+30} 165 '
                  f'M{cx-24} 215 Q{cx} 228 {cx+24} 215 M{cx-22} 238 Q{cx} 247 {cx+22} 238 '
                  f'M{cx-32} 304 L{cx-15} 385 M{cx+32} 304 L{cx+15} 385" '
                  f'fill="none" stroke="#9a5c50" stroke-width="2.2" opacity=".65"/>')
        return '<g fill="#dfaa90" stroke="#855b51" stroke-width="2.8">'+head+neck+limbs+torso+'</g>'+detail
    def ovals(muscles, color, opacity):
        out=[]
        for muscle in muscles:
            for x,y,rx,ry in ANATOMICAL_REGIONS.get(muscle, []):
                out.append(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{color}" opacity="{opacity}"/>')
        return ''.join(out)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 505 520">'
            f'<rect width="505" height="520" rx="18" fill="#edf1f6"/>'
            f'<g>{body(127)}{body(377)}</g>'
            f'{ovals(secondary,"#e4a148", ".60")}{ovals(primary,"#2077cc", ".76")}'
            f'<text x="127" y="505" font-size="16" text-anchor="middle" fill="#223849">Mặt trước</text>'
            f'<text x="377" y="505" font-size="16" text-anchor="middle" fill="#223849">Mặt sau</text>'
            f'</svg>')


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
    st.caption('28 bài tập • 8 nhóm cơ • Tìm kiếm và thay thế có xét cơ chính + cơ phụ.')
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
    st.write(f'**{len(found)} / {len(library)}** bài tập phù hợp · 8 nhóm cơ: Ngực, Lưng, Vai, Tay, Core, Mông, Đùi, Bắp chân')
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
                    with st.expander('🧍 Xem mô hình cơ thể người và hướng dẫn', expanded=False):
                        st.image(muscle_svg(ex['primary_muscles'], ex['secondary_muscles']),
                                 caption='Hình cơ thể người mặt trước/sau: xanh = cơ chính, cam = cơ phụ (mô phỏng, không phải ảnh người que)',
                                 use_container_width=True)
                        st.write('**Cách thực hiện:**')
                        for i, step in enumerate(ex['steps'], 1):
                            st.write(f'{i}. {step}')
                        st.write('**Lỗi thường gặp:**')
                        for mistake in ex['common_mistakes']:
                            st.warning(mistake)
                        st.info(ex['safety_notes'])
                        st.markdown('📷 [Thư viện hình ảnh hướng dẫn bài tập của ACE Fitness](https://www.acefitness.org/resources/everyone/exercise-library/) · [Hình giải phẫu cơ thể người (CC BY-SA 4.0)](https://commons.wikimedia.org/wiki/File:Muscles_front_and_back.svg)')
                        st.caption('Không dùng các GIF người que cũ. GIF/video người thật cho từng bài chưa có bản quyền để đóng gói offline; hãy xem ảnh hướng dẫn tại nguồn ACE.')
                    alts = suggest_alternatives(ex, library, available_equipment=available, limitations=limitations)
                    if alts:
                        st.write('**Gợi ý thay thế phù hợp với thông tin đã khai báo:** '+', '.join(x['name'] for x in alts))
                    else:
                        st.caption('Chưa có bài thay thế phù hợp trong danh sách đã kiểm duyệt.')
    st.caption('Sơ đồ chỉ minh họa khu vực nhóm cơ, không phải sơ đồ giải phẫu y khoa. Lưu ý an toàn không thay thế tư vấn chuyên môn.')
