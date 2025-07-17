#!/usr/bin/env python3
"""
Test script for proxy-enabled transcript extraction
"""

import sys
from src.transcript_extractor import transcript_extractor
from src.proxy_manager import proxy_manager


def test_proxy_config():
    """Test proxy configuration"""
    print("🔧 Testing proxy configuration...")
    
    proxy_info = proxy_manager.get_proxy_info()
    print(f"📊 Proxy Info: {proxy_info}")
    
    if proxy_info['webshare_configured']:
        print("✅ Webshare proxy is configured")
        
        # Test proxy connection
        success, message = proxy_manager.test_proxy()
        print(f"🧪 Proxy test: {message}")
        
        if success:
            print("✅ Proxy connection successful")
        else:
            print("🔴 Proxy connection failed")
    else:
        print("⚠️ No Webshare proxy configured")
    
    print()


def test_transcript_extraction(video_id):
    """Test transcript extraction with proxy"""
    print(f"🎬 Testing transcript extraction for video: {video_id}")
    
    try:
        transcript = transcript_extractor.extract_transcript(video_id)
        
        if transcript:
            print(f"✅ Successfully extracted transcript with {len(transcript)} entries")
            print(f"📝 First few entries:")
            for i, entry in enumerate(transcript[:3]):
                print(f"  [{entry['formatted_time']}] {entry['text'][:100]}...")
            return True
        else:
            print("🔴 Failed to extract transcript")
            return False
            
    except Exception as e:
        print(f"🔴 Error: {str(e)}")
        return False


def main():
    """Main test function"""
    print("🚀 Starting proxy transcript extraction test...\n")
    
    # Test proxy configuration
    test_proxy_config()
    
    # Test with a sample video ID
    test_video_id = "dQw4w9WgXcQ"  # Rick Roll (reliable test video)
    
    if len(sys.argv) > 1:
        test_video_id = sys.argv[1]
    
    print(f"🎯 Using test video ID: {test_video_id}\n")
    
    # Test transcript extraction
    success = test_transcript_extraction(test_video_id)
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n🔴 Tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()