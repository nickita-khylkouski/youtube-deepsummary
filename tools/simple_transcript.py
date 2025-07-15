#!/usr/bin/env python3
"""
Simple YouTube Transcript Downloader

Downloads transcripts using yt-dlp which is commonly available.
"""

import sys
import subprocess
import json
import os

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    import re
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/.*[?&]v=([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def download_with_ytdlp(video_url):
    """Download transcript using yt-dlp"""
    try:
        # Try to get subtitle info first
        cmd = ['yt-dlp', '--list-subs', video_url]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return None, f"yt-dlp failed: {result.stderr}"
        
        # Download auto-generated English subtitles
        video_id = extract_video_id(video_url)
        cmd = ['yt-dlp', '--write-auto-sub', '--sub-lang', 'en', '--skip-download', '--sub-format', 'vtt', video_url]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return None, f"Failed to download subtitles: {result.stderr}"
        
        # Look for the downloaded subtitle file
        subtitle_files = [f for f in os.listdir('.') if f.endswith('.vtt') and video_id in f]
        
        if not subtitle_files:
            return None, "No subtitle file found after download"
        
        subtitle_file = subtitle_files[0]
        
        # Read and parse the VTT file
        with open(subtitle_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Clean up the file
        os.remove(subtitle_file)
        
        return parse_vtt(content), None
        
    except FileNotFoundError:
        return None, "yt-dlp not found. Please install it with: pip install yt-dlp"
    except Exception as e:
        return None, str(e)

def parse_vtt(vtt_content):
    """Parse VTT subtitle content"""
    lines = vtt_content.split('\n')
    transcript = ""
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for timestamp lines
        if '-->' in line:
            # Extract start time
            start_time = line.split(' --> ')[0]
            i += 1
            
            # Get the text lines
            text_lines = []
            while i < len(lines) and lines[i].strip() and '-->' not in lines[i]:
                text_lines.append(lines[i].strip())
                i += 1
            
            if text_lines:
                text = ' '.join(text_lines)
                # Remove HTML tags
                import re
                text = re.sub(r'<[^>]+>', '', text)
                transcript += f"[{start_time}] {text}\n"
        else:
            i += 1
    
    return transcript

def main():
    if len(sys.argv) != 2:
        print("Usage: python simple_transcript.py <youtube_url>")
        print("Example: python simple_transcript.py 'https://www.youtube.com/watch?v=suXZgzy3sAU'")
        print("\nNote: This script requires yt-dlp. Install it with:")
        print("pip install yt-dlp")
        sys.exit(1)
    
    video_url = sys.argv[1]
    print(f"Downloading transcript for: {video_url}")
    
    transcript, error = download_with_ytdlp(video_url)
    
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