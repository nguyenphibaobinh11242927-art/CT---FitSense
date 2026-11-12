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


# Planner names can originate from an old AI plan or a user-imported file.
MUSCLE_ALIASES = {
    'chest': ('nguc', 'chest', 'pectoral'),
    'back': ('lung', 'xo', 'back', 'row'),
    'shoulders': ('vai', 'shoulder', 'deltoid'),
    'triceps': ('tay sau', 'tricep'),
    'biceps': ('tay truoc', 'bicep'),
    'core': ('bung', 'core', 'abs'),
    'glutes': ('mong', 'glute'),
    'quads': ('dui truoc', 'quadricep', 'quad'),
    'hamstrings': ('dui sau', 'hamstring'),
    'calves': ('bap chan', 'calf'),
    'hip_flexors': ('gap hong', 'hip flexor'),
}


def _muscle_codes(value: object) -> set[str]:
    """Parse old Vietnamese/English labels; do not infer muscles from arbitrary text."""
    if isinstance(value, (list, tuple, set)):
        return {code for item in value for code in _muscle_codes(item)}
    text = normalize(value or '')
    if not text or text in ('khong', 'none', 'toan than'):
        return set()
    return {code for code, aliases in MUSCLE_ALIASES.items()
            if code == text or any(alias in text for alias in aliases)}


def planner_target_muscles(current: dict, catalog: list[dict]) -> tuple[set[str], set[str]]:
    """Resolve target primary/secondary muscle roles from catalogue or legacy plan."""
    source = current if current.get('primary_muscles') else resolve_exercise(
        current.get('exercise_id') or current.get('id') or current.get('name', ''), catalog)
    if source:
        return set(source.get('primary_muscles', [])), set(source.get('secondary_muscles', []))
    primary = _muscle_codes(current.get('primary_muscle', ''))
    secondary = _muscle_codes(current.get('secondary_muscle', '')) - primary
    return primary, secondary


def replacement_matches(current: dict, catalog: list[dict],
                        available_equipment: set[str] | None = None,
                        limitations: set[str] | None = None) -> list[dict]:
    """Candidates must exercise at least one of the original primary/secondary muscles.

    Annotate each result with a human-readable main/assisting muscle match.
    Preserve all original catalogue fields for downstream selection by stable ID.
    """
    target_primary, target_secondary = planner_target_muscles(current, catalog)
    target = target_primary | target_secondary
    if not target:
        return []  # Unknown muscle group: do not suggest unrelated exercises.
    limit = set(limitations or ())
    available = set(available_equipment) if available_equipment is not None else None
    current_id = current.get('exercise_id') or current.get('id')
    current_name = normalize(current.get('name', ''))
    ranked = []
    for candidate in catalog:
        if not isinstance(candidate, dict) or not candidate.get('id'):
            continue
        if (candidate['id'] == current_id or
                normalize(candidate.get('name','')) == current_name or
                normalize(candidate.get('name_en','')) == current_name):
            continue
        if not set(candidate.get('avoid_if', [])).isdisjoint(limit):
            continue
        if available is not None and not set(candidate.get('equipment', [])).issubset(available):
            continue
        cp = set(candidate.get('primary_muscles', []))
        cs = set(candidate.get('secondary_muscles', []))
        main_match = cp & target
        assist_match = cs & target
        if not (main_match or assist_match):
            continue
        # Prioritize preserving the original exercise's primary muscles.
        score = (8 * len(cp & target_primary) +
                 4 * len(cs & target_primary) +
                 2 * len(cp & target_secondary) +
                 len(cs & target_secondary))
        enriched = dict(candidate)
        enriched['match_primary'] = sorted(main_match)
        enriched['match_secondary'] = sorted(assist_match)
        ranked.append((-score, len(candidate.get('equipment', [])),
                       candidate['name'], enriched))
    ranked.sort(key=lambda item: item[:3])
    return [row[3] for row in ranked]


def compatible_replacements(current: dict, catalog: list[dict],
                            available_equipment: set[str] | None = None,
                            limitations: set[str] | None = None) -> list[dict]:
    """Backwards-compatible API returning only muscle-compatible exercise records."""
    return replacement_matches(current, catalog, available_equipment, limitations)
