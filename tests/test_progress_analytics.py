"""Unit tests for SCRUM-21: Pandas progress analytics, timeframe filtering, and PRs."""
from datetime import date, timedelta
import unittest

from src.progress_analytics import build_progress_analytics, compute_personal_records


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


if __name__ == "__main__":
    unittest.main()