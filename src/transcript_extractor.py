#!/usr/bin/env python3
"""
YouTube Transcript Extractor

A module that handles transcript extraction from YouTube videos using multiple methods
with fallback support and proxy configuration including yt-dlp support.
"""

import os
import subprocess
import json
import re
import tempfile
from typing import List, Dict, Optional, Tuple
from youtube_transcript_api import YouTubeTranscriptApi
from src.proxy_manager import proxy_manager


class TranscriptExtractor:
    """Handles transcript extraction from YouTube videos with proxy rotation"""
    
    def __init__(self):
        """Initialize the transcript extractor with proxy configuration"""
        self.max_retries = 3
        self.ytdlp_available = self._check_ytdlp_available()
    
    def _check_ytdlp_available(self) -> bool:
        """Check if yt-dlp is available"""
        try:
            result = subprocess.run(['yt-dlp', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def extract_transcript(self, video_id: str) -> List[Dict]:
        """
        Extract transcript for given video ID using multiple methods with proxy rotation
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of transcript entries with time, text, and formatted_time
            
        Raises:
            Exception: If transcript extraction fails with all methods
        """
        print(f"🎬 Fetching transcript for video ID: {video_id}")
        
        # Try youtube-transcript-api first (faster and more reliable)
        try:
            result = self._extract_with_youtube_transcript_api(video_id)
            if result:
                print("✅ Successfully extracted transcript using youtube-transcript-api")
                return result
        except Exception as e:
            print(f"🔴 youtube-transcript-api failed: {str(e)}")
        
        # Fallback to yt-dlp if available
        if self.ytdlp_available:
            print("🔄 Falling back to yt-dlp method...")
            try:
                result = self._extract_with_ytdlp(video_id)
                if result:
                    print("✅ Successfully extracted transcript using yt-dlp")
                    return result
            except Exception as e:
                print(f"🔴 yt-dlp method failed: {str(e)}")
        else:
            print("⚠️ yt-dlp not available, skipping fallback")
        
        raise Exception("All transcript extraction methods failed")
    
    def _extract_with_youtube_transcript_api(self, video_id: str) -> List[Dict]:
        """
        Extract transcript using youtube-transcript-api with proxy rotation
        """
        for attempt in range(self.max_retries):
            try:
                # Get current proxy configuration
                proxies = proxy_manager.get_current_proxy_config()
                
                if proxies:
                    proxy_info = proxy_manager.get_proxy_info()
                    print(f"🌐 Attempt {attempt + 1}: Using proxy {proxy_info['current_proxy']}")
                else:
                    print(f"🔄 Attempt {attempt + 1}: No proxy configured")
                
                # Try to get English transcript first
                try:
                    transcript_list = YouTubeTranscriptApi.get_transcript(
                        video_id, 
                        languages=['en'], 
                        proxies=proxies
                    )
                    language_used = "en (English)"
                    print(f"📝 Found English transcript with {len(transcript_list)} entries")
                    
                except Exception as e:
                    print(f"⚠️ English transcript not available: {str(e)}")
                    
                    # Try to get any available transcript
                    transcript_list_data = YouTubeTranscriptApi.list_transcripts(
                        video_id, 
                        proxies=proxies
                    )
                    
                    # Get first available transcript
                    available_languages = []
                    for transcript in transcript_list_data:
                        available_languages.append(transcript.language_code)
                        print(f"📋 Available: {transcript.language} ({transcript.language_code})")
                    
                    if available_languages:
                        first_lang = available_languages[0]
                        transcript_list = YouTubeTranscriptApi.get_transcript(
                            video_id, 
                            languages=[first_lang], 
                            proxies=proxies
                        )
                        
                        # Get language name for logging
                        first_transcript = next(iter(transcript_list_data))
                        language_used = f"{first_transcript.language} ({first_transcript.language_code})"
                        print(f"📝 Using {language_used} transcript with {len(transcript_list)} entries")
                    else:
                        raise Exception("No transcripts found for this video")
                
                # Format the transcript
                formatted_transcript = []
                for entry in transcript_list:
                    formatted_transcript.append({
                        'time': entry['start'],
                        'text': entry['text'],
                        'formatted_time': f"{int(entry['start'] // 60):02d}:{int(entry['start'] % 60):02d}"
                    })
                
                print(f"✅ Transcript extraction successful using {language_used}")
                return formatted_transcript
                
            except Exception as e:
                print(f"🔴 Attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    # Mark proxy as failed and rotate to next one
                    proxy_manager.mark_proxy_failed()
                    print(f"🔄 Rotating to next proxy for retry...")
                else:
                    print(f"❌ All {self.max_retries} attempts failed with youtube-transcript-api")
        
        raise Exception("youtube-transcript-api extraction failed after all retries")
    
    def _extract_with_ytdlp(self, video_id: str) -> List[Dict]:
        """
        Extract transcript using yt-dlp with proxy rotation
        """
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        for attempt in range(self.max_retries):
            try:
                # Get current proxy for yt-dlp
                proxy_url = proxy_manager.get_current_proxy_for_ytdlp()
                
                if proxy_url:
                    proxy_info = proxy_manager.get_proxy_info()
                    print(f"🌐 yt-dlp attempt {attempt + 1}: Using proxy {proxy_info['current_proxy']}")
                else:
                    print(f"🔄 yt-dlp attempt {attempt + 1}: No proxy configured")
                
                # Build yt-dlp command
                with tempfile.TemporaryDirectory() as temp_dir:
                    cmd = [
                        'yt-dlp',
                        '--write-auto-sub',
                        '--sub-lang', 'en',
                        '--skip-download',
                        '--sub-format', 'vtt',
                        '--output', f'{temp_dir}/%(id)s.%(ext)s',
                        video_url
                    ]
                    
                    # Add proxy if available
                    if proxy_url:
                        cmd.extend(['--proxy', proxy_url])
                    
                    print(f"🚀 Running yt-dlp command: {' '.join(cmd[:4])}... (proxy: {'yes' if proxy_url else 'no'})")
                    
                    # Run yt-dlp
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    
                    if result.returncode != 0:
                        raise Exception(f"yt-dlp failed with return code {result.returncode}: {result.stderr}")
                    
                    # Find the downloaded subtitle file
                    subtitle_files = []
                    for file in os.listdir(temp_dir):
                        if file.endswith('.vtt') and video_id in file:
                            subtitle_files.append(os.path.join(temp_dir, file))
                    
                    if not subtitle_files:
                        raise Exception("No subtitle file found after yt-dlp download")
                    
                    # Parse the VTT file
                    with open(subtitle_files[0], 'r', encoding='utf-8') as f:
                        vtt_content = f.read()
                    
                    transcript = self._parse_vtt_to_transcript(vtt_content)
                    print(f"✅ yt-dlp extracted {len(transcript)} transcript entries")
                    return transcript
                    
            except Exception as e:
                print(f"🔴 yt-dlp attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    # Mark proxy as failed and rotate to next one
                    proxy_manager.mark_proxy_failed()
                    print(f"🔄 Rotating to next proxy for yt-dlp retry...")
                else:
                    print(f"❌ All {self.max_retries} yt-dlp attempts failed")
        
        raise Exception("yt-dlp extraction failed after all retries")
    
    def _parse_vtt_to_transcript(self, vtt_content: str) -> List[Dict]:
        """
        Parse VTT subtitle content into transcript format
        """
        lines = vtt_content.split('\n')
        transcript = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for timestamp lines (format: 00:00:00.000 --> 00:00:05.000)
            if '-->' in line:
                try:
                    # Extract start time
                    start_time_str = line.split(' --> ')[0]
                    start_time = self._parse_vtt_timestamp(start_time_str)
                    
                    i += 1
                    
                    # Get the text lines
                    text_lines = []
                    while i < len(lines) and lines[i].strip() and '-->' not in lines[i]:
                        text_line = lines[i].strip()
                        # Remove HTML tags
                        text_line = re.sub(r'<[^>]+>', '', text_line)
                        if text_line:
                            text_lines.append(text_line)
                        i += 1
                    
                    if text_lines:
                        text = ' '.join(text_lines)
                        transcript.append({
                            'time': start_time,
                            'text': text,
                            'formatted_time': f"{int(start_time // 60):02d}:{int(start_time % 60):02d}"
                        })
                        
                except Exception as e:
                    print(f"⚠️ Error parsing VTT timestamp: {e}")
                    i += 1
            else:
                i += 1
        
        return transcript
    
    def _parse_vtt_timestamp(self, timestamp_str: str) -> float:
        """
        Parse VTT timestamp (00:00:05.000) to seconds
        """
        # Handle both formats: HH:MM:SS.mmm and MM:SS.mmm
        parts = timestamp_str.split(':')
        
        if len(parts) == 3:  # HH:MM:SS.mmm
            hours, minutes, seconds = parts
            total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        elif len(parts) == 2:  # MM:SS.mmm
            minutes, seconds = parts
            total_seconds = int(minutes) * 60 + float(seconds)
        else:
            raise ValueError(f"Invalid timestamp format: {timestamp_str}")
        
        return total_seconds
    
    def get_available_languages(self, video_id: str) -> List[Dict]:
        """
        Get list of available transcript languages for a video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of available languages with codes and names
        """
        try:
            proxies = proxy_manager.get_current_proxy_config()
            transcript_list_data = YouTubeTranscriptApi.list_transcripts(
                video_id, 
                proxies=proxies
            )
            
            languages = []
            for transcript in transcript_list_data:
                languages.append({
                    'code': transcript.language_code,
                    'name': transcript.language,
                    'is_generated': transcript.is_generated,
                    'is_translatable': transcript.is_translatable
                })
            
            return languages
            
        except Exception as e:
            print(f"Error getting available languages: {str(e)}")
            return []
    
    def extract_transcript_in_language(self, video_id: str, language_code: str) -> List[Dict]:
        """
        Extract transcript in a specific language
        
        Args:
            video_id: YouTube video ID
            language_code: ISO language code (e.g., 'en', 'es', 'fr')
            
        Returns:
            List of transcript entries
        """
        try:
            proxies = proxy_manager.get_current_proxy_config()
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id, 
                languages=[language_code], 
                proxies=proxies
            )
            
            # Format the transcript
            formatted_transcript = []
            for entry in transcript_list:
                formatted_transcript.append({
                    'time': entry['start'],
                    'text': entry['text'],
                    'formatted_time': f"{int(entry['start'] // 60):02d}:{int(entry['start'] % 60):02d}"
                })
            
            return formatted_transcript
            
        except Exception as e:
            raise Exception(f"Error downloading transcript in {language_code}: {str(e)}")


# Global transcript extractor instance
transcript_extractor = TranscriptExtractor()


def extract_transcript(video_id: str) -> List[Dict]:
    """
    Convenience function to extract transcript using the global extractor
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        List of transcript entries
    """
    return transcript_extractor.extract_transcript(video_id)


def get_available_transcript_languages(video_id: str) -> List[Dict]:
    """
    Convenience function to get available transcript languages
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        List of available languages
    """
    return transcript_extractor.get_available_languages(video_id)