#!/usr/bin/env python3
"""
YouTube Transcript Downloader

This script downloads transcripts from YouTube videos using the youtube-transcript-api library.
"""

import sys
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import re

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/.*[?&]v=([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def download_transcript(video_url, proxy=None):
    """Download and format transcript from YouTube video"""
    video_id = extract_video_id(video_url)
    
    if not video_id:
        print("Error: Could not extract video ID from URL")
        return None
    
    try:
        proxies = None
        if proxy:
            proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            print(f"Using proxy: {proxy}")
        else:
            print("No proxy specified")
        
        # First try to get English transcript directly
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'], proxies=proxies)
            print(f"Successfully fetched English transcript with {len(transcript_list)} entries")
            language_used = "en (English)"
        except Exception as e:
            print(f"English transcript not available: {str(e)}")
            
            # If English not available, get the first available transcript
            try:
                print("Attempting to find available transcripts...")
                transcript_list_data = YouTubeTranscriptApi.list_transcripts(video_id, proxies=proxies)
                
                # Get list of available language codes
                available_languages = []
                for transcript in transcript_list_data:
                    available_languages.append(transcript.language_code)
                    print(f"Available: {transcript.language} ({transcript.language_code})")
                
                if available_languages:
                    # Use the first available language code with the standard get_transcript method
                    first_lang = available_languages[0]
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[first_lang], proxies=proxies)
                    
                    # Get language name for logging
                    first_transcript = next(iter(transcript_list_data))
                    language_used = f"{first_transcript.language} ({first_transcript.language_code})"
                    print(f"Successfully fetched {language_used} transcript with {len(transcript_list)} entries")
                else:
                    raise Exception("No transcripts found")
                    
            except Exception as fallback_error:
                print(f"Fallback transcript fetch failed: {str(fallback_error)}")
                raise Exception(f"No transcripts available for this video: {str(fallback_error)}")
        
        full_transcript = ""
        for entry in transcript_list:
            text = entry['text']
            start_time = entry['start']
            full_transcript += f"[{start_time:.2f}s] {text}\n"
        
        print(f"Transcript language used: {language_used}")
        return full_transcript
        
    except Exception as e:
        print(f"Error downloading transcript: {e}")
        return None

def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python download_transcript.py <youtube_url> [proxy_ip:port]")
        print("Example: python download_transcript.py 'https://www.youtube.com/watch?v=suXZgzy3sAU' '200.174.198.86:8888'")
        sys.exit(1)
    
    video_url = sys.argv[1]
    proxy = sys.argv[2] if len(sys.argv) == 3 else None
    
    transcript = download_transcript(video_url, proxy)
    
    if transcript:
        video_id = extract_video_id(video_url)
        filename = f"transcript_{video_id}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(transcript)
        
        print(f"Transcript saved to: {filename}")
        print("\nFirst 500 characters:")
        print(transcript[:500] + "..." if len(transcript) > 500 else transcript)
    else:
        print("Failed to download transcript")
        sys.exit(1)

if __name__ == "__main__":
    main()