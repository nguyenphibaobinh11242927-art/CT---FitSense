"""Comprehensive Unit Tests for FitSense REST API (FastAPI Backend)."""

import unittest
from fastapi.testclient import TestClient
from backend.main import app


class TestBackendAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "online")
        self.assertIn("FitSense", data["platform"])

    def test_auth_me_and_login(self):
        import uuid
        unique_email = f"user_{uuid.uuid4().hex[:8]}@fitsense.vn"

        # Initial state: not logged in (no demo user pre-created)
        self.client.post("/api/auth/logout")
        res = self.client.get("/api/auth/me")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["is_logged_in"])
        self.assertIsNone(data["user"])

        # Register a new user
        reg_payload = {
            "name": "Vận Động Viên Mới",
            "email": unique_email,
            "password": "Password123",
            "height_cm": 172.0,
            "weight_kg": 66.0,
        }
        res_reg = self.client.post("/api/auth/register", json=reg_payload)
        self.assertEqual(res_reg.status_code, 200)
        self.assertTrue(res_reg.json()["success"])

        # Me check after register
        res_me = self.client.get("/api/auth/me")
        self.assertTrue(res_me.json()["is_logged_in"])
        self.assertEqual(res_me.json()["user"]["email"], unique_email)

        # Login existing user
        res_login = self.client.post("/api/auth/login", json={"email": unique_email, "password": "Password123"})
        self.assertEqual(res_login.status_code, 200)
        self.assertTrue(res_login.json()["success"])

        # Test Auth Config
        res_cfg = self.client.get("/api/auth/config")
        self.assertEqual(res_cfg.status_code, 200)
        self.assertIn("google_client_id", res_cfg.json())

        # Test Google Auth - existing user
        res_g_exist = self.client.post("/api/auth/google", json={"email": unique_email, "name": "Google User"})
        self.assertEqual(res_g_exist.status_code, 200)
        self.assertFalse(res_g_exist.json()["is_new_user"])

        # Test Google Auth - brand new user
        new_g_email = f"googler_{uuid.uuid4().hex[:8]}@gmail.com"
        res_g_new = self.client.post("/api/auth/google", json={"email": new_g_email, "name": "Google Newbie"})
        self.assertEqual(res_g_new.status_code, 200)
        self.assertTrue(res_g_new.json()["is_new_user"])
        self.assertIn("google_data", res_g_new.json())

        # Complete Google registration onboarding
        res_g_complete = self.client.post("/api/auth/google/complete-registration", json={
            "email": new_g_email,
            "name": "Google Newbie",
            "height_cm": 175.0,
            "weight_kg": 68.0,
            "age": 23,
            "gender": "Nam",
            "goal": "Tăng cơ & Sức mạnh",
            "fitness_level": "Beginner (Người mới bắt đầu)",
            "environment": "Tại nhà (Home Workout)",
            "restrictions": ["Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)"],
            "equipment": ["Không có dụng cụ (Chỉ tập Bodyweight)"],
        })
        self.assertEqual(res_g_complete.status_code, 200)
        self.assertTrue(res_g_complete.json()["success"])

        # Logout
        res_logout = self.client.post("/api/auth/logout")
        self.assertEqual(res_logout.status_code, 200)
        self.assertTrue(res_logout.json()["success"])

    def test_profile_bmi_calculation(self):
        res = self.client.post("/api/profile/bmi", json={"weight_kg": 65.0, "height_cm": 170.0})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertAlmostEqual(data["bmi"], 22.5, places=1)
        self.assertEqual(data["category"], "Cân đối lý tưởng")
        self.assertTrue(data["healthy_weight_min"] > 50)

    def test_profile_get_and_update(self):
        # Login test user
        self.client.post("/api/auth/login", json={"email": "athlete@fitsense.vn", "password": "Password123"})
        res = self.client.get("/api/profile")
        self.assertEqual(res.status_code, 200)
        profile = res.json()
        self.assertIsNotNone(profile)
        self.assertIn("weight_kg", profile)

        profile_update = {
            "name": "Nguyễn Văn A",
            "email": "athlete@fitsense.vn",
            "age": 24,
            "gender": "Nam",
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "days_per_week": 4,
            "session_duration_minutes": 45,
            "goal": "Tăng cơ & Sức mạnh",
            "fitness_level": "Intermediate (Đã có nền tảng)",
            "environment": "Tại nhà (Home Workout)",
            "restrictions": ["Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)"],
            "equipment": ["Không có dụng cụ (Chỉ tập Bodyweight)"],
        }
        res_update = self.client.put("/api/profile", json=profile_update)
        self.assertEqual(res_update.status_code, 200)
        self.assertTrue(res_update.json()["success"])

    def test_exercises_endpoints(self):
        res_meta = self.client.get("/api/exercises/meta")
        self.assertEqual(res_meta.status_code, 200)
        meta = res_meta.json()
        self.assertIn("muscles", meta)
        self.assertIn("levels", meta)
        self.assertTrue(meta["total_exercises"] >= 28)

        # Detail with anatomical SVG
        res_detail = self.client.get("/api/exercises/squat")
        self.assertEqual(res_detail.status_code, 200)
        detail = res_detail.json()
        self.assertIn("muscle_svg", detail)
        self.assertIn("<svg", detail["muscle_svg"])

        # Raw SVG endpoint
        res_svg = self.client.get("/api/exercises/squat/svg")
        self.assertEqual(res_svg.status_code, 200)
        self.assertIn("image/svg+xml", res_svg.headers.get("content-type", ""))

        # Filtering tests: single muscle, multi-muscle, and no equipment
        res_hip = self.client.get("/api/exercises?muscle=hip_flexors")
        self.assertEqual(res_hip.status_code, 200)
        hip_data = res_hip.json()
        self.assertEqual(hip_data["count"], 2)
        hip_ids = [x["id"] for x in hip_data["exercises"]]
        self.assertIn("dead_bug", hip_ids)
        self.assertIn("march_in_place", hip_ids)

        res_multi = self.client.get("/api/exercises?muscle=chest,shoulders")
        self.assertEqual(res_multi.status_code, 200)
        self.assertTrue(res_multi.json()["count"] > 2)

        res_none_equip = self.client.get("/api/exercises?equipment=__none__")
        self.assertEqual(res_none_equip.status_code, 200)
        self.assertTrue(all(len(x.get("equipment", [])) == 0 for x in res_none_equip.json()["exercises"]))

    def test_planner_endpoints(self):
        res_week = self.client.get("/api/planner/week")
        self.assertEqual(res_week.status_code, 200)
        data = res_week.json()
        self.assertEqual(len(data["schedule"]), 7)
        self.assertIn("today_name", data)

        res_gen = self.client.post("/api/planner/generate", json={"goal": "Sức bền", "use_ai": True})
        self.assertEqual(res_gen.status_code, 200)
        self.assertTrue(res_gen.json()["success"])

        res_reset = self.client.post("/api/planner/reset")
        self.assertEqual(res_reset.status_code, 200)
        self.assertEqual(len(res_reset.json()["schedule"]), 7)

        # Download sample template
        res_tmpl = self.client.get("/api/planner/template")
        self.assertEqual(res_tmpl.status_code, 200)
        self.assertIn("template", res_tmpl.json())

        # Update single day
        res_update_day = self.client.post("/api/planner/update-day", json={
            "day": "Thứ 2",
            "focus": "Thử nghiệm Thân trên Cá nhân",
            "is_rest": False,
            "exercises": [
                {"name": "Custom Pushup", "sets": 4, "reps": "15", "rest_sec": 45, "primary_muscle": "Ngực"}
            ],
        })
        self.assertEqual(res_update_day.status_code, 200)
        self.assertTrue(res_update_day.json()["success"])

        # Check recovery warnings
        res_rec = self.client.get("/api/planner/check-recovery/Thứ 2")
        self.assertEqual(res_rec.status_code, 200)
        self.assertIn("has_warnings", res_rec.json())

        # Start workout with out-of-order day (triggers AI rescheduling)
        res_start_day = self.client.post("/api/planner/start-day-workout", json={
            "source_day": "Thứ 5",
            "use_ai": True,
        })
        self.assertEqual(res_start_day.status_code, 200)
        data_day = res_start_day.json()
        self.assertTrue(data_day["success"])
        self.assertIn("schedule", data_day)
        self.assertIn("active_workout", data_day)
        self.assertIn("replan_method", data_day)

    def test_profile_update_and_auto_realign_restrictions(self):
        # Reset schedule first to ensure standard baseline with squat
        self.client.post("/api/planner/reset")
        
        # Update profile with knee joint restriction
        res_prof = self.client.put("/api/profile", json={
            "name": "Knee Care Athlete",
            "email": "knee_user@fitsense.vn",
            "age": 25,
            "gender": "Nam",
            "height_cm": 172.0,
            "weight_kg": 68.0,
            "days_per_week": 4,
            "session_duration_minutes": 45,
            "goal": "Tăng cơ & Sức mạnh",
            "fitness_level": "Beginner (Người mới bắt đầu)",
            "environment": "Tại nhà (Home Workout)",
            "restrictions": ["Khớp gối yếu (Tránh Squat quá sâu, Jumping)"],
            "equipment": ["Không có dụng cụ (Chỉ tập Bodyweight)"],
        })
        self.assertEqual(res_prof.status_code, 200)
        prof_data = res_prof.json()
        self.assertTrue(prof_data["success"])
        self.assertTrue(prof_data["schedule_updated"])
        self.assertTrue(len(prof_data["schedule_changes"]) > 0)

        # Verify that squat in schedule was replaced with a knee-safe exercise
        res_sched = self.client.get("/api/planner/week")
        self.assertEqual(res_sched.status_code, 200)
        all_exercises = [ex for d in res_sched.json()["schedule"] for ex in d.get("exercises", [])]
        ex_ids = [ex.get("id") for ex in all_exercises]
        self.assertNotIn("squat", ex_ids)

    def test_workout_session_and_fsm(self):
        res_start = self.client.post("/api/session/start", json={"exercise_id": "squat", "target_reps": 12})
        self.assertEqual(res_start.status_code, 200)
        data = res_start.json()
        self.assertTrue(data["success"])
        session_id = data["session_id"]

        # Step 1: Up
        res_up = self.client.post("/api/session/fsm-rep", json={"session_id": session_id, "angle": 170.0})
        self.assertEqual(res_up.json()["state"], "STATE_UP")

        # Step 2: Going down (< 150)
        res_going_down = self.client.post("/api/session/fsm-rep", json={"session_id": session_id, "angle": 130.0})
        self.assertEqual(res_going_down.json()["state"], "STATE_GOING_DOWN")

        # Step 3: Bottom squat (<= 90)
        res_down = self.client.post("/api/session/fsm-rep", json={"session_id": session_id, "angle": 85.0})
        self.assertEqual(res_down.json()["state"], "STATE_DOWN")

        # Step 4: Going up (> 105)
        res_going_up = self.client.post("/api/session/fsm-rep", json={"session_id": session_id, "angle": 120.0})
        self.assertEqual(res_going_up.json()["state"], "STATE_GOING_UP")

        # Step 5: Stand back up (>= 160) -> Rep completes!
        res_finish_rep = self.client.post("/api/session/fsm-rep", json={"session_id": session_id, "angle": 165.0})
        self.assertTrue(res_finish_rep.json()["rep_incremented"])
        self.assertEqual(res_finish_rep.json()["rep_count"], 1)

        res_finish = self.client.post("/api/session/finish", json={
            "session_id": session_id,
            "exercise_id": "squat",
            "completed_reps": 10,
            "duration_seconds": 180,
            "rpe": 8,
            "feedback_notes": "Tập luyện AI rất chuẩn xác",
        })
        self.assertEqual(res_finish.status_code, 200)
        self.assertTrue(res_finish.json()["success"])

    def test_progress_and_heatmap(self):
        res_stats = self.client.get("/api/progress/stats")
        self.assertEqual(res_stats.status_code, 200)
        stats = res_stats.json()
        self.assertIn("total_workouts", stats)
        self.assertIn("current_streak_days", stats)
        self.assertIn("personal_records", stats)
        self.assertIn("weekly_volume", stats)

        res_heat = self.client.get("/api/progress/heatmap")
        self.assertEqual(res_heat.status_code, 200)
        self.assertIn("muscles", res_heat.json())
        self.assertTrue(len(res_heat.json()["muscles"]) >= 5)

        # Test evaluation meta & submission
        res_meta = self.client.get("/api/progress/evaluation-meta")
        self.assertEqual(res_meta.status_code, 200)
        self.assertIn("rpe_descriptions", res_meta.json())

        # Overload strategy test
        res_eval_overload = self.client.post("/api/progress/evaluate", json={
            "completion_rate": 95,
            "rpe": 5,
            "soreness": ["Cơ đùi trước (Quads)"],
            "note": "Rất sung sức!",
            "auto_apply": True,
        })
        self.assertEqual(res_eval_overload.status_code, 200)
        data_overload = res_eval_overload.json()["evaluation"]
        self.assertEqual(data_overload["recommendation"]["strategy"], "overload")

        # Deload strategy test
        res_eval_deload = self.client.post("/api/progress/evaluate", json={
            "completion_rate": 60,
            "rpe": 9,
            "soreness": ["Khớp gối", "Cổ tay"],
            "note": "Khá mỏi cơ và đau khớp",
            "auto_apply": True,
        })
        self.assertEqual(res_eval_deload.status_code, 200)
        data_deload = res_eval_deload.json()["evaluation"]
        self.assertEqual(data_deload["recommendation"]["strategy"], "deload")

    def test_capybara_status(self):
        res = self.client.get("/api/capybara/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("mood", data)
        self.assertIn("quote", data)
        self.assertIn("<svg", data["svg"])


if __name__ == "__main__":
    unittest.main()
