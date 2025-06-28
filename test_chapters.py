#!/usr/bin/env python3
"""
Test script to debug chapter extraction issues
"""

def test_environment():
    """Test the environment for chapter extraction"""
    print("=== Environment Test ===")
    
    # Test yt-dlp import
    try:
        import yt_dlp
        print("✅ yt-dlp imported successfully")
        print(f"yt-dlp version: {yt_dlp.version.__version__}")
    except ImportError as e:
        print(f"❌ yt-dlp import failed: {e}")
        return False
    
    # Test basic yt-dlp functionality
    try:
        test_video_id = "Dp75wqOrtBs"
        print(f"\n=== Testing chapter extraction for {test_video_id} ===")
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_info = ydl.extract_info(
                f'https://www.youtube.com/watch?v={test_video_id}', 
                download=False
            )
            
            chapters = video_info.get('chapters', [])
            print(f"Found {len(chapters)} chapters")
            
            if chapters:
                for i, chapter in enumerate(chapters[:3]):  # Show first 3
                    print(f"  {i+1}. {chapter.get('title', 'Unknown')} - {chapter.get('start_time', 0)}s")
                if len(chapters) > 3:
                    print(f"  ... and {len(chapters) - 3} more chapters")
            else:
                print("No chapters found")
                
        return True
        
    except Exception as e:
        print(f"❌ Chapter extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_transcript_summarizer():
    """Test the transcript_summarizer module"""
    print("\n=== Testing transcript_summarizer module ===")
    
    try:
        from transcript_summarizer import extract_video_chapters
        print("✅ transcript_summarizer imported successfully")
        
        test_video_id = "Dp75wqOrtBs"
        chapters = extract_video_chapters(test_video_id)
        
        if chapters:
            print(f"✅ Found {len(chapters)} chapters via transcript_summarizer")
        else:
            print("❌ No chapters found via transcript_summarizer")
            
        return chapters is not None
        
    except Exception as e:
        print(f"❌ transcript_summarizer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("YouTube Chapter Extraction Test")
    print("=" * 40)
    
    env_ok = test_environment()
    module_ok = test_transcript_summarizer()
    
    print(f"\n=== Results ===")
    print(f"Environment test: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"Module test: {'✅ PASS' if module_ok else '❌ FAIL'}")
    
    if env_ok and module_ok:
        print("✅ Everything looks good!")
    else:
        print("❌ Issues detected - check error messages above")