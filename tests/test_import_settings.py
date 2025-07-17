#!/usr/bin/env python3
"""
Test import settings functionality
"""
import unittest
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database_storage import DatabaseStorage

class TestImportSettings(unittest.TestCase):
    """Test import settings functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.db_storage = DatabaseStorage()
    
    def test_get_import_settings(self):
        """Test getting import settings"""
        settings = self.db_storage.get_import_settings()
        
        # Should return a dictionary
        self.assertIsInstance(settings, dict)
        
        # Should have expected keys
        expected_keys = [
            'default_max_results',
            'default_days_back',
            'max_results_limit',
            'enable_auto_summary',
            'enable_transcript_extraction',
            'enable_chapter_extraction',
            'import_strategy',
            'fallback_strategies',
            'skip_existing_videos',
            'batch_processing',
            'batch_size',
            'retry_failed_imports',
            'max_retry_attempts',
            'import_timeout',
            'enable_progress_tracking',
            'log_import_operations'
        ]
        
        for key in expected_keys:
            self.assertIn(key, settings, f"Missing expected setting: {key}")
    
    def test_get_import_setting(self):
        """Test getting a specific import setting"""
        # Test getting an integer setting
        max_results = self.db_storage.get_import_setting('default_max_results', 20)
        self.assertIsInstance(max_results, int)
        self.assertGreaterEqual(max_results, 1)
        
        # Test getting a boolean setting
        auto_summary = self.db_storage.get_import_setting('enable_auto_summary', True)
        self.assertIsInstance(auto_summary, bool)
        
        # Test getting a string setting
        strategy = self.db_storage.get_import_setting('import_strategy', 'uploads_playlist')
        self.assertIsInstance(strategy, str)
        self.assertIn(strategy, ['uploads_playlist', 'activities_api', 'search_api'])
        
        # Test getting non-existent setting with default
        non_existent = self.db_storage.get_import_setting('non_existent_setting', 'default_value')
        self.assertEqual(non_existent, 'default_value')
    
    def test_update_import_setting(self):
        """Test updating an import setting"""
        # Test updating an integer setting
        success = self.db_storage.update_import_setting('test_max_results', 25, 'integer')
        self.assertTrue(success)
        
        # Verify the update
        value = self.db_storage.get_import_setting('test_max_results', 0)
        self.assertEqual(value, 25)
        
        # Test updating a boolean setting
        success = self.db_storage.update_import_setting('test_boolean', True, 'boolean')
        self.assertTrue(success)
        
        # Verify the update
        value = self.db_storage.get_import_setting('test_boolean', False)
        self.assertEqual(value, True)
        
        # Test updating a string setting
        success = self.db_storage.update_import_setting('test_string', 'test_value', 'string')
        self.assertTrue(success)
        
        # Verify the update
        value = self.db_storage.get_import_setting('test_string', '')
        self.assertEqual(value, 'test_value')
    
    def test_update_import_settings_batch(self):
        """Test updating multiple import settings at once"""
        test_settings = {
            'test_batch_1': 100,
            'test_batch_2': False,
            'test_batch_3': 'batch_test_value'
        }
        
        success = self.db_storage.update_import_settings_batch(test_settings)
        self.assertTrue(success)
        
        # Verify all updates
        for key, expected_value in test_settings.items():
            value = self.db_storage.get_import_setting(key, None)
            self.assertEqual(value, expected_value)

if __name__ == '__main__':
    unittest.main() 