"""SCRUM-17: validated, read-only exercise catalogue and deterministic search.

No network calls, personal data or Streamlit dependencies in this module.
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parents[1] / 'data' / 'exercises.json'
MUSCLES = {
    'chest': 'Ngực', 'back': 'Lưng / xô', 'shoulders': 'Vai',
    'triceps': 'Tay sau', 'biceps': 'Tay trước', 'core': 'Bụng / core',
    'glutes': 'Mông', 'quads': 'Đùi trước', 'hamstrings': 'Đùi sau',
    'calves': 'Bắp chân', 'hip_flexors': 'Cơ gập hông',
}
EQUIPMENT = {'mat': 'Thảm', 'chair': 'Ghế tựa / Điểm tựa cao', 'band': 'Dây kháng lực'}
INJURIES = {'wrist': 'Cổ tay', 'knee': 'Khớp gối'}
LEVELS = ('Beginner', 'Intermediate', 'Advanced')


def normalize(text: str) -> str:
    """Unicode-aware case- and accent-insensitive search."""
    text = unicodedata.normalize('NFD', str(text).casefold().replace('đ', 'd'))
    return ''.join(c for c in text if not unicodedata.combining(c)).strip()


def validate_catalog(items: list[dict]) -> None:
    """Reject malformed references, inconsistent tags and missing safety guidance."""
    if not isinstance(items, list) or not items:
        raise ValueError('Thư viện phải chứa danh sách bài tập không rỗng.')
    ids = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('Mỗi bài tập phải là một object.')
        for key in ('id', 'name', 'name_en', 'category', 'difficulty', 'description',
                    'safety_notes', 'steps', 'common_mistakes', 'primary_muscles',
                    'secondary_muscles', 'equipment', 'avoid_if', 'alternatives'):
            if key not in item:
                raise ValueError(f"Bài tập thiếu trường: {key}")
        eid = item['id']
        if not isinstance(eid, str) or not eid or eid in ids:
            raise ValueError('Mã bài tập trống hoặc trùng lặp.')
        ids.add(eid)
        if item['difficulty'] not in LEVELS:
            raise ValueError(f'{eid}: trình độ không hợp lệ.')
        for key in ('name', 'name_en', 'category', 'description', 'safety_notes'):
            if not isinstance(item[key], str) or not item[key].strip():
                raise ValueError(f'{eid}: {key} phải có nội dung.')
        for key in ('steps', 'common_mistakes'):
            if not isinstance(item[key], list) or not item[key] or not all(isinstance(s,str) and s.strip() for s in item[key]):
                raise ValueError(f'{eid}: {key} không hợp lệ.')
        for key in ('primary_muscles', 'secondary_muscles', 'equipment', 'avoid_if', 'alternatives'):
            if not isinstance(item[key], list) or not all(isinstance(v, str) for v in item[key]):
                raise ValueError(f'{eid}: {key} phải là danh sách mã.')
        if not item['primary_muscles'] or set(item['primary_muscles']+item['secondary_muscles']) - MUSCLES.keys():
            raise ValueError(f'{eid}: nhóm cơ chưa khai báo.')
        if set(item['equipment']) - EQUIPMENT.keys() or set(item['avoid_if']) - INJURIES.keys():
            raise ValueError(f'{eid}: mã dụng cụ hoặc hạn chế không hợp lệ.')
        gif = item.get('media_gif')
        if gif is not None and (not isinstance(gif,str) or not gif.startswith('assets/exercises/') or '..' in gif):
            raise ValueError(f'{eid}: đường dẫn minh họa không hợp lệ.')
    for item in items:
        if any(a not in ids or a == item['id'] for a in item['alternatives']):
            raise ValueError(f"{item['id']}: mã bài thay thế không hợp lệ.")


def load_catalog(path: str | Path = CATALOG_PATH) -> list[dict]:
    """Read and validate local JSON; propagate clear errors instead of silently hiding them."""
    with Path(path).open(encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise ValueError('Phiên bản dữ liệu thư viện không được hỗ trợ.')
    items = data.get('exercises')
    validate_catalog(items)
    return items


def search_exercises(catalog: list[dict], query: str = '', muscle: str = '',
                     role: str = 'all', equipment: str = '', difficulty: str = '',
                     category: str = '') -> list[dict]:
    """Intersection of search and filters, preserving JSON catalogue ordering."""
    if role not in {'all', 'primary', 'secondary'}:
        raise ValueError('Vai trò nhóm cơ không hợp lệ.')
    needle = normalize(query)
    result = []
    for ex in catalog:
        muscles = (ex['primary_muscles'] if role == 'primary' else
                   ex['secondary_muscles'] if role == 'secondary' else
                   ex['primary_muscles'] + ex['secondary_muscles'])
        names = [ex['name'], ex['name_en'], ex['category']]
        names += [MUSCLES.get(m, m) for m in ex['primary_muscles']+ex['secondary_muscles']]
        names += ex['primary_muscles']+ex['secondary_muscles']
        if needle and not any(needle in normalize(value) for value in names):
            continue
        if muscle and muscle not in muscles:
            continue
        if equipment and equipment not in ex['equipment']:
            continue
        if difficulty and ex['difficulty'] != difficulty:
            continue
        if category and ex['category'] != category:
            continue
        result.append(ex)
    return result


def suggest_alternatives(exercise: dict, catalog: list[dict],
                         available_equipment: set[str] | None = None,
                         limitations: set[str] | None = None) -> list[dict]:
    """Recommend related exercises by ID with injury/equipment safeguards.

    Explicitly curated alternatives win. If all curated choices are unavailable,
    search the full catalogue by *primary and secondary* muscle overlap.
    """
    by_id = {ex['id']: ex for ex in catalog}
    available = None if available_equipment is None else set(available_equipment)
    limitations = set(limitations or ())
    def eligible(ex):
        return (ex['id'] != exercise['id'] and
                set(ex['avoid_if']).isdisjoint(limitations) and
                (available is None or set(ex['equipment']).issubset(available)))
    explicit = [by_id[eid] for eid in exercise['alternatives']
                if eid in by_id and eligible(by_id[eid])]
    if explicit:
        return explicit
    # If a restriction rules out the *original* exercise, do not offer
    # unreviewed medical substitutions just to fill the dropdown.
    if limitations.intersection(exercise['avoid_if']):
        return []
    primary = set(exercise['primary_muscles'])
    secondary = set(exercise['secondary_muscles'])
    ranked = []
    for candidate in catalog:
        if not eligible(candidate):
            continue
        cp, cs = set(candidate['primary_muscles']), set(candidate['secondary_muscles'])
        score = 4 * len(primary & cp) + 2 * len(primary & cs) + len(secondary & cp)
        if score:
            ranked.append((-score, len(candidate['equipment']), candidate['name'], candidate))
    ranked.sort(key=lambda item: item[:3])
    return [x[-1] for x in ranked[:8]]


GROUPS8 = {
    'Ngực': ('chest',), 'Lưng': ('back',), 'Vai': ('shoulders',),
    'Tay': ('biceps', 'triceps'), 'Bụng / Core': ('core', 'hip_flexors'),
    'Mông': ('glutes',), 'Đùi': ('quads', 'hamstrings'), 'Bắp chân': ('calves',),
}


def resolve_exercise(name_or_id: str, catalog: list[dict]) -> dict | None:
    """Match plan names from English/Vietnamese and legacy parenthesized labels."""
    query = normalize(name_or_id)
    if not query:
        return None
    for ex in catalog:
        if query in {normalize(ex['id']), normalize(ex['name']), normalize(ex['name_en'])}:
            return ex
    for ex in catalog:
        if normalize(ex['name']) in query or normalize(ex['name_en']) in query:
            return ex
    return None


def compatible_replacements(current: dict, catalog: list[dict],
                            available_equipment: set[str] | None = None,
                            limitations: set[str] | None = None) -> list[dict]:
    """Return ranked replacements for either a JSON-catalogue item or planner item.

    Alternatives share at least one of the target's main/assisting muscles;
    constraints are respected, never fabricate a candidate name.
    """
    source = current if 'primary_muscles' in current else resolve_exercise(current.get('exercise_id') or current.get('name', ''), catalog)
    limitations = set(limitations or ())
    available = None if available_equipment is None else set(available_equipment)
    primary = set((source or {}).get('primary_muscles', []))
    secondary = set((source or {}).get('secondary_muscles', []))
    if not primary:
        muscle_text = normalize(str(current.get('primary_muscle', '')) + ' ' + str(current.get('secondary_muscle', '')))
        # Translate common planner labels, including legacy "Lưng & Xô" and "Bụng & Core".
        aliases = {
            'chest': ('nguc', 'chest'), 'back': ('lung', 'xo', 'back', 'row'),
            'shoulders': ('vai', 'shoulder'), 'triceps': ('tay sau', 'tricep'),
            'biceps': ('tay truoc', 'bicep'), 'core': ('bung', 'core', 'abs'),
            'glutes': ('mong', 'glute'), 'quads': ('dui truoc', 'quads', 'chan'),
            'hamstrings': ('dui sau', 'hamstring'), 'calves': ('bap chan', 'calf'),
            'hip_flexors': ('gap hong', 'hip flexor'),
        }
        primary = {key for key, terms in aliases.items() if any(term in muscle_text for term in terms)}
    ranked = []
    for ex in catalog:
        if source is not None and ex['id'] == source['id']:
            continue
        if normalize(ex['name']) == normalize(current.get('name', '')):
            continue
        if not set(ex['avoid_if']).isdisjoint(limitations):
            continue
        if available is not None and not set(ex['equipment']).issubset(available):
            continue
        ep,es=set(ex['primary_muscles']),set(ex['secondary_muscles'])
        points=4*len(primary & ep)+2*len(primary & es)+len(secondary & ep)
        if points>0:
            ranked.append((-points,len(ex['equipment']),ex['name'],ex))
    ranked.sort(key=lambda item:item[:3])
    return [item[3] for item in ranked]
