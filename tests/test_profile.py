"""Unit tests for SCRUM-13's pure-Python profile data logic."""
import json
import tempfile
import unittest
from pathlib import Path

from src.profile import (
    NO_EQUIPMENT, NO_RESTRICTIONS, load_profile, profile_path,
    save_profile, validate_profile,
)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.profile = {
            "name": "Example User",
            "email": "example@test.invalid",
            "goal": "Đốt mỡ & Săn chắc toàn thân",
            "fitness_level": "Beginner (Mới bắt đầu)",
            "environment": "Tại nhà / Phòng riêng",
            "restrictions": [],
            "equipment": ["Thảm yoga/thể dục"],
            "weight_kg": 65.0,
            "height_cm": 170.0,
            "age": 22,
            "days_per_week": 3,
            "session_duration_minutes": 30,
        }

    def test_valid_profile(self):
        self.assertEqual(validate_profile(self.profile), [])

    def test_missing_name(self):
        self.profile["name"] = " "
        self.assertTrue(validate_profile(self.profile))

    def test_missing_goal(self):
        self.profile["goal"] = ""
        self.assertTrue(validate_profile(self.profile))

    def test_invalid_level(self):
        self.profile["fitness_level"] = "Expert"
        self.assertTrue(validate_profile(self.profile))

    def test_injuries_conflict(self):
        self.profile["restrictions"] = [NO_RESTRICTIONS, "Cổ tay đau"]
        self.assertTrue(validate_profile(self.profile))

    def test_equipment_conflict(self):
        self.profile["equipment"] = [NO_EQUIPMENT, "Xà đơn"]
        self.assertTrue(validate_profile(self.profile))

    def test_optional_metrics(self):
        self.profile.update(weight_kg=None, height_cm=None, age=None)
        self.assertEqual(validate_profile(self.profile), [])

    def test_invalid_days_and_duration(self):
        self.profile.update(days_per_week=0, session_duration_minutes=200)
        self.assertGreaterEqual(len(validate_profile(self.profile)), 2)

    def test_save_and_load(self):
        path = save_profile(self.profile["email"], self.profile, self.directory)
        self.assertTrue(path.is_file())
        self.assertEqual(load_profile(self.profile["email"], self.directory), self.profile)

    def test_filename_does_not_expose_email(self):
        path = profile_path(self.profile["email"], self.directory)
        self.assertNotIn("@", path.name)
        self.assertEqual(path.parent, self.directory)

    def test_missing_file(self):
        self.assertIsNone(load_profile("absent@example.invalid", self.directory))

    def test_corrupt_json(self):
        path = profile_path(self.profile["email"], self.directory)
        path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_profile(self.profile["email"], self.directory)

    def test_invalid_saved_json(self):
        path = profile_path(self.profile["email"], self.directory)
        path.write_text(json.dumps({"name": "Only name"}), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_profile(self.profile["email"], self.directory)

    def test_invalid_profile_not_saved(self):
        self.profile["name"] = ""
        with self.assertRaises(ValueError):
            save_profile(self.profile["email"], self.profile, self.directory)
        self.assertFalse(profile_path(self.profile["email"], self.directory).exists())


if __name__ == "__main__":
    unittest.main()
