# SCRUM-24 — QA & Automated Testing

- Lead: Đậu Cao Dũng (M03); Review & Merge: Nguyễn Minh Huy (M06)
- Sprint 4; 4.5 SP; branch `25127301`
- Baseline: ZIP `CT---FitSense-main(1).zip`, commit `5bbca4b018927985f893e8a780b3977b227899d5` (archive metadata).
- Scope: camera occlusion (simulated missing tracking), squat depth, X stop gesture, Streak >= 50%; Python regression; webcam manual validation.

## 1. Acceptance rules and assumptions

- Squat FSM: standing >= 160°, descending < 150°, bottom <= 90°, rising > 105°. Missing angle (`None`) invalidates the unfinished repetition, preserves the count and requires a standing frame before a new attempt.
- Python X FSM: both wrists strictly inside torso height, distance strictly below 15% of body width, visible head; default confirmation 45 frames or 1500 ms. After confirmation, the FSM locks repetitions and triggers only once until reset. These are Python rules, not an assertion of identical browser behavior.
- Streak: a calendar day qualifies when at least one recorded session has a known completion percentage in [50, 100], including partially completed/abandoned sessions reaching 50%. Same-day records count once; dates must be ISO calendar dates; invalid/future dates and missing rates do not qualify. Consecutive calendar days count; yesterday's streak remains current until today ends. Rest days are not automatically exempted. These aggregation, abandonment and grace-day policies are implementation assumptions requiring M06 confirmation. No persistence or per-account redesign is included: backend still uses existing in-memory global history.
- Preserve existing 70% deload recommendation rule; it is not the Streak threshold. Avoid rounding the session percentage before qualification. Evaluation records keep their supplied percentage rather than defaulting to 100%. Existing self-report evaluation behavior is preserved; no deduplication of evaluation versus workout records beyond calendar-day Streak counting.
- Browser X currently uses 35% shoulder width and completes the current set (rest timer), not necessarily the entire session; this differs from Python FSM. Do not claim browser end-to-end verification. M06 should clarify whether Jira requires ending the set or whole session and align the frontend with the agreed specification if necessary.

## 2. Automated test cases

Each parameter row below is a distinct test case. Preconditions: fresh FSM or isolated history unless specified; no physical camera required. Steps: invoke the named test with listed input and compare the assertions. PASS = actually executed successfully; BLOCKED = not executed due to missing dependencies. N = normal, E = edge, X = exception. Test files are under `tests/`.

| ID | Type | Input / steps | Expected | Actual / status | Pytest function |
|---|---|---|---|---|---|
| D01 | E | 170,145,89,120,160 | 1 rep | 1 / PASS | `test_rep_counter.py::test_scrum24_depth_boundary` |
| D02 | E | 170,145,90,120,160 | 1 rep | 1 / PASS | same |
| D03 | E | 170,145,91,120,160 | 0 reps | 0 / PASS | same |
| D04 | X | angle -1 | ValueError; count 0 | as expected / PASS | `test_scrum24_invalid_angle` |
| D05 | X | angle 181 | ValueError; count 0 | as expected / PASS | same |
| D06 | X | angle NaN | ValueError; count 0 | as expected / PASS | same |
| C01 | X | None,None,90,120,160; then 145,90,120,160 | no false rep; next complete attempt counts 1 | as expected / PASS | `test_scrum24_camera_absent_at_start` |
| X01 | E | wrists distance 14.9; width 100; y=40 in torso (20,80) | true | true / PASS | `test_gestures.py::test_scrum24_x_distance_boundary` |
| X02 | E | distance 15; same torso | false | false / PASS | same |
| X03 | E | distance 15.1; same torso | false | false / PASS | same |
| X04 | E | wrist y=20 (shoulder boundary) | false | false / PASS | `test_scrum24_x_invalid_geometry` |
| X05 | E | wrist y=80 (hip boundary) | false | false / PASS | same |
| X06 | X | body width=0 | false | false / PASS | same |
| X07 | X | 2 detected frames; lose head; then 3 detected frames; repeat | reset; trigger once; remain locked | as expected / PASS | `test_scrum24_x_head_loss_and_single_trigger` |
| S01 | N | rate 0% today | streak 0 | 0 / PASS | `test_progress_analytics.py::test_scrum24_streak_threshold` |
| S02 | E | 49% | 0 | 0 / PASS | same |
| S03 | E | 49.99% | 0 | 0 / PASS | same |
| S04 | E | 50% | 1 | 1 / PASS | same |
| S05 | E | 51% | 1 | 1 / PASS | same |
| S06 | N | 100% | 1 | 1 / PASS | same |
| S07 | X | missing rate (None) | 0 | 0 / PASS | same |
| S08 | X | 101% | 0 | 0 / PASS | same |
| S09 | X | -1% | 0 | 0 / PASS | same |
| S10 | E | dates today, duplicate today, yesterday, -3,-4,-5 days, future and invalid; advance reference date | current 2; longest 3; then current 3 and 0 | as expected / PASS | `test_scrum24_streak_consecutive_duplicate_and_gap` |
| S11 | X | empty history; missing date/rate | all streak values zero/false | as expected / PASS | `test_scrum24_streak_empty_and_missing_data` |
| S12 | E | abandoned session 50% | current 1 | 1 / PASS | `test_scrum24_streak_partial_session_qualifies` |
| S13 | E | router stats, completed 49% with stale true flag, then abandoned 50% | current 0 then 1 | as expected / PASS | `test_scrum24_stats_reads_qualifying_history` |
| S14 | E | record_workout 49 then 50% | stats 0 then 1 | not run / BLOCKED | `test_backend_api.py::test_scrum24_stats_uses_rate_not_completed_status` |
| S15 | E | submit evaluation 49%, RPE7, no auto-apply | stored 49%, streak 0 | not run / BLOCKED | `test_scrum24_evaluation_keeps_actual_rate` |
| G01 | E | A(1,0),B(0,0),C(2,0) | 0° | not run / BLOCKED | `test_pose_angles.py::test_scrum24_joint_geometry` |
| G02 | N | A(1,0),B(0,0),C(1,1) | 45° | not run / BLOCKED | same |
| G03 | N | A(1,0),B(0,0),C(-1,1) | 135° | not run / BLOCKED | same |

Existing regression coverage retained: `test_tracking_loss_discards_partial_rep_and_preserves_total`, `test_incomplete_reps`, `test_stop_gesture`, `test_timed_x_hold_triggers_at_1500_ms`, `test_timed_x_hold_preserves_short_gap_and_resets_long_gap`, `test_reset_after_stop`, `test_coincident_points`, `test_tracking_loss_and_explicit_pause_require_a_fresh_attempt`, `test_fastapi_voice_events_use_completed_attempts_and_tracking_grace`. The latter geometry/API files were blocked in this environment.

## 3. Manual webcam test cases (NOT RUN)

Preconditions: launch `python run_server.py`; visit localhost:8000; sign in if needed, allow webcam, select squat in AI mode, start a set. Save screenshots or video and record actual result before marking PASS.

| ID | Steps | Expected | Actual / status |
|---|---|---|---|
| M01 | Perform one valid squat; cover camera during next descent; uncover while low and return upright; perform fresh complete squat | first count preserved; interrupted attempt not counted; fresh rep increments once | NOT RUN |
| M02 | Cover camera completely, then leave and re-enter frame | tracking warning/pause; no phantom rep; recover when upright | NOT RUN |
| M03 | Perform shallow squat, then a full squat within comfortable range | shallow does not count; appropriate feedback; full squat counts | NOT RUN |
| M04 | Hold X less than 1.5 s, release; hold X >= 1.5 s while active | no early trigger; one stop/transition; no duplicate rep after stop | NOT RUN; confirm set vs entire session with M06 |
| M05 | Attempt X with wrist/head occlusion or outside active set | no unintended stop | NOT RUN; browser may differ from Python |
| M06 | Finish manual sessions below 50% and at 50%; inspect Progress | first does not qualify; second qualifies once for that day | NOT RUN |

## 4. Execution evidence

Environment: Python 3.13, pytest available; Streamlit and MediaPipe absent. Dependency installation attempted but DNS/network unavailable. No mocks were used to bypass these collection errors in the regression run.

| Run | Result |
|---|---|
| Full baseline `python -m pytest -q` | 8 collection errors (7 Streamlit, 1 MediaPipe) |
| Baseline available subset | 111 passed, 94 subtests passed |
| Updated available subset | 138 passed, 94 subtests passed |
| Updated targeted three modules (rep, gesture, progress) | 55 passed, 4 subtests passed |
| Full updated `python -m pytest -q` | same 8 collection errors |
| New SCRUM-24 cases | 27 PASS, 5 BLOCKED; manual 0/6 run |

To reproduce on Windows PowerShell in repository root (activate project environment first):

```powershell
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pytest -v -k scrum24
python -m pytest -q
```

The available-subset run excludes only the eight collection-blocked files:

```powershell
python -m pytest -q --ignore=tests/test_backend_api.py --ignore=tests/test_fitsense_ui.py --ignore=tests/test_planner_fitai.py --ignore=tests/test_pose_angles.py --ignore=tests/test_pose_handoff.py --ignore=tests/test_scrum_19_hud.py --ignore=tests/test_session_fsm.py --ignore=tests/test_session_handoff.py
```

## 5. DoD and open issues

- Detailed Test Cases: complete. Automated tests: added to existing files, no existing tests deleted. Available regression: PASS.
- Full Python regression, blocked geometry/API cases and actual webcam: pending; **DoD is not yet fully verified**. Run on a machine with project dependencies and webcam. If full suite reports failures, distinguish existing failures from regressions; do not weaken assertions solely to pass.
- M06 review: confirm 50% rule aggregation and X behavior mismatch; existing browser detection is not verified by Python tests. Existing global in-memory history, capybara imported flag and legacy Streamlit state are not redesigned in this task.
