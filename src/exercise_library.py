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
    """Only explicitly reviewed alternative IDs, screened for equipment and injuries.

    Passing None for equipment means no equipment information (no filtering).
    Passing None for limitations means none were declared (not a medical clearance).
    """
    by_id = {ex['id']: ex for ex in catalog}
    available = None if available_equipment is None else set(available_equipment)
    limitations = set(limitations or ())
    candidates = []
    for alt_id in exercise['alternatives']:
        alt = by_id.get(alt_id)
        if not alt or not set(alt['avoid_if']).isdisjoint(limitations):
            continue
        if available is not None and not set(alt['equipment']).issubset(available):
            continue
        candidates.append(alt)
    return candidates
