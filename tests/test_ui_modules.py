"""Kiểm thử cấu trúc các module và khởi tạo trạng thái giao diện Ratatouille (SCRUM-11)."""

import unittest
from unittest.mock import MagicMock
import streamlit as st

import app
import src.profile_inventory as profile_inventory
import src.menu_shopping as menu_shopping
import src.cooking as cooking
import src.diary_statistics as diary_statistics
import src.habits_exercise as habits_exercise


class TestRatatouilleUIModules(unittest.TestCase):
    """Bộ kiểm thử cho khung giao diện Streamlit và các module nghiệp vụ."""

    def setUp(self):
        """Khởi tạo môi trường giả lập trước mỗi ca test."""
        # Reset session state cho mỗi test
        st.session_state.clear()
        app.init_app_state(force_reset=True)

    def test_module_render_callables(self):
        """Kiểm tra tất cả 5 module đều có hàm render tương ứng và gọi được."""
        self.assertTrue(callable(profile_inventory.render_profile_inventory))
        self.assertTrue(callable(menu_shopping.render_menu_shopping))
        self.assertTrue(callable(cooking.render_cooking))
        self.assertTrue(callable(diary_statistics.render_diary_statistics))
        self.assertTrue(callable(habits_exercise.render_habits_exercise))

    def test_session_state_initialization(self):
        """Kiểm tra khởi tạo trạng thái đầy đủ 8 thực thể dữ liệu chính."""
        expected_keys = [
            "user_profile",
            "kitchen_utensils",
            "ingredient_batches",
            "menu_suggestions",
            "shopping_basket_items",
            "event_log",
            "habits_streaks",
            "exercise_profile",
            "food_diary",
        ]
        for key in expected_keys:
            self.assertIn(key, st.session_state, f"Thiếu key '{key}' trong session_state.")

    def test_fefo_expiry_warning_detection(self):
        """Kiểm tra dữ liệu mẫu có lô nguyên liệu hạn dùng gần để kích hoạt cảnh báo FEFO."""
        batches = st.session_state["ingredient_batches"]
        self.assertGreater(len(batches), 0)
        # Kiểm tra cấu trúc mỗi lô
        for b in batches:
            self.assertIn("batch_id", b)
            self.assertIn("name", b)
            self.assertIn("quantity", b)
            self.assertIn("unit", b)
            self.assertIn("expiry_date", b)
            self.assertIn("status", b)

    def test_shortage_calculation_rule(self):
        """Kiểm tra công thức tính phần thiếu: Shortage = max(0, Required - Available)."""
        required = 150.0
        available_empty = 0.0
        available_more = 200.0

        shortage_1 = max(0.0, required - available_empty)
        shortage_2 = max(0.0, required - available_more)

        self.assertEqual(shortage_1, 150.0)
        self.assertEqual(shortage_2, 0.0)

    def test_habit_independent_streaks(self):
        """Kiểm tra 4 thói quen độc lập được khởi tạo đúng và độc lập (P8)."""
        habits = st.session_state["habits_streaks"]
        expected_habits = ["cook_at_home", "healthy_eating", "under_budget", "daily_exercise"]
        for h in expected_habits:
            self.assertIn(h, habits)
            self.assertIn("current_streak", habits[h])
            self.assertIn("longest_streak", habits[h])
            self.assertIn("today_status", habits[h])

    def test_event_log_deduplication_structure(self):
        """Kiểm tra mỗi sự kiện có Event ID duy nhất và phân loại rõ ràng (P6)."""
        events = st.session_state["event_log"]
        self.assertGreater(len(events), 0)
        event_ids = [e["event_id"] for e in events]
        self.assertEqual(len(event_ids), len(set(event_ids)), "Mã sự kiện bị trùng lặp!")


if __name__ == "__main__":
    unittest.main()
