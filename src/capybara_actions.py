"""Các thao tác lịch tập độc lập với AI và giao diện."""
from copy import deepcopy
import re
from src.exercise_library import normalize, resolve_exercise, LEVELS, MUSCLES, EQUIPMENT
from src.planner_generation import DEFAULT_DAYS


class ActionError(ValueError):
    pass


def validate_schedule(schedule):
    if not isinstance(schedule, list) or len(schedule) != 7 or any(
        not isinstance(d, dict) or not isinstance(d.get('exercises'), list)
        or any(not isinstance(e, dict) for e in d['exercises']) for d in schedule
    ) or [d.get('day') for d in schedule] != DEFAULT_DAYS:
        raise ActionError('Lịch tuần không hợp lệ.')


def _completed(day):
    return day.get('is_completed') or day.get('workout_status') in {'completed', 'in_progress'}


def _day(schedule, name):
    for day in schedule:
        if day['day'] == name:
            return day
    raise ActionError('Ngày tập không hợp lệ.')


def parse_action(message):
    """Chỉ thực hiện câu lệnh rõ ràng; không suy đoán từ câu phủ định."""
    text = ' '.join(normalize(message).strip(' .!?').split())
    injury = re.fullmatch(r'(?:toi |minh |em )?(?:bi |dang )?dau (?:khop |dau )?(goi|co tay)(?: (?:nen )?(?:hay )?doi bai tap(?: cho toi)?)?', text)
    if injury:
        return 'injury', {'injury': {'goi': 'knee', 'co tay': 'wrist'}[injury[1]]}
    move = re.fullmatch(r'(?:hay )?(?:doi|doi lich|doi buoi tap|doi lich tap|doi buoi|chuyen|chuyen lich|chuyen lich tap|doi lich tap|doi lich buoi tap) (thu [2-7]|chu nhat) (?:sang|voi|qua) (thu [2-7]|chu nhat)', text)
    # normalize converts both “dời” and “đổi” to “doi”
    if move:
        names = {normalize(d): d for d in DEFAULT_DAYS}
        return 'move', {'source_day': names[move[1]], 'target_day': names[move[2]]}
    if re.fullmatch(r'(?:(?:hom nay )?(?:toi |minh )?(?:cam thay )?(?:kha |rat )?met[, ]+)?(?:hay )?giam (?:tai(?: tap luyen)?|cuong do(?: tap luyen)?)(?: cho toi)?(?: hom nay)?', text):
        return 'deload', {}
    return None, {}


def _replacement(original, catalog, limits, equipment):
    primary, secondary = set(original['primary_muscles']), set(original['secondary_muscles'])
    ranked = []
    for candidate in catalog:
        if (candidate['id'] == original['id'] or limits.intersection(candidate['avoid_if'])
                or not set(candidate['equipment']).issubset(equipment)
                or LEVELS.index(candidate['difficulty']) > LEVELS.index(original['difficulty'])):
            continue
        cp, cs = set(candidate['primary_muscles']), set(candidate['secondary_muscles'])
        score = 4 * len(primary & cp) + 2 * len(primary & cs) + len(secondary & cp) + len(secondary & cs)
        # Cần ít nhất một nhóm cơ chính chung; ưu tiên phương án đã có trong thư viện
        if primary & cp:
            ranked.append((candidate['id'] not in original['alternatives'], -score, candidate['id'], candidate))
    return min(ranked, key=lambda row: row[:3])[3] if ranked else None


def _prescription(old, candidate):
    # Không giữ metadata kỹ thuật hoặc phương án thay thế của bài gây đau
    return {'id': candidate['id'], 'name': f"{candidate['name']} ({candidate['name_en']})",
            'sets': old.get('sets', 3), 'reps': old.get('reps', 12),
            'rest_sec': old.get('rest_sec', 60),
            'primary_muscle': ', '.join(MUSCLES[m] for m in candidate['primary_muscles']),
            'secondary_muscle': ', '.join(MUSCLES[m] for m in candidate['secondary_muscles']),
            'equipment': ', '.join(EQUIPMENT[e] for e in candidate['equipment']) or 'Bodyweight',
            'difficulty': candidate['difficulty'], 'form_tip': candidate['steps'][0]}


def swap_exercise_for_injury(schedule, injury, catalog, today_index, equipment, existing_limits=()):
    validate_schedule(schedule)
    if injury not in {'knee', 'wrist'} or not 0 <= today_index < 7:
        raise ActionError('Chấn thương hoặc ngày không được hỗ trợ.')
    limits = set(existing_limits) | {injury}
    plan, diff = deepcopy(schedule), []
    for day in plan:
        if DEFAULT_DAYS.index(day['day']) < today_index or _completed(day) or day.get('is_rest'):
            continue
        for i, old in enumerate(day['exercises']):
            original = resolve_exercise(old.get('id') or old.get('name', ''), catalog)
            if original and not limits.intersection(original['avoid_if']):
                continue
            if old.get('paused'):
                continue
            candidate = _replacement(original, catalog, limits, equipment) if original else None
            new = _prescription(old, candidate) if candidate else {**old, 'paused': True, 'pause_reason': 'Chưa xác định bài thay thế phù hợp; không thực hiện khi đang đau.'}
            day['exercises'][i] = new
            diff.append({'target_day': day['day'], 'exercise_index': i, 'old_exercise': old,
                         'new_exercise': new if candidate else None, 'status': 'replaced' if candidate else 'paused'})
    return plan, diff


def move_workout_day(schedule, source_day, target_day):
    validate_schedule(schedule)
    plan = deepcopy(schedule)
    source, target = _day(plan, source_day), _day(plan, target_day)
    if source is target:
        return plan, []
    if _completed(source) or _completed(target):
        raise ActionError('Không thay đổi buổi tập đã hoàn thành.')
    old_source, old_target = deepcopy(source), deepcopy(target)
    # Giữ định danh ngày, hoán đổi toàn bộ nội dung kế hoạch
    source.clear(); source.update({**old_target, 'day': source_day})
    target.clear(); target.update({**old_source, 'day': target_day})
    return plan, [{'target_day': source_day, 'old_day': old_source, 'new_day': deepcopy(source)},
                  {'target_day': target_day, 'old_day': old_target, 'new_day': deepcopy(target)}]


def apply_instant_deload(schedule, today_index):
    validate_schedule(schedule)
    if not 0 <= today_index < 7:
        raise ActionError('Ngày tập không hợp lệ.')
    plan, diff = deepcopy(schedule), []
    day = _day(plan, DEFAULT_DAYS[today_index])
    if day.get('is_rest') or _completed(day) or day.get('instant_deload_applied'):
        return plan, diff
    for i, exercise in enumerate(day['exercises']):
        reps = exercise.get('reps')
        if exercise.get('paused') or isinstance(reps, bool) or not (isinstance(reps, int) or isinstance(reps, str) and reps.isascii() and reps.isdigit()):
            continue
        if int(reps) < 1:
            continue
        new = max(1, int(reps) * 7 // 10)
        if new != int(reps):
            old = deepcopy(exercise)
            exercise['reps'] = str(new) if isinstance(reps, str) else new
            diff.append({'target_day': day['day'], 'exercise_index': i, 'old_exercise': old, 'new_exercise': deepcopy(exercise)})
    if diff:
        day['instant_deload_applied'] = True
    return plan, diff
