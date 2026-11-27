"""Comprehensive Unit Tests for FitSense REST API (FastAPI Backend)."""

import unittest
import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.routers import planner, progress, session
from src.school_ai import FitAIServiceError


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
        with patch("backend.routers.auth.verify_google_credential", return_value={
            "email": unique_email,
            "name": "Google User",
            "avatar_url": None,
            "google_id": "google-user-existing",
        }):
            res_g_exist = self.client.post("/api/auth/google", json={"credential": "verified-test-token"})
        self.assertEqual(res_g_exist.status_code, 200)
        self.assertFalse(res_g_exist.json()["is_new_user"])

        # Test Google Auth - brand new user
        new_g_email = f"googler_{uuid.uuid4().hex[:8]}@gmail.com"
        google_identity = {
            "email": new_g_email,
            "name": "Google Newbie",
            "avatar_url": None,
            "google_id": "google-user-new",
        }
        with patch("backend.routers.auth.verify_google_credential", return_value=google_identity):
            res_g_new = self.client.post("/api/auth/google", json={"credential": "verified-test-token"})
        self.assertEqual(res_g_new.status_code, 200)
        self.assertTrue(res_g_new.json()["is_new_user"])
        self.assertIn("google_data", res_g_new.json())

        # Complete Google registration onboarding
        with patch("backend.routers.auth.verify_google_credential", return_value=google_identity):
            res_g_complete = self.client.post("/api/auth/google/complete-registration", json={
                "credential": "verified-test-token",
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

    def test_fastapi_plan_preserves_saved_schedule_on_error_and_keeps_catalog_ids(self):
        email = "planner-audit@example.invalid"
        saved = [{"day": "Thứ 2", "focus": "Lịch đã lưu", "exercises": []}]
        profile = {
            "goal": "Sức bền & Tim mạch", "fitness_level": "Beginner",
            "restrictions": ["Khớp gối yếu"], "equipment": [],
        }
        candidate = {
            "exercise_id": "wall_push_up", "sets": 2, "reps": 8, "hold_seconds": 3, "rest_seconds": 0,
            "alternative": {"exercise_id": "push_up", "sets": 1, "reps": 5, "hold_seconds": 2, "rest_seconds": 30},
        }
        output = {"goal": "endurance", "days": [
            {"day": day, "exercises": [candidate, candidate] if day == 1 else []}
            for day in range(1, 8)
        ]}
        with (
            patch.dict(planner.CURRENT_SESSION, {"user_email": email}),
            patch.dict(planner.USER_SCHEDULES, {email: saved}),
            patch.object(planner, "load_profile", return_value=profile),
            patch.object(planner, "complete_with_school_ai", side_effect=[
                FitAIServiceError("FIT-AI mất kết nối"), "{}", json.dumps(output),
            ]),
        ):
            for status in (503, 422):
                rejected = self.client.post("/api/planner/generate", json={})
                self.assertEqual(rejected.status_code, status)
                self.assertIs(planner.USER_SCHEDULES[email], saved)
            generated = self.client.post("/api/planner/generate", json={})
            self.assertEqual(generated.status_code, 200, generated.text)
            exercise = generated.json()["schedule"][0]["exercises"][0]
            self.assertEqual((exercise["id"], exercise["hold_seconds"], exercise["rest_sec"]), ("wall_push_up", 3, 0))
            self.assertEqual(exercise["ai_alternative"]["id"], "push_up")
            self.assertEqual(self.client.get("/api/planner/week").json()["schedule"][0]["exercises"][1]["id"],
                             "wall_push_up")

            swap = {"day": "Thứ 2", "current_exercise_id": "wall_push_up", "exercise_index": 1}
            for excluded in ("squat", "incline_push_up"):
                response = self.client.post("/api/planner/swap", json={**swap, "new_exercise_id": excluded})
                self.assertEqual(response.status_code, 422, response.text)
            response = self.client.post("/api/planner/swap", json={**swap, "new_exercise_id": "push_up"})
            self.assertEqual(response.status_code, 200, response.text)
            first, second = response.json()["day"]["exercises"]
            self.assertEqual(first["id"], "wall_push_up")
            self.assertEqual((second["id"], second["sets"], second["hold_seconds"]), ("push_up", 1, 2))

    def test_fastapi_voice_events_use_completed_attempts_and_tracking_grace(self):
        with patch.dict(session.ACTIVE_SESSIONS, {}, clear=True):
            session_id = self.client.post("/api/session/start", json={"exercise_id": "squat"}).json()["session_id"]

            def frame(angle, **extra):
                response = self.client.post("/api/session/fsm-rep", json={"session_id": session_id, "angle": angle, **extra})
                self.assertEqual(response.status_code, 200, response.text)
                return response.json()

            frame(145)
            self.assertIsNone(frame(130)["voice_event"])
            self.assertFalse(frame(None)["tracking_lost"])
            self.assertFalse(frame(None)["tracking_lost"])
            self.assertEqual(frame(165)["voice_event"], {"kind": "shallow_squat"})
            self.assertIsNone(frame(170)["voice_event"])
            for angle in (145, 130):
                frame(angle)
            self.assertTrue(frame(None, tracking_interrupted=True)["tracking_lost"])
            self.assertIsNone(frame(165)["voice_event"])
            for angle in (145, 90, 120):
                frame(angle)
            self.assertEqual(frame(165)["voice_event"], {"kind": "rep", "count": 1})

    def test_rep_feedback_resets_for_new_sets_and_obeys_the_current_exercise(self):
        with patch.dict(session.ACTIVE_SESSIONS, {}, clear=True):
            start = self.client.post("/api/session/start", json={"exercise_id": "squat", "total_sets": 2})
            session_id = start.json()["session_id"]

            def frame(angle, current_set):
                return self.client.post("/api/session/fsm-rep", json={
                    "session_id": session_id, "angle": angle, "current_set": current_set,
                })

            for current_set in (1, 2):
                for angle in (170, 145, 90, 120, 165):
                    response = frame(angle, current_set)
                    self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["voice_event"], {"kind": "rep", "count": 1})
            self.assertEqual(frame(145, 1).status_code, 409)

            for exercise_id, cue in (("push_up", None), ("squat", {"kind": "shallow_squat"})):
                switched = self.client.post("/api/session/switch-exercise", json={
                    "session_id": session_id, "exercise_id": exercise_id,
                })
                self.assertEqual(switched.status_code, 200, switched.text)
                for angle in (170, 145, 130, 165):
                    response = frame(angle, 1)
                self.assertEqual(response.json()["voice_event"], cue)

    def test_ai_workout_summary_uses_all_sets_and_saves_once(self):
        with (
            patch.dict(session.ACTIVE_SESSIONS, {}, clear=True),
            patch.object(progress, "WORKOUT_HISTORY", []),
            patch.object(progress, "HAS_WORKED_OUT_TODAY", False),
        ):
            start = self.client.post("/api/session/start", json={
                "exercise_id": "squat", "target_reps": 12, "total_sets": 2,
            })
            session_id = start.json()["session_id"]
            frame_id = 0
            for current_set in (1, 2):
                for _ in range(12):
                    for angle in (170, 145, 90, 120, 165):
                        frame_id += 1
                        frame = self.client.post("/api/session/fsm-rep", json={
                            "session_id": session_id, "angle": angle, "current_set": current_set,
                            "exercise_index": 0, "frame_id": frame_id,
                        })
                        self.assertEqual(frame.status_code, 200, frame.text)
                self.assertEqual(frame.json()["rep_count"], 12)

            summary = self.client.get(f"/api/session/summary/{session_id}").json()
            self.assertEqual((summary["total_reps"], summary["total_target_reps"]), (24, 24))
            self.assertEqual([entry["reps"] for entry in summary["sets"]], [12, 12])
            finish = {"session_id": session_id, "exercise_id": "squat", "completed_reps": 12, "duration_seconds": 180}
            first = self.client.post("/api/session/finish", json=finish).json()
            self.assertEqual(first["record"]["reps"], 24)
            self.assertEqual(first["record"]["status"], "completed")
            self.assertEqual(first["record"]["mode"], "ai")
            self.assertEqual(self.client.post("/api/session/finish", json=finish).json(), first)
            self.assertEqual(len(progress.WORKOUT_HISTORY), 1)
            self.assertEqual(self.client.post("/api/session/fsm-rep", json={
                "session_id": session_id, "angle": 170,
            }).status_code, 409)

    def test_tracking_loss_and_explicit_pause_require_a_fresh_attempt(self):
        with patch.dict(session.ACTIVE_SESSIONS, {}, clear=True):
            session_id = self.client.post("/api/session/start", json={"exercise_id": "squat"}).json()["session_id"]

            def frame(angle, **extra):
                return self.client.post("/api/session/fsm-rep", json={
                    "session_id": session_id, "angle": angle, **extra,
                })

            for angle in (170, 145, 85, 120):
                self.assertEqual(frame(angle).status_code, 200)
            lost = frame(None, tracking_interrupted=True).json()
            self.assertEqual((lost["status"], lost["rep_count"]), ("paused", 0))
            self.assertEqual(frame(120).json()["status"], "paused")
            restored = frame(170).json()
            self.assertEqual((restored["status"], restored["rep_count"]), ("active", 0))
            self.assertFalse(restored["rep_incremented"])

            for paused in (True, False):
                response = self.client.post("/api/session/pause", json={"session_id": session_id, "paused": paused})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(frame(170).status_code, 409 if paused else 200)
            self.assertEqual(frame(145, frame_id=10).status_code, 200)
            self.assertEqual(frame(85, frame_id=10).status_code, 409)
            for angle in (85, 120):
                frame(angle)
            self.assertEqual(frame(170).json()["rep_count"], 1)

    def test_manual_and_abandoned_workouts_keep_their_own_results(self):
        with (
            patch.dict(session.ACTIVE_SESSIONS, {}, clear=True),
            patch.object(progress, "WORKOUT_HISTORY", []),
            patch.object(progress, "HAS_WORKED_OUT_TODAY", False),
        ):
            ai_id = self.client.post("/api/session/start", json={"exercise_id": "squat"}).json()["session_id"]
            manual_id = self.client.post("/api/session/start", json={"exercise_id": "squat", "mode": "manual"}).json()["session_id"]
            self.assertEqual(self.client.post("/api/session/fsm-rep", json={
                "session_id": manual_id, "angle": 170,
            }).status_code, 409)
            for angle in (170, 145, 85, 120, 170):
                self.client.post("/api/session/fsm-rep", json={"session_id": ai_id, "angle": angle})
            abandoned = self.client.post("/api/session/finish", json={
                "session_id": ai_id, "exercise_id": "squat", "duration_seconds": 20, "outcome": "abandoned",
            }).json()["record"]
            self.assertEqual((abandoned["status"], abandoned["reps"]), ("abandoned", 1))
            self.assertIsNone(abandoned["rpe"])
            self.assertFalse(progress.HAS_WORKED_OUT_TODAY)
            manual = self.client.post("/api/session/finish", json={
                "session_id": manual_id, "exercise_id": "squat", "duration_seconds": 45, "completed_reps": 6,
            }).json()["record"]
            self.assertEqual((manual["status"], manual["mode"], manual["reps"]), ("completed", "manual", 6))
            self.assertEqual(self.client.get("/api/progress/history").json()["history"], [manual, abandoned])

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
        # SCRUM-19: Test default exercises endpoint for HUD & Up Next List
        res_defaults = self.client.get("/api/session/default-exercises")
        self.assertEqual(res_defaults.status_code, 200)
        data_defaults = res_defaults.json()
        self.assertIn("exercises", data_defaults)
        self.assertTrue(len(data_defaults["exercises"]) >= 3)
        self.assertEqual(data_defaults["exercises"][0]["id"], "squat")

        # SCRUM-19: Start session with multi-exercise list & sets tracking
        res_start = self.client.post("/api/session/start", json={
            "exercise_id": "squat",
            "target_reps": 12,
            "total_sets": 3,
            "current_set": 1,
            "exercise_list": data_defaults["exercises"],
        })
        self.assertEqual(res_start.status_code, 200)
        data = res_start.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["current_set"], 1)
        self.assertEqual(data["total_sets"], 3)
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

        # SCRUM-19: Test switch/jump to next exercise
        res_switch = self.client.post("/api/session/switch-exercise", json={
            "session_id": session_id,
            "exercise_id": "pushup",
            "exercise_name": "Chống đẩy (Push-up)",
            "target_reps": 10,
            "current_set": 1,
            "total_sets": 3,
        })
        self.assertEqual(res_switch.status_code, 200)
        self.assertTrue(res_switch.json()["success"])
        self.assertEqual(res_switch.json()["exercise_id"], "pushup")

        res_finish = self.client.post("/api/session/finish", json={
            "session_id": session_id,
            "exercise_id": "pushup",
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
