#!/usr/bin/env python3
"""
YouTube Chapter Extractor

A module that handles chapter extraction from YouTube videos using yt-dlp
and provides fallback methods for chapter detection.
"""

import os
import re
from typing import List, Dict, Optional
from src.proxy_manager import proxy_manager


class ChapterExtractor:
    """Handles chapter extraction from YouTube videos with proxy rotation"""
    
    def __init__(self):
        """Initialize the chapter extractor with proxy configuration"""
        self.max_retries = 3
    
    def extract_video_info(self, video_id: str) -> Dict[str, any]:
        """
        Extract comprehensive video information including title, chapters, and metadata using yt-dlp
        with proxy rotation support
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary containing video information including chapters
        """
        print(f"🎬 Extracting video info for: {video_id}")
        
        try:
            import yt_dlp
            print(f"📦 yt-dlp imported successfully")
            
            # Try with proxy rotation
            for attempt in range(self.max_retries):
                try:
                    # Get current proxy for yt-dlp
                    proxy_url = proxy_manager.get_current_proxy_for_ytdlp()
                    
                    # Configure yt-dlp options
                    ydl_opts = {
                        'quiet': True,
                        'no_warnings': True,
                        'extract_flat': False,
                    }
                    
                    # Add proxy configuration if available
                    if proxy_url:
                        ydl_opts['proxy'] = proxy_url
                        proxy_info = proxy_manager.get_proxy_info()
                        print(f"🌐 yt-dlp attempt {attempt + 1}: Using proxy {proxy_info['current_proxy']}")
                    else:
                        print(f"🔄 yt-dlp attempt {attempt + 1}: No proxy configured")
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        video_info = ydl.extract_info(
                            f'https://www.youtube.com/watch?v={video_id}', 
                            download=False
                        )
                        
                        # Extract title
                        title = video_info.get('title', 'Unknown Title')
                        
                        # Extract chapters
                        chapters = video_info.get('chapters', [])
                        formatted_chapters = None
                        
                        if chapters:
                            formatted_chapters = []
                            for chapter in chapters:
                                formatted_chapters.append({
                                    'title': chapter.get('title', 'Unknown Chapter'),
                                    'time': chapter.get('start_time', 0)
                                })
                            print(f"📋 Found {len(formatted_chapters)} chapters")
                        else:
                            print("📋 No chapters found in video")
                        
                        result = {
                            'title': title,
                            'chapters': formatted_chapters,
                            'duration': video_info.get('duration'),
                            'channel_name': video_info.get('channel', video_info.get('uploader', 'Unknown Channel')),
                            'channel_id': video_info.get('channel_id'),
                            'description': video_info.get('description', ''),
                            'view_count': video_info.get('view_count'),
                            'like_count': video_info.get('like_count'),
                            'upload_date': video_info.get('upload_date'),
                            'thumbnail': video_info.get('thumbnail'),
                            'tags': video_info.get('tags', [])
                        }
                        
                        print(f"✅ Successfully extracted video info: {title}")
                        return result
                        
                except Exception as e:
                    print(f"🔴 yt-dlp attempt {attempt + 1} failed: {str(e)}")
                    
                    if attempt < self.max_retries - 1:
                        # Mark proxy as failed and rotate to next one
                        proxy_manager.mark_proxy_failed()
                        print(f"🔄 Rotating to next proxy for retry...")
                    else:
                        print(f"❌ All {self.max_retries} yt-dlp attempts failed")
                        raise e
                
        except ImportError:
            print("⚠️ yt-dlp not available, falling back to description parsing")
            return self._extract_info_fallback(video_id)
        except Exception as e:
            print(f"🔴 Error extracting video info with yt-dlp: {e}")
            return self._extract_info_fallback(video_id)
    
    def extract_chapters_only(self, video_id: str) -> Optional[List[Dict]]:
        """
        Extract only chapter information from a video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of chapters or None if no chapters found
        """
        video_info = self.extract_video_info(video_id)
        return video_info.get('chapters')
    
    def _extract_info_fallback(self, video_id: str) -> Dict[str, any]:
        """
        Fallback method to extract basic video info without yt-dlp
        This is a basic implementation that could be enhanced with web scraping
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Basic video information dictionary
        """
        print(f"Using fallback method for video {video_id}")
        return {
            'title': f'Video {video_id}',
            'chapters': None,
            'duration': None,
            'channel_name': 'Unknown Channel',
            'channel_id': None,
            'description': '',
            'view_count': None,
            'like_count': None,
            'upload_date': None,
            'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
            'tags': []
        }
    
    def parse_chapters_from_description(self, description: str) -> Optional[List[Dict]]:
        """
        Parse chapters from video description text
        
        Args:
            description: Video description text
            
        Returns:
            List of parsed chapters or None if no chapters found
        """
        if not description:
            return None
        
        # Common timestamp patterns
        timestamp_patterns = [
            r'(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–—]\s*(.+)',  # MM:SS - Title or HH:MM:SS - Title
            r'(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)',         # MM:SS Title or HH:MM:SS Title
            r'(\d{1,2}:\d{2}(?::\d{2})?)\s*[:\-–—]\s*(.+)', # MM:SS: Title or MM:SS - Title
        ]
        
        chapters = []
        lines = description.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            for pattern in timestamp_patterns:
                match = re.search(pattern, line)
                if match:
                    timestamp_str = match.group(1)
                    title = match.group(2).strip()
                    
                    # Convert timestamp to seconds
                    time_seconds = self._timestamp_to_seconds(timestamp_str)
                    
                    chapters.append({
                        'title': title,
                        'time': time_seconds
                    })
                    break
        
        # Sort chapters by time and return only if we have multiple chapters
        if len(chapters) >= 2:
            chapters.sort(key=lambda x: x['time'])
            return chapters
        
        return None
    
    def _timestamp_to_seconds(self, timestamp_str: str) -> int:
        """
        Convert timestamp string to seconds
        
        Args:
            timestamp_str: Timestamp in format MM:SS or HH:MM:SS
            
        Returns:
            Time in seconds
        """
        parts = timestamp_str.split(':')
        if len(parts) == 2:  # MM:SS
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        elif len(parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        else:
            return 0
    
    def validate_chapters(self, chapters: List[Dict], video_duration: Optional[int] = None) -> List[Dict]:
        """
        Validate and clean up chapter data
        
        Args:
            chapters: List of chapter dictionaries
            video_duration: Video duration in seconds (optional)
            
        Returns:
            Cleaned and validated chapter list
        """
        if not chapters:
            return []
        
        # Remove duplicates and sort by time
        seen_times = set()
        valid_chapters = []
        
        for chapter in chapters:
            time = chapter.get('time', 0)
            title = chapter.get('title', '').strip()
            
            # Skip if no title or duplicate time
            if not title or time in seen_times:
                continue
            
            # Skip if time is beyond video duration
            if video_duration and time > video_duration:
                continue
            
            seen_times.add(time)
            valid_chapters.append({
                'title': title,
                'time': time
            })
        
        # Sort by time
        valid_chapters.sort(key=lambda x: x['time'])
        
        return valid_chapters
    
    def format_chapter_timestamp(self, seconds) -> str:
        """
        Format seconds into readable timestamp
        
        Args:
            seconds: Time in seconds (int or float)
            
        Returns:
            Formatted timestamp string
        """
        # Convert to int to handle both int and float inputs
        seconds = int(seconds) if seconds is not None else 0
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"


# Global chapter extractor instance
chapter_extractor = ChapterExtractor()


def extract_video_info(video_id: str) -> Dict[str, any]:
    """
    Convenience function to extract video info using the global extractor
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        Dictionary containing video information
    """
    return chapter_extractor.extract_video_info(video_id)


def extract_video_chapters(video_id: str) -> Optional[List[Dict]]:
    """
    Convenience function to extract only chapters using the global extractor
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        List of chapters or None
    """
    return chapter_extractor.extract_chapters_only(video_id)