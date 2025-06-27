#!/usr/bin/env python3
"""
YouTube Transcript Downloader (Manual Implementation)

This script downloads transcripts from YouTube videos using web scraping.
"""

import sys
import urllib.request
import urllib.parse
import json
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

def get_transcript_data(video_id):
    """Get transcript data from YouTube"""
    try:
        # Construct YouTube watch URL
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Create request with headers to mimic browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        req = urllib.request.Request(watch_url, headers=headers)
        response = urllib.request.urlopen(req)
        html = response.read().decode('utf-8')
        
        # Look for captions data in the HTML
        caption_tracks_pattern = r'"captionTracks":\[(.*?)\]'
        match = re.search(caption_tracks_pattern, html)
        
        if not match:
            return None, "No caption tracks found"
        
        # Extract the first caption track URL
        caption_data = match.group(1)
        base_url_pattern = r'"baseUrl":"(.*?)"'
        url_match = re.search(base_url_pattern, caption_data)
        
        if not url_match:
            return None, "No caption URL found"
        
        caption_url = url_match.group(1).replace('\\u0026', '&')
        
        # Download the caption XML
        req = urllib.request.Request(caption_url, headers=headers)
        response = urllib.request.urlopen(req)
        xml_content = response.read().decode('utf-8')
        
        return xml_content, None
        
    except Exception as e:
        return None, str(e)

def parse_xml_transcript(xml_content):
    """Parse XML transcript content"""
    transcript = ""
    
    # Simple XML parsing for transcript entries
    text_pattern = r'<text start="([^"]*)"[^>]*>([^<]*)</text>'
    matches = re.findall(text_pattern, xml_content)
    
    for start_time, text in matches:
        # Clean up the text (decode HTML entities)
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
        transcript += f"[{float(start_time):.2f}s] {text}\n"
    
    return transcript

def download_transcript(video_url):
    """Download and format transcript from YouTube video"""
    video_id = extract_video_id(video_url)
    
    if not video_id:
        return None, "Could not extract video ID from URL"
    
    xml_content, error = get_transcript_data(video_id)
    
    if error:
        return None, error
    
    if not xml_content:
        return None, "No transcript content found"
    
    transcript = parse_xml_transcript(xml_content)
    
    if not transcript:
        return None, "Could not parse transcript data"
    
    return transcript, None

def main():
    if len(sys.argv) != 2:
        print("Usage: python download_transcript_manual.py <youtube_url>")
        print("Example: python download_transcript_manual.py 'https://www.youtube.com/watch?v=suXZgzy3sAU'")
        sys.exit(1)
    
    video_url = sys.argv[1]
    print(f"Downloading transcript for: {video_url}")
    
    transcript, error = download_transcript(video_url)
    
    if error:
        print(f"Error: {error}")
        sys.exit(1)
    
    if transcript:
        video_id = extract_video_id(video_url)
        filename = f"transcript_{video_id}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(transcript)
        
        print(f"Transcript saved to: {filename}")
        print(f"Total length: {len(transcript)} characters")
        print("\nFirst 500 characters:")
        print(transcript[:500] + "..." if len(transcript) > 500 else transcript)
    else:
        print("Failed to download transcript")
        sys.exit(1)

if __name__ == "__main__":
    main()