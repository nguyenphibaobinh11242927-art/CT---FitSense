"""SCRUM-17: fast deterministic tests, no Streamlit or network required."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.exercise_library import (CATALOG_PATH, EQUIPMENT, MUSCLES, load_catalog,
                                  normalize, search_exercises, suggest_alternatives,
                                  validate_catalog)


class TestExerciseLibrary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def test_catalog_size_and_unique_ids(self):
        self.assertGreaterEqual(len(self.catalog), 15)
        self.assertEqual(len({x['id'] for x in self.catalog}), len(self.catalog))

    def test_original_fixture_persists(self):
        self.assertTrue({'squat','push_up','plank','glute_bridge','bench_dip'} <= {x['id'] for x in self.catalog})

    def test_search_vietnamese_accent_insensitive(self):
        self.assertIn('push_up', {x['id'] for x in search_exercises(self.catalog, 'hit dat')})

    def test_search_english_name(self):
        self.assertIn('squat', {x['id'] for x in search_exercises(self.catalog, 'Bodyweight Squat')})

    def test_search_muscle_name(self):
        self.assertIn('push_up', {x['id'] for x in search_exercises(self.catalog, 'nguc')})

    def test_primary_vs_secondary(self):
        self.assertIn('push_up', {x['id'] for x in search_exercises(self.catalog,muscle='chest',role='primary')})
        self.assertNotIn('push_up', {x['id'] for x in search_exercises(self.catalog,muscle='chest',role='secondary')})

    def test_equipment_filter(self):
        chosen=search_exercises(self.catalog,equipment='chair')
        self.assertTrue(chosen)
        self.assertTrue(all('chair' in x['equipment'] for x in chosen))

    def test_difficulty_filter(self):
        self.assertTrue(all(x['difficulty']=='Beginner' for x in search_exercises(self.catalog,difficulty='Beginner')))

    def test_category_filter(self):
        self.assertTrue(all(x['category']=='Cardio' for x in search_exercises(self.catalog,category='Cardio')))

    def test_combination_filter(self):
        found=search_exercises(self.catalog,query='chest',difficulty='Intermediate')
        self.assertTrue(all(x['difficulty']=='Intermediate' for x in found))

    def test_no_matches(self):
        self.assertEqual(search_exercises(self.catalog,'nonexistent-movement-name'),[])

    def test_invalid_role(self):
        with self.assertRaises(ValueError): search_exercises(self.catalog,role='typo')

    def test_alternatives_explicit_only(self):
        ex=next(x for x in self.catalog if x['id']=='push_up')
        self.assertEqual({x['id'] for x in suggest_alternatives(ex,self.catalog)},set(ex['alternatives']))

    def test_alternatives_filtered_by_equipment(self):
        ex=next(x for x in self.catalog if x['id']=='push_up')
        self.assertEqual([x['id'] for x in suggest_alternatives(ex,self.catalog,available_equipment=set())],['wall_push_up'])

    def test_alternatives_filtered_by_injury(self):
        ex=next(x for x in self.catalog if x['id']=='push_up')
        self.assertEqual(suggest_alternatives(ex,self.catalog,limitations={'wrist'}),[])

    def test_bad_duplicate_id(self):
        data=copy.deepcopy(self.catalog);data.append(copy.deepcopy(data[0]))
        with self.assertRaises(ValueError): validate_catalog(data)

    def test_unknown_alternative(self):
        data=copy.deepcopy(self.catalog);data[0]['alternatives']=['missing']
        with self.assertRaises(ValueError): validate_catalog(data)

    def test_missing_safety(self):
        data=copy.deepcopy(self.catalog);data[0]['safety_notes']=''
        with self.assertRaises(ValueError): validate_catalog(data)

    def test_unknown_equipment(self):
        data=copy.deepcopy(self.catalog);data[0]['equipment']=['treadmill']
        with self.assertRaises(ValueError): validate_catalog(data)

    def test_schema_version(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'db.json';f.write_text(json.dumps({'schema_version':2,'exercises':self.catalog}),encoding='utf-8')
            with self.assertRaises(ValueError): load_catalog(f)

    def test_media_gifs_exist(self):
        for ex in self.catalog:
            if ex.get('media_gif'):
                self.assertTrue((CATALOG_PATH.parents[1]/ex['media_gif']).is_file())


if __name__ == '__main__': unittest.main()
