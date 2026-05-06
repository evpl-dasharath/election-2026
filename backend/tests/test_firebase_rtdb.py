import sys
from unittest.mock import MagicMock

# Mock dependencies before importing the module under test
mock_firebase_admin = MagicMock()
sys.modules['firebase_admin'] = mock_firebase_admin
sys.modules['firebase_admin.credentials'] = MagicMock()
sys.modules['firebase_admin.db'] = MagicMock()
sys.modules['django'] = MagicMock()
sys.modules['django.conf'] = MagicMock()

import unittest
import os

# Add backend to sys.path to import firebase_rtdb
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from firebase_rtdb import has_constituency_changed

class TestFirebaseRTDB(unittest.TestCase):
    def setUp(self):
        self.ac_number = 1
        self.str_ac = "1"
        self.base_data = {
            'status': 'IN_PROGRESS',
            'rounds_completed': 5,
            'total_rounds': 10,
            'candidates': [
                {'name': 'Candidate A', 'votes': 1000},
                {'name': 'Candidate B', 'votes': 800}
            ]
        }
        self.cache = {
            "live": {
                self.str_ac: {
                    'status': 'IN_PROGRESS',
                    'rounds_completed': 5,
                    'total_rounds': 10,
                    'candidates': [
                        {'name': 'Candidate A', 'votes': 1000},
                        {'name': 'Candidate B', 'votes': 800}
                    ]
                }
            }
        }

    def test_no_change(self):
        """Identical data should return False (or something falsy)."""
        new_data = self.base_data.copy()
        result = has_constituency_changed(self.ac_number, new_data, self.cache)
        # Using bool() to ensure it's falsy (False or None)
        self.assertFalse(bool(result))

    def test_ac_not_in_cache(self):
        """AC number not in cache should return True."""
        self.assertTrue(has_constituency_changed(999, self.base_data, self.cache))

    def test_status_change(self):
        """Change in status should return True."""
        new_data = self.base_data.copy()
        new_data['status'] = 'RESULT_DECLARED'
        self.assertTrue(has_constituency_changed(self.ac_number, new_data, self.cache))

    def test_rounds_completed_change(self):
        """Change in rounds_completed should return True."""
        new_data = self.base_data.copy()
        new_data['rounds_completed'] = 6
        self.assertTrue(has_constituency_changed(self.ac_number, new_data, self.cache))

    def test_total_rounds_change(self):
        """Change in total_rounds should return True."""
        new_data = self.base_data.copy()
        new_data['total_rounds'] = 11
        self.assertTrue(has_constituency_changed(self.ac_number, new_data, self.cache))

    def test_candidate_count_change(self):
        """Change in number of candidates should return True."""
        new_data = self.base_data.copy()
        new_data['candidates'] = self.base_data['candidates'] + [{'name': 'Candidate C', 'votes': 100}]
        self.assertTrue(has_constituency_changed(self.ac_number, new_data, self.cache))

    def test_candidate_votes_change(self):
        """Change in candidate votes should return True."""
        new_data = {
            'status': 'IN_PROGRESS',
            'rounds_completed': 5,
            'total_rounds': 10,
            'candidates': [
                {'name': 'Candidate A', 'votes': 1001},
                {'name': 'Candidate B', 'votes': 800}
            ]
        }
        self.assertTrue(has_constituency_changed(self.ac_number, new_data, self.cache))

    def test_candidate_name_change(self):
        """Change in candidate name should return True."""
        new_data = {
            'status': 'IN_PROGRESS',
            'rounds_completed': 5,
            'total_rounds': 10,
            'candidates': [
                {'name': 'Candidate X', 'votes': 1000},
                {'name': 'Candidate B', 'votes': 800}
            ]
        }
        self.assertTrue(has_constituency_changed(self.ac_number, new_data, self.cache))

    def test_candidate_order_change(self):
        """Change in candidate order should return True (current implementation is order-sensitive)."""
        new_data = {
            'status': 'IN_PROGRESS',
            'rounds_completed': 5,
            'total_rounds': 10,
            'candidates': [
                {'name': 'Candidate B', 'votes': 800},
                {'name': 'Candidate A', 'votes': 1000}
            ]
        }
        self.assertTrue(has_constituency_changed(self.ac_number, new_data, self.cache))

    def test_missing_candidates_in_new_data(self):
        """Missing candidates key in new data should be handled (defaults to empty list)."""
        new_data = {
            'status': 'IN_PROGRESS',
            'rounds_completed': 5,
            'total_rounds': 10
        }
        # cached_data has candidates, new_data does not -> length mismatch -> True
        self.assertTrue(has_constituency_changed(self.ac_number, new_data, self.cache))

    def test_missing_candidates_in_cache(self):
        """Missing candidates key in cache should be handled."""
        cache = {
            "live": {
                self.str_ac: {
                    'status': 'IN_PROGRESS',
                    'rounds_completed': 5,
                    'total_rounds': 10
                }
            }
        }
        new_data = self.base_data.copy()
        # cached_data has no candidates, new_data has -> length mismatch -> True
        self.assertTrue(has_constituency_changed(self.ac_number, new_data, cache))

    def test_missing_top_level_field_in_new_data(self):
        """Missing top-level field in new data should return True if it exists in cache."""
        new_data = self.base_data.copy()
        del new_data['status']
        self.assertTrue(has_constituency_changed(self.ac_number, new_data, self.cache))

if __name__ == '__main__':
    unittest.main()
