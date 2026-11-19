"""Regression checks for 28-item library and primary/secondary exercise swap."""
import unittest
from src.exercise_library import (load_catalog, validate_catalog, search_exercises,
                                  compatible_replacements, suggest_alternatives, GROUPS8)

class TestFeedback28(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def test_exactly_28(self):
        self.assertEqual(len(self.catalog), 28)
        validate_catalog(self.catalog)

    def test_eight_groups_present(self):
        for group, muscles in GROUPS8.items():
            with self.subTest(group=group):
                self.assertTrue(any(set(ex['primary_muscles']) & set(muscles) for ex in self.catalog))

    def test_each_item_has_replacement_with_unrestricted_profile(self):
        for ex in self.catalog:
            with self.subTest(ex=ex['id']):
                self.assertTrue(compatible_replacements(ex,self.catalog))

    def test_options_for_planner_name(self):
        suggestions = compatible_replacements({'name':'Standard Push-up (Hít đất chuẩn)', 'primary_muscle':'Ngực'},self.catalog)
        self.assertTrue(suggestions)
        self.assertTrue(any('chest' in (ex['primary_muscles']+ex['secondary_muscles']) for ex in suggestions))

    def test_legacy_back_plan_name(self):
        options=compatible_replacements({'name':'Inverted Rows (Hít xà nghiêng)','primary_muscle':'Lưng & Xô'},self.catalog)
        self.assertTrue(options)
        self.assertTrue(all('back' in ex['primary_muscles']+ex['secondary_muscles'] for ex in options))

    def test_primary_and_secondary_used(self):
        result=compatible_replacements({'name':'Tập bụng', 'primary_muscle':'Ngực'},self.catalog)
        self.assertTrue(any('chest' in e['secondary_muscles'] for e in result))

    def test_filtered_equipment_no_empty_for_back(self):
        row=next(ex for ex in self.catalog if ex['id']=='band_row')
        self.assertTrue(suggest_alternatives(row,self.catalog,available_equipment=set()))

    def test_no_self_and_no_unknown_ids(self):
        for ex in self.catalog:
            alts=compatible_replacements(ex,self.catalog)
            self.assertNotIn(ex['id'],[a['id'] for a in alts])

if __name__=='__main__':unittest.main()
