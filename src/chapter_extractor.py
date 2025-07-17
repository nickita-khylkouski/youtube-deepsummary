#!/usr/bin/env python3
"""
YouTube Chapter Extractor

A module that handles chapter extraction from YouTube videos using yt-dlp.
"""

import os
import re
from typing import List, Dict, Optional


class ChapterExtractor:
    """Handles chapter extraction from YouTube videos using yt-dlp"""
    
    def __init__(self):
        """Initialize the chapter extractor with proxy configuration"""
        self.proxy = os.getenv('YOUTUBE_PROXY')
    
    def extract_chapters(self, video_id: str) -> Optional[List[Dict]]:
        """
        Extract chapter information from a YouTube video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of chapters or None if no chapters found
        """
        try:
            import yt_dlp
            print(f"Extracting chapters using yt-dlp for {video_id}")
            
            # Configure yt-dlp options for chapter extraction only
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            # Add proxy configuration if available
            if self.proxy:
                ydl_opts['proxy'] = f'http://{self.proxy}'
                print(f"Using proxy for yt-dlp chapter extraction: {self.proxy}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(
                    f'https://www.youtube.com/watch?v={video_id}', 
                    download=False
                )
                
                # Extract and format chapters
                chapters = video_info.get('chapters', [])
                if chapters:
                    formatted_chapters = []
                    for chapter in chapters:
                        formatted_chapters.append({
                            'title': chapter.get('title', 'Unknown Chapter'),
                            'time': chapter.get('start_time', 0)
                        })
                    
                    # Validate and clean chapters
                    video_duration = video_info.get('duration')
                    return self.validate_chapters(formatted_chapters, video_duration)
                
                return None
                
        except ImportError:
            print("yt-dlp not available for chapter extraction")
            return None
        except Exception as e:
            print(f"Error extracting chapters with yt-dlp for {video_id}: {e}")
            return None
    
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


def extract_video_chapters(video_id: str) -> Optional[List[Dict]]:
    """
    Convenience function to extract chapters using the global extractor
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        List of chapters or None
    """
    return chapter_extractor.extract_chapters(video_id)