#!/usr/bin/env python3
"""
Test script to demonstrate proxy rotation functionality
"""

import time
from src.proxy_manager import proxy_manager
from src.transcript_extractor import transcript_extractor


def test_proxy_rotation():
    """Test proxy rotation with multiple attempts"""
    print("🔄 Testing proxy rotation functionality...")
    
    # Test manual rotation
    print(f"\n🔧 Current proxy: {proxy_manager.current_proxy}")
    
    for i in range(5):
        proxy_manager.rotate_proxy()
        proxy_config = proxy_manager.get_current_proxy_config()
        if proxy_config:
            print(f"  Rotated to proxy {proxy_manager.current_proxy}")
        else:
            print(f"  No proxy available after rotation")
    
    print()


def test_proxy_failure_handling():
    """Test proxy failure handling and automatic rotation"""
    print("🚨 Testing proxy failure handling...")
    
    # Mark current proxy as failed
    current = proxy_manager.current_proxy
    print(f"  Marking proxy {current} as failed...")
    proxy_manager.mark_proxy_failed()
    
    print(f"  New current proxy: {proxy_manager.current_proxy}")
    print(f"  Failed proxies: {proxy_manager.failed_proxies}")
    
    # Test with a few more failures
    for i in range(2):
        current = proxy_manager.current_proxy
        proxy_manager.mark_proxy_failed()
        print(f"  Marked proxy {current} as failed, now using: {proxy_manager.current_proxy}")
    
    print(f"  Final failed proxies: {proxy_manager.failed_proxies}")
    print()


def test_transcript_with_different_proxies():
    """Test transcript extraction with different proxies"""
    print("🎬 Testing transcript extraction with proxy rotation...")
    
    test_videos = [
        "dQw4w9WgXcQ",  # Rick Roll
        "9bZkp7q19f0",  # Gangnam Style (if it exists)
    ]
    
    for video_id in test_videos:
        print(f"\n  Testing video: {video_id}")
        try:
            # Force rotation before each attempt
            proxy_manager.rotate_proxy()
            current_proxy = proxy_manager.current_proxy
            print(f"    Using proxy: {current_proxy}")
            
            # Extract transcript
            result = transcript_extractor.extract_transcript(video_id)
            if result:
                print(f"    ✅ Success: {len(result)} entries with proxy {current_proxy}")
            else:
                print(f"    🔴 Failed with proxy {current_proxy}")
                
        except Exception as e:
            print(f"    🔴 Error with proxy {current_proxy}: {str(e)[:100]}...")


def test_proxy_info():
    """Display comprehensive proxy information"""
    print("📊 Proxy system information:")
    
    info = proxy_manager.get_proxy_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    print()


def main():
    """Main test function"""
    print("🚀 Starting comprehensive proxy rotation tests...\n")
    
    # Display initial proxy info
    test_proxy_info()
    
    # Test basic rotation
    test_proxy_rotation()
    
    # Test failure handling
    test_proxy_failure_handling()
    
    # Test with real transcript extraction
    test_transcript_with_different_proxies()
    
    print("\n🏁 Proxy rotation tests completed!")


if __name__ == "__main__":
    main()