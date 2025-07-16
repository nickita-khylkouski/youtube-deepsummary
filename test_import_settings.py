#!/usr/bin/env python3
"""
Test script to verify import settings are working correctly
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database_storage import database_storage

def test_import_settings():
    """Test that import settings are being read correctly"""
    print("Testing Import Settings...")
    print("=" * 50)
    
    # Get all import settings
    settings = database_storage.get_import_settings()
    
    print("All import settings:")
    for key, value in sorted(settings.items()):
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 50)
    print("Testing video processing settings logic:")
    
    # Test the same logic used in video processing
    import_settings = database_storage.get_import_settings()
    enable_transcript_extraction = import_settings.get('enableTranscriptExtraction', import_settings.get('enable_transcript_extraction', True))
    enable_auto_summary = import_settings.get('enableAutoSummary', import_settings.get('enable_auto_summary', True))
    enable_chapter_extraction = import_settings.get('enableChapterExtraction', import_settings.get('enable_chapter_extraction', True))
    
    print(f"enable_transcript_extraction: {enable_transcript_extraction}")
    print(f"enable_auto_summary: {enable_auto_summary}")
    print(f"enable_chapter_extraction: {enable_chapter_extraction}")
    
    print("\n" + "=" * 50)
    print("Expected behavior:")
    if not enable_transcript_extraction:
        print("✓ Transcript extraction should be SKIPPED")
    else:
        print("✗ Transcript extraction should be ENABLED")
        
    if not enable_auto_summary:
        print("✓ Auto summary generation should be SKIPPED")
    else:
        print("✗ Auto summary generation should be ENABLED")
        
    if not enable_chapter_extraction:
        print("✓ Chapter extraction should be SKIPPED")
    else:
        print("✗ Chapter extraction should be ENABLED")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_import_settings() 