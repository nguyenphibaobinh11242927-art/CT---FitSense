"""Unit & Integration Tests for SCRUM-22: Post-Workout Evaluation & Adaptive AI.

Phân hệ CT: D7. Post-Workout Evaluation & Adaptive Deload (Yêu cầu 69 – 71).
Kiểm thử toàn diện:
  1. Tính toán tỉ lệ hoàn thành rho, định dạng nhãn buổi tập kèm thời gian thực.
  2. Thang đo mức độ gắng sức RPE (Borg Scale 1-10) kèm emoji, giá trị mặc định = 5.
  3. Khảo sát mỏi cơ cục bộ DOMS và mức độ hài lòng buổi tập.
  4. Thuật toán Thích ứng Tải trọng 4 bậc theo CT Section 4.4 (Deload -15%, Giảm nhẹ -5%, Duy trì 1.00x, Tăng tiến +10%).
  5. Lời khuyên phục hồi sinh học: Giờ nghỉ cơ bắp (24h/48h), bài tập giãn cơ cool-down và lượng nước bù.
  6. Tự động áp dụng và bảo toàn tính toàn vẹn của Kế hoạch tuần (không sửa buổi quá khứ).
  7. Công thức bảo toàn chuỗi Streak công bằng theo CT Section 4.5 (rho >= 50% hoặc T >= 600s).
  8. Tích hợp Backend REST API (/api/progress/evaluate, /api/progress/evaluations, /api/progress/evaluation-meta).
"""

from copy import deepcopy
import unittest
from fastapi.testclient import TestClient

from backend.main import app
import src.evaluation_view as evaluation_view


class TestScrum22PostWorkoutEvaluation(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_session_label_format_and_ai_completion_rate(self):
        """1. Kiểm tra định dạng nhãn buổi tập có thời gian thực và AI tự tính tỷ lệ rho."""
        record = {
            "session_name": "Thứ 4 - Lưng & Tay trước",
            "mode": "ai",
            "status": "completed",
            "reps": 30,
            "target_reps": 36,
            "finished_at": "18:45 15/11/2026",
            "duration_seconds": 960,
        }
        label = evaluation_view.format_session_label(record)
        self.assertIn("Thứ 4 - Lưng & Tay trước", label)
        self.assertIn("18:45 15/11/2026", label)
        self.assertIn("30 rep", label)

        pct, calc_label, detail = evaluation_view.compute_ai_completion_rate({}, selected_result=record)
        self.assertEqual(pct, 83)  # round(30 * 100 / 36) = 83%
        self.assertIn("30/36 reps", detail)
        self.assertEqual(label, calc_label)

    def test_rpe_borg_scale_emojis_and_default(self):
        """2. Kiểm tra thang đo RPE Borg 1-10 có đủ 10 mức kèm dải emoji và mô tả chuẩn."""
        self.assertEqual(len(evaluation_view.RPE_DESCRIPTIONS), 10)
        expected_emojis = ["😌", "🙂", "😊", "😉", "😤", "😅", "😓", "😫", "🥵", "🤯"]
        for score in range(1, 11):
            desc = evaluation_view.RPE_DESCRIPTIONS[score]
            self.assertIn(expected_emojis[score - 1], desc)

        # Kiểm tra mức mặc định RPE = 5 (Vừa sức lý tưởng)
        self.assertIn("Vừa sức", evaluation_view.RPE_DESCRIPTIONS[5])
        self.assertIn("😤", evaluation_view.RPE_DESCRIPTIONS[5])

    def test_doms_and_satisfaction_options(self):
        """3. Kiểm tra các tùy chọn mỏi cơ DOMS và mức độ hài lòng buổi tập."""
        doms_keys = list(evaluation_view.DOMS_SEVERITY_OPTIONS.keys())
        self.assertIn("normal", doms_keys)
        self.assertIn("moderate", doms_keys)
        self.assertIn("intense", doms_keys)

        sat_keys = list(evaluation_view.SATISFACTION_OPTIONS.keys())
        self.assertIn("very_satisfied", sat_keys)
        self.assertIn("satisfied", sat_keys)
        self.assertIn("neutral", sat_keys)
        self.assertIn("unsatisfied", sat_keys)

    def test_adaptive_formulation_4_tiers_ct_4_4(self):
        """4. Kiểm tra thuật toán thích ứng tải trọng 4 bậc chuẩn CT Section 4.4."""
        # Tier 1: Deload -15% khi rho < 0.70 hoặc RPE >= 9
        res_deload_rho = evaluation_view.compute_adaptive_adjustment(rho=65, rpe=7)
        self.assertEqual(res_deload_rho["strategy"], "deload")
        self.assertEqual(res_deload_rho["multiplier"], 0.85)

        res_deload_rpe = evaluation_view.compute_adaptive_adjustment(rho=90, rpe=9)
        self.assertEqual(res_deload_rpe["strategy"], "deload")
        self.assertEqual(res_deload_rpe["multiplier"], 0.85)

        # Tier 2: Giảm nhẹ -5% khi 0.70 <= rho < 0.85 hoặc (RPE == 8 và rho < 0.90)
        res_minor = evaluation_view.compute_adaptive_adjustment(rho=75, rpe=7)
        self.assertEqual(res_minor["strategy"], "minor_deload")
        self.assertEqual(res_minor["multiplier"], 0.95)

        res_minor_rpe8 = evaluation_view.compute_adaptive_adjustment(rho=88, rpe=8)
        self.assertEqual(res_minor_rpe8["strategy"], "minor_deload")
        self.assertEqual(res_minor_rpe8["multiplier"], 0.95)

        # Tier 3: Cường độ tối ưu duy trì 1.00x khi 0.85 <= rho <= 1.00 và RPE in [7, 8]
        res_maint = evaluation_view.compute_adaptive_adjustment(rho=95, rpe=7)
        self.assertEqual(res_maint["strategy"], "maintenance")
        self.assertEqual(res_maint["multiplier"], 1.00)

        # Tier 4: Tăng tiến tải trọng +10% khi rho >= 0.90 và RPE <= 6
        res_overload = evaluation_view.compute_adaptive_adjustment(rho=100, rpe=5)
        self.assertEqual(res_overload["strategy"], "overload")
        self.assertEqual(res_overload["multiplier"], 1.10)
        self.assertEqual(res_overload["rep_delta"], 2)

    def test_recovery_advice_and_hydration(self):
        """5. Kiểm tra lời khuyên phục hồi giãn cơ (Cool-down) và tính lượng nước bù."""
        # Kiểm tra bài tập giãn cơ cho Đùi trước và Ngực
        advice = evaluation_view.get_recovery_advice(["Cơ đùi trước (Quads)", "Cơ ngực (Chest)"])
        self.assertEqual(len(advice), 2)
        self.assertEqual(advice[0]["rest_hours"], 48)
        self.assertIn("Quad Stretch", advice[0]["stretch_name"])
        self.assertEqual(advice[1]["rest_hours"], 48)
        self.assertIn("Doorway Chest Stretch", advice[1]["stretch_name"])

        # Kiểm tra cổ tay (cơ nhỏ nghỉ 24h)
        wrist_advice = evaluation_view.get_recovery_advice(["Cổ tay"])
        self.assertEqual(wrist_advice[0]["rest_hours"], 24)

        # Kiểm tra tính lượng nước bù sau tập
        ml, text = evaluation_view.calculate_hydration_advice(duration_sec=1200)  # 20 phút
        self.assertTrue(350 <= ml <= 550)
        self.assertIn(f"{ml}ml", text)

    def test_apply_adaptive_adjustment_to_schedule(self):
        """6. Kiểm tra cập nhật số reps vào Kế hoạch tuần, bảo vệ buổi đã hoàn thành."""
        dummy_schedule = [
            {
                "day": "Thứ 2",
                "workout_status": "completed",
                "exercises": [{"name": "Push-up", "reps": 12}],
            },
            {
                "day": "Thứ 4",
                "workout_status": "planned",
                "is_rest": False,
                "exercises": [{"name": "Standard Push-up", "reps": 20}],
            },
            {
                "day": "Thứ 6",
                "workout_status": "planned",
                "is_rest": True,
                "exercises": [],
            },
        ]

        strat_deload = {"strategy": "deload", "multiplier": 0.85, "rep_delta": -2}
        updated, count = evaluation_view.apply_adaptive_adjustment_to_schedule(dummy_schedule, strat_deload)

        self.assertEqual(count, 1)
        # Thứ 2 đã completed nên giữ nguyên 12
        self.assertEqual(updated[0]["exercises"][0]["reps"], 12)
        # Thứ 4 planned nên giảm 15%: round(20 * 0.85) = 17
        self.assertEqual(updated[1]["exercises"][0]["reps"], 17)

        # Thử nghiệm overload +2 reps
        strat_overload = {"strategy": "overload", "multiplier": 1.10, "rep_delta": 2}
        updated_overload, count_overload = evaluation_view.apply_adaptive_adjustment_to_schedule(dummy_schedule, strat_overload)
        self.assertEqual(count_overload, 1)
        self.assertEqual(updated_overload[1]["exercises"][0]["reps"], 22)

    def test_streak_earned_condition_ct_4_5(self):
        """7. Kiểm tra điều kiện duy trì chuỗi Streak theo CT 4.5 (rho >= 50% hoặc T >= 600s)."""
        # Hoàn thành 50% khối lượng -> Được streak
        self.assertTrue(evaluation_view.check_is_streak_earned(rho=50, duration_sec=300))
        # Tập đủ 10 phút (600s) dù rho chỉ 40% -> Được streak
        self.assertTrue(evaluation_view.check_is_streak_earned(rho=40, duration_sec=600))
        # Bỏ dở khi rho = 30% và thời gian mới 200s -> Không được streak
        self.assertFalse(evaluation_view.check_is_streak_earned(rho=30, duration_sec=200, is_completed=False))

    def test_backend_api_evaluation_endpoints(self):
        """8. Kiểm tra đầy đủ các REST API endpoint phục vụ đánh giá sau buổi tập."""
        # GET /api/progress/evaluation-meta
        res_meta = self.client.get("/api/progress/evaluation-meta")
        self.assertEqual(res_meta.status_code, 200)
        meta = res_meta.json()
        self.assertIn("rpe_descriptions", meta)
        self.assertIn("doms_severity_options", meta)
        self.assertIn("satisfaction_options", meta)
        self.assertIn("stretching_recommendations", meta)

        # POST /api/progress/evaluate (Minor deload test)
        res_eval = self.client.post("/api/progress/evaluate", json={
            "session_id": "test-sess-01",
            "session_label": "Thứ 2 - Upper Body",
            "completion_rate": 78,
            "rpe": 7,
            "soreness": ["Cơ ngực (Chest)", "Cổ tay"],
            "doms_severity": "moderate",
            "satisfaction": "satisfied",
            "duration_sec": 1000,
            "note": "Cơ ngực mỏi căng tốt!",
            "auto_apply": True,
        })
        self.assertEqual(res_eval.status_code, 200)
        eval_data = res_eval.json()["evaluation"]
        self.assertEqual(eval_data["recommendation"]["strategy"], "minor_deload")
        self.assertEqual(eval_data["doms_severity"], "moderate")
        self.assertEqual(eval_data["satisfaction"], "satisfied")
        self.assertTrue(len(eval_data["recovery_items"]) >= 2)
        self.assertIn("ml", eval_data["hydration_advice"])

        # GET /api/progress/evaluations
        res_list = self.client.get("/api/progress/evaluations")
        self.assertEqual(res_list.status_code, 200)
        self.assertTrue(res_list.json()["count"] >= 1)

    def test_demo_account_auth_and_seeded_data(self):
        """9. Kiểm tra tài khoản Demo (demo@fitsense.vn) đăng nhập và có đầy đủ dữ liệu mẫu."""
        # Test login API with demo credentials
        res_login = self.client.post("/api/auth/login", json={
            "email": "demo@fitsense.vn",
            "password": "demo123",
        })
        self.assertEqual(res_login.status_code, 200)
        user = res_login.json()["user"]
        self.assertEqual(user["email"], "demo@fitsense.vn")
        self.assertEqual(user["name"], "Vận Động Viên Trải Nghiệm")

        # Test pre-seeded workout history
        res_hist = self.client.get("/api/progress/history")
        self.assertEqual(res_hist.status_code, 200)
        self.assertTrue(res_hist.json()["count"] >= 4)

        # Test pre-seeded stats & PRs
        res_stats = self.client.get("/api/progress/stats")
        self.assertEqual(res_stats.status_code, 200)
        stats = res_stats.json()
        self.assertTrue(stats["total_workouts"] >= 4)
        self.assertIn("Standard Push-up", stats["personal_records"])
        self.assertEqual(stats["personal_records"]["Standard Push-up"], "36 Reps")

        # Test Streamlit session populator
        dummy_state = {}
        import src.auth_view as auth_view
        auth_view.populate_demo_user_session(dummy_state)
        self.assertTrue(dummy_state["is_logged_in"])
        self.assertEqual(dummy_state["user_profile"]["email"], "demo@fitsense.vn")
        self.assertEqual(dummy_state["streak_info"]["current_streak"], 4)
        self.assertEqual(len(dummy_state["workout_results"]), 4)
        self.assertEqual(len(dummy_state["session_history"]), 4)

    def test_evaluation_per_session_isolation_and_hidden_when_unsubmitted(self):
        """10. Khuyến nghị chỉ xuất hiện cho buổi đã đánh giá, ẩn hoàn toàn với buổi chưa khảo sát."""
        res_list = self.client.get("/api/progress/evaluations").json()
        evals = res_list["evaluations"]
        eval_sessions = {e.get("session_id") for e in evals if e.get("session_id")}

        # w-04 và w-03 đã có đánh giá
        self.assertIn("w-04", eval_sessions)
        self.assertIn("w-03", eval_sessions)
        # w-02 (Squat) và w-01 (Push-up) chưa có đánh giá
        self.assertNotIn("w-02", eval_sessions)
        self.assertNotIn("w-01", eval_sessions)

        # Gửi đánh giá mới cho w-02
        res_eval = self.client.post("/api/progress/evaluate", json={
            "session_id": "w-02",
            "session_label": "Squat Thể dục (Bodyweight Squat)",
            "completion_rate": 90,
            "rpe": 5,
            "soreness": ["Cơ đùi trước (Quads)"],
            "doms_severity": "normal",
            "satisfaction": "very_satisfied",
            "duration_sec": 960,
        })
        self.assertEqual(res_eval.status_code, 200)
        self.assertEqual(res_eval.json()["evaluation"]["session_id"], "w-02")
        self.assertEqual(res_eval.json()["evaluation"]["recommendation"]["strategy"], "overload")

        # Kiểm tra w-02 giờ đã có đánh giá trong danh sách
        updated_list = self.client.get("/api/progress/evaluations").json()["evaluations"]
        updated_sessions = {e.get("session_id") for e in updated_list if e.get("session_id")}
        self.assertIn("w-02", updated_sessions)
        # w-01 vẫn chưa có đánh giá
        self.assertNotIn("w-01", updated_sessions)

    def test_multi_exercise_evaluation_and_substitute_recommendation(self):
        """11. Kiểm tra đánh giá theo bài tập con trong buổi và đề xuất bài biến thể thay thế."""
        # Kiểm tra dữ liệu lịch sử buổi tập có chứa danh sách bài tập con (2-3 bài/buổi)
        res_hist = self.client.get("/api/progress/history").json()
        w01 = next(w for w in res_hist["history"] if w["id"] == "w-01")
        self.assertTrue(len(w01.get("exercises", [])) >= 3)
        self.assertEqual(w01["exercises"][0]["id"], "push_up")

        # Gửi đánh giá riêng cho bài 'push_up' trong w-01 với RPE = 9 (quá tải)
        res_ex_eval = self.client.post("/api/progress/evaluate", json={
            "session_id": "w-01",
            "session_label": "Thứ 2: Thân trên: Ngực & Tay sau (3 bài)",
            "scope": "exercise",
            "exercise_id": "push_up",
            "exercise_name": "Standard Push-up",
            "completion_rate": 65,
            "rpe": 9,
            "soreness": ["Cơ ngực (Chest)", "Cổ tay"],
            "doms_severity": "intense",
            "satisfaction": "unsatisfied",
        })
        self.assertEqual(res_ex_eval.status_code, 200)
        eval_data = res_ex_eval.json()["evaluation"]
        self.assertEqual(eval_data["scope"], "exercise")
        self.assertEqual(eval_data["exercise_id"], "push_up")
        self.assertIn("Knee Push-up", eval_data["recommendation"]["action"])
        self.assertIn("Tối ưu Động tác", eval_data["recommendation"]["title"])


if __name__ == "__main__":
    unittest.main()
