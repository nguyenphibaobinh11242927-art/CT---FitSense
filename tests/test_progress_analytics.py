"""Unit tests for SCRUM-21: Pandas progress analytics, timeframe filtering, and PRs."""
from datetime import date, timedelta
import unittest
import pytest

from src.progress_analytics import build_progress_analytics, compute_personal_records, compute_streak


class TestProgressAnalytics(unittest.TestCase):
    def setUp(self):
        self.ref_date = date(2026, 11, 19)
        self.sample_history = [
            {
                "id": "w-01",
                "exercise_id": "squat",
                "exercise_name": "Squat thể dục",
                "actual_date": self.ref_date.isoformat(),
                "reps": 25,
                "duration_sec": 120,
                "rpe": 6,
            },
            {
                "id": "w-02",
                "exercise_id": "plank",
                "exercise_name": "Plank khuỷu tay",
                "actual_date": (self.ref_date - timedelta(days=2)).isoformat(),
                "reps": 0,
                "duration_sec": 75,
                "rpe": 7,
            },
            {
                "id": "w-03",
                "exercise_id": "push_up",
                "exercise_name": "Hít đất chuẩn",
                "actual_date": (self.ref_date - timedelta(days=15)).isoformat(),
                "reps": 18,
                "duration_sec": 90,
                "rpe": 8,
            },
            {
                "id": "w-04",
                "exercise_id": "plank",
                "exercise_name": "Plank khuỷu tay",
                "actual_date": (self.ref_date - timedelta(days=45)).isoformat(),
                "reps": 0,
                "duration_sec": 45,
                "rpe": 6,
            },
        ]

    def test_empty_history_returns_safe_defaults(self):
        res = build_progress_analytics([], timeframe="week", reference_date=self.ref_date)
        self.assertEqual(res["labels"], [])
        self.assertEqual(res["reps_series"], [])
        self.assertEqual(res["plank_series"], [])
        self.assertEqual(res["summary"]["total_sessions"], 0)
        self.assertEqual(res["personal_records"]["Plank Tĩnh"], "Chưa ghi nhận")

    def test_compute_personal_records_reps_and_plank(self):
        prs = compute_personal_records(self.sample_history)
        self.assertEqual(prs["Squat Thể dục"], "25 reps")
        self.assertEqual(prs["Standard Push-up"], "18 reps")
        self.assertEqual(prs["Plank Tĩnh"], "1p 15s")
        self.assertEqual(prs["Dips trên ghế"], "Chưa ghi nhận")

    def test_timeframe_filtering_week_month_all(self):
        week_res = build_progress_analytics(self.sample_history, timeframe="week", reference_date=self.ref_date)
        month_res = build_progress_analytics(self.sample_history, timeframe="month", reference_date=self.ref_date)
        all_res = build_progress_analytics(self.sample_history, timeframe="all", reference_date=self.ref_date)

        # Week (7 days): w-01 and w-02
        self.assertEqual(week_res["summary"]["total_sessions"], 2)
        self.assertEqual(week_res["summary"]["total_reps"], 25)
        self.assertEqual(week_res["summary"]["best_plank_sec"], 75)

        # Month (30 days): w-01, w-02, w-03
        self.assertEqual(month_res["summary"]["total_sessions"], 3)
        self.assertEqual(month_res["summary"]["total_reps"], 43)

        # All: all 4 records
        self.assertEqual(all_res["summary"]["total_sessions"], 4)

    def test_missing_optional_columns_do_not_raise(self):
        # Records completely missing reps, duration_sec, rpe, and actual_date
        minimal_history = [
            {"id": "m-01", "exercise_id": "squat", "exercise_name": "Squat"},
        ]
        res = build_progress_analytics(minimal_history, timeframe="all", reference_date=self.ref_date)
        self.assertEqual(res["summary"]["total_sessions"], 0)
        self.assertEqual(res["summary"]["invalid_date_records"], 1)
        self.assertEqual(res["personal_records"]["Squat Thể dục"], "Chưa ghi nhận")

        # Record with valid date but missing reps, duration_sec, rpe
        valid_date_minimal = [
            {"id": "m-02", "exercise_id": "squat", "actual_date": self.ref_date.isoformat()},
        ]
        res2 = build_progress_analytics(valid_date_minimal, timeframe="week", reference_date=self.ref_date)
        self.assertEqual(res2["summary"]["total_sessions"], 1)
        self.assertEqual(res2["summary"]["total_reps"], 0)
        self.assertEqual(res2["summary"]["avg_rpe"], 7.0)

    def test_invalid_dates_are_excluded_not_coerced_to_today(self):
        history = [
            {
                "id": "bad-1",
                "exercise_id": "squat",
                "actual_date": "not-a-valid-date",
                "reps": 30,
                "duration_sec": 60,
            },
            {
                "id": "bad-2",
                "exercise_id": "plank",
                "actual_date": None,
                "reps": 0,
                "duration_sec": 90,
            },
        ]
        res = build_progress_analytics(history, timeframe="week", reference_date=self.ref_date)
        self.assertEqual(res["labels"], [])
        self.assertEqual(res["summary"]["total_sessions"], 0)
        self.assertEqual(res["summary"]["total_reps"], 0)
        self.assertEqual(res["summary"]["invalid_date_records"], 2)

    def test_future_dates_are_excluded_from_completed_history(self):
        future_date = (self.ref_date + timedelta(days=3)).isoformat()
        history = [
            {
                "id": "f-01",
                "exercise_id": "squat",
                "actual_date": future_date,
                "reps": 50,
                "duration_sec": 120,
            },
            {
                "id": "p-01",
                "exercise_id": "squat",
                "actual_date": self.ref_date.isoformat(),
                "reps": 20,
                "duration_sec": 60,
            },
        ]
        for tf in ("week", "month", "all"):
            res = build_progress_analytics(history, timeframe=tf, reference_date=self.ref_date)
            self.assertEqual(res["summary"]["total_sessions"], 1)
            self.assertEqual(res["summary"]["total_reps"], 20)
            self.assertEqual(res["labels"], [self.ref_date.strftime("%d/%m")])

    def test_multiple_exercises_in_same_session_counted_once(self):
        history = [
            {
                "id": "w-10",
                "session_id": "sess-001",
                "exercise_id": "squat",
                "actual_date": self.ref_date.isoformat(),
                "reps": 20,
                "duration_sec": 90,
            },
            {
                "id": "w-11",
                "session_id": "sess-001",
                "exercise_id": "push_up",
                "actual_date": self.ref_date.isoformat(),
                "reps": 15,
                "duration_sec": 60,
            },
            {
                "id": "w-12",
                "session_id": "sess-002",
                "exercise_id": "plank",
                "actual_date": self.ref_date.isoformat(),
                "reps": 0,
                "duration_sec": 80,
            },
        ]
        res = build_progress_analytics(history, timeframe="week", reference_date=self.ref_date)
        # 3 exercise records, but only 2 distinct sessions (sess-001 and sess-002)
        self.assertEqual(res["summary"]["total_sessions"], 2)
        self.assertEqual(res["summary"]["total_reps"], 35)

    def test_same_day_multiple_records_aggregate_reps_and_max_plank(self):
        day_str = self.ref_date.isoformat()
        history = [
            {"id": "d-1", "exercise_id": "squat", "actual_date": day_str, "reps": 15, "duration_sec": 60},
            {"id": "d-2", "exercise_id": "push_up", "actual_date": day_str, "reps": 12, "duration_sec": 45},
            {"id": "d-3", "exercise_id": "plank", "actual_date": day_str, "reps": 0, "duration_sec": 50},
            {"id": "d-4", "exercise_id": "plank", "actual_date": day_str, "reps": 0, "duration_sec": 85},
        ]
        res = build_progress_analytics(history, timeframe="week", reference_date=self.ref_date)
        self.assertEqual(res["labels"], [self.ref_date.strftime("%d/%m")])
        self.assertEqual(res["reps_series"], [27])      # 15 + 12
        self.assertEqual(res["plank_series"], [85])     # max(50, 85)
        self.assertEqual(res["summary"]["best_plank_sec"], 85)

    def test_personal_records_ignore_invalid_and_future_dates(self):
        future_date = (self.ref_date + timedelta(days=5)).isoformat()
        history = [
            {
                "id": "valid-1",
                "exercise_id": "squat",
                "actual_date": self.ref_date.isoformat(),
                "reps": 20,
                "duration_sec": 60,
            },
            {
                "id": "future-1",
                "exercise_id": "squat",
                "actual_date": future_date,
                "reps": 99,
                "duration_sec": 120,
            },
            {
                "id": "invalid-1",
                "exercise_id": "plank",
                "actual_date": "invalid-date",
                "reps": 0,
                "duration_sec": 300,
            },
        ]
        res = build_progress_analytics(history, timeframe="week", reference_date=self.ref_date)
        self.assertEqual(res["personal_records"]["Squat Thể dục"], "20 reps")
        self.assertEqual(res["personal_records"]["Plank Tĩnh"], "Chưa ghi nhận")

    def test_personal_records_span_all_valid_history_regardless_of_timeframe(self):
    # Record from 45 days ago should still count toward PRs even when timeframe="week"
        res_week = build_progress_analytics(self.sample_history, timeframe="week", reference_date=self.ref_date)
        self.assertEqual(res_week["personal_records"]["Standard Push-up"], "18 reps")
        self.assertEqual(res_week["personal_records"]["Plank Tĩnh"], "1p 15s")





@pytest.mark.parametrize("rate, expected", [(0, 0), (49, 0), (49.99, 0), (50, 1), (51, 1), (100, 1), (None, 0), (101, 0), (-1, 0)])
def test_scrum24_streak_threshold(rate, expected):
    today = date(2026, 11, 19)
    result = compute_streak([{"actual_date": today.isoformat(), "completion_rate": rate}], today)
    assert result == {"current_streak_days": expected, "longest_streak_days": expected,
                      "has_worked_out_today": bool(expected)}


def test_scrum24_streak_consecutive_duplicate_and_gap():
    today = date(2026, 11, 19)
    history = [{"actual_date": (today - timedelta(days=n)).isoformat(), "completion_rate": 50}
               for n in (0, 0, 1, 3, 4, 5, -1)]
    history.append({"actual_date": "invalid", "completion_rate": 100})
    assert compute_streak(history, today) == {"current_streak_days": 2, "longest_streak_days": 3,
                                              "has_worked_out_today": True}
    assert compute_streak(history, today + timedelta(days=1))["current_streak_days"] == 3
    assert compute_streak(history, today + timedelta(days=3))["current_streak_days"] == 0


def test_scrum24_streak_empty_and_missing_data():
    today = date(2026, 11, 19)
    assert compute_streak([{}, {"actual_date": today.isoformat()}], today) == compute_streak([], today)


def test_scrum24_streak_partial_session_qualifies():
    today = date(2026, 11, 19)
    assert compute_streak([{"actual_date": today.isoformat(), "completion_rate": 50, "status": "abandoned"}], today)["current_streak_days"] == 1



def test_scrum24_stats_reads_qualifying_history(monkeypatch):
    from backend.routers import progress
    today = date.today().isoformat()
    history = [{"actual_date": today, "completion_rate": 49, "status": "completed"}]
    monkeypatch.setattr(progress, "WORKOUT_HISTORY", history)
    monkeypatch.setattr(progress, "HAS_WORKED_OUT_TODAY", True)
    assert progress.get_stats()["current_streak_days"] == 0
    history.append({"actual_date": today, "completion_rate": 50, "status": "abandoned"})
    assert progress.get_stats()["current_streak_days"] == 1


if __name__ == "__main__":
    unittest.main()
