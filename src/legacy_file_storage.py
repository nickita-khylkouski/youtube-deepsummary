#!/usr/bin/env python3
"""
Legacy file-based transcript storage module with TTL support

DEPRECATED: This module has been replaced by database_storage.py which uses Supabase.
Only kept for historical reference and potential fallback scenarios.
"""

import os
import json
import time
from typing import Optional, Dict, List
from pathlib import Path


class LegacyFileStorage:
    """
    DEPRECATED: Legacy file-based storage for YouTube transcripts with TTL
    
    This class has been replaced by database_storage.py which uses Supabase for 
    persistent storage. Only kept for historical reference and potential fallback.
    """
    
    def __init__(self, cache_dir: str = "cache", ttl_hours: int = 24):
        """
        Initialize legacy file storage (DEPRECATED)
        
        Args:
            cache_dir: Directory to store cache files
            ttl_hours: Time to live in hours (default 24 hours = 1 day)
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_hours * 3600
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(exist_ok=True)
        
    def _get_cache_file(self, video_id: str) -> Path:
        """Get cache file path for video ID"""
        return self.cache_dir / f"{video_id}.json"
    
    def _is_cache_valid(self, cache_file: Path) -> bool:
        """Check if cache file exists and is not expired"""
        if not cache_file.exists():
            return False
        
        # Check if file is older than TTL
        file_age = time.time() - cache_file.stat().st_mtime
        return file_age < self.ttl_seconds
    
    def get(self, video_id: str) -> Optional[Dict]:
        """
        Get cached transcript data for video ID
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Cached data dict or None if not found/expired
        """
        cache_file = self._get_cache_file(video_id)
        
        if not self._is_cache_valid(cache_file):
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"Cache HIT for video {video_id}")
                return data
        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            print(f"Cache read error for {video_id}: {e}")
            # Remove corrupted cache file
            cache_file.unlink(missing_ok=True)
            return None
    
    def set(self, video_id: str, transcript: List[Dict], video_info: Dict, formatted_transcript: str):
        """
        Cache transcript data for video ID
        
        Args:
            video_id: YouTube video ID
            transcript: Raw transcript data
            video_info: Video metadata (title, chapters, etc.)
            formatted_transcript: Formatted readable transcript
        """
        cache_file = self._get_cache_file(video_id)
        
        cache_data = {
            'video_id': video_id,
            'timestamp': time.time(),
            'transcript': transcript,
            'video_info': video_info,
            'formatted_transcript': formatted_transcript
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                print(f"Cache SAVED for video {video_id}")
        except Exception as e:
            print(f"Cache write error for {video_id}: {e}")
    
    def clear_expired(self):
        """Remove expired cache files"""
        if not self.cache_dir.exists():
            return
        
        removed_count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            if not self._is_cache_valid(cache_file):
                cache_file.unlink(missing_ok=True)
                removed_count += 1
        
        if removed_count > 0:
            print(f"Removed {removed_count} expired cache files")
    
    def get_cache_info(self) -> Dict:
        """Get cache statistics"""
        if not self.cache_dir.exists():
            return {'total_files': 0, 'valid_files': 0, 'expired_files': 0}
        
        total_files = 0
        valid_files = 0
        expired_files = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            total_files += 1
            if self._is_cache_valid(cache_file):
                valid_files += 1
            else:
                expired_files += 1
        
        return {
            'total_files': total_files,
            'valid_files': valid_files,
            'expired_files': expired_files,
            'cache_dir': str(self.cache_dir),
            'ttl_hours': self.ttl_seconds / 3600
        }
    
    def get_all_cached_videos(self) -> List[Dict]:
        """Get list of all cached videos with metadata"""
        if not self.cache_dir.exists():
            return []
        
        cached_videos = []
        
        for cache_file in self.cache_dir.glob("*.json"):
            video_id = cache_file.stem
            
            # Check if cache is valid
            is_valid = self._is_cache_valid(cache_file)
            
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    video_info = data.get('video_info', {})
                    
                    # Calculate cache age
                    cache_timestamp = data.get('timestamp', 0)
                    cache_age_hours = (time.time() - cache_timestamp) / 3600
                    
                    cached_videos.append({
                        'video_id': video_id,
                        'title': video_info.get('title', 'Unknown Title'),
                        'uploader': video_info.get('uploader', 'Unknown Channel'),
                        'duration': video_info.get('duration'),
                        'chapters_count': len(video_info.get('chapters', [])) if video_info.get('chapters') else 0,
                        'transcript_entries': len(data.get('transcript', [])),
                        'cache_age_hours': round(cache_age_hours, 1),
                        'is_valid': is_valid,
                        'cache_timestamp': cache_timestamp,
                        'file_size': cache_file.stat().st_size
                    })
            except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
                # Include corrupted/unreadable files
                cached_videos.append({
                    'video_id': video_id,
                    'title': 'Error reading cache',
                    'uploader': 'Unknown',
                    'duration': None,
                    'chapters_count': 0,
                    'transcript_entries': 0,
                    'cache_age_hours': 0,
                    'is_valid': False,
                    'cache_timestamp': 0,
                    'file_size': cache_file.stat().st_size,
                    'error': str(e)
                })
        
        # Sort by cache timestamp (newest first)
        cached_videos.sort(key=lambda x: x['cache_timestamp'], reverse=True)
        
        return cached_videos


# Global legacy storage instance (DEPRECATED - use database_storage instead)
legacy_file_storage = LegacyFileStorage()