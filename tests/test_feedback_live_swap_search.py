"""Regression tests for muscle-aware swaps and instant search feedback."""
from pathlib import Path
import unittest

from src.exercise_library import (load_catalog, replacement_matches,
                                  planner_target_muscles, search_exercises)


class TestLiveSwapAndSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def test_all_replacements_overlap_target_primary_or_secondary(self):
        for original in self.catalog:
            with self.subTest(original=original['id']):
                target = set(original['primary_muscles']) | set(original['secondary_muscles'])
                options = replacement_matches(original, self.catalog)
                self.assertTrue(options)
                self.assertEqual(len(options), len({item['id'] for item in options}))
                for chosen in options:
                    self.assertNotEqual(chosen['id'], original['id'])
                    self.assertTrue(target & (set(chosen['primary_muscles']) |
                                              set(chosen['secondary_muscles'])))

    def test_pushup_primary_chest_and_secondary_triceps(self):
        current = next(ex for ex in self.catalog if ex['id'] == 'push_up')
        options = replacement_matches(current, self.catalog)
        by_id = {ex['id']: ex for ex in options}
        self.assertIn('knee_push_up', by_id)
        self.assertIn('bench_dip', by_id)
        self.assertIn('chest', by_id['knee_push_up']['match_primary'])
        self.assertIn('triceps', by_id['bench_dip']['match_primary'])
        self.assertIn('chest', by_id['bench_dip']['match_secondary'])
        self.assertNotIn('squat', by_id)

    def test_legacy_name_and_roles(self):
        old = {'name': 'Standard Push-up', 'primary_muscle': 'Ngực (Chest)',
               'secondary_muscle': 'Tay sau, Vai'}
        primary, secondary = planner_target_muscles(old, self.catalog)
        self.assertIn('chest', primary)
        self.assertIn('triceps', secondary)
        self.assertNotIn('quads', primary | secondary)
        opts = replacement_matches(old, self.catalog)
        self.assertIn('knee_push_up', {ex['id'] for ex in opts})
        self.assertNotIn('squat', {ex['id'] for ex in opts})

    def test_unknown_muscle_no_all_exercises_fallback(self):
        self.assertEqual(replacement_matches({'name':'Unknown New Exercise'}, self.catalog), [])

    def test_search_substrings_without_enter(self):
        self.assertIn('push_up', {ex['id'] for ex in search_exercises(self.catalog, 'hit')})
        self.assertIn('push_up', {ex['id'] for ex in search_exercises(self.catalog, 'hit dat')})

    def test_streamlit_live_search_wired(self):
        source = (Path(__file__).parents[1] / 'src' / 'exercise_library_view.py').read_text(encoding='utf-8')
        self.assertIn('from st_keyup import st_keyup', source)
        self.assertIn('debounce=180', source)
        self.assertIn('exercise_library_live_search', source)

    def test_swap_callback_updates_on_selection(self):
        source = (Path(__file__).parents[1] / 'src' / 'planner_view.py').read_text(encoding='utf-8')
        self.assertIn('on_change=apply_selected_replacement', source)
        self.assertIn("st.session_state['weekly_schedule'] = replace_in_schedule", source)


if __name__ == '__main__':
    unittest.main()
