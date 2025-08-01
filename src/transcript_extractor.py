#!/usr/bin/env python3
"""
YouTube Transcript Extractor

A module that handles transcript extraction from YouTube videos using multiple methods
with fallback support and proxy configuration.
"""

import os
import time
import threading
from typing import List, Dict, Optional
from youtube_transcript_api import YouTubeTranscriptApi


class TranscriptExtractor:
    """Handles transcript extraction from YouTube videos"""
    
    def __init__(self):
        """Initialize the transcript extractor with proxy configuration"""
        self.proxy = os.getenv('YOUTUBE_PROXY')
        self.proxies = None
        if self.proxy:
            self.proxies = {
                'http': f'http://{self.proxy}',
                'https': f'http://{self.proxy}'
            }
    
    def extract_transcript(self, video_id: str, timeout: int = 30) -> List[Dict]:
        """
        Extract transcript for given video ID using proxy from environment with language fallback
        
        Args:
            video_id: YouTube video ID
            timeout: Timeout in seconds (default 30)
            
        Returns:
            List of transcript entries with time, text, and formatted_time
            
        Raises:
            Exception: If transcript extraction fails
        """
        try:
            if self.proxies:
                print(f"Using proxy: {self.proxy}")
            else:
                print("No proxy configured")
            
            print(f"Fetching transcript for video ID: {video_id} (timeout: {timeout}s)")
            start_time = time.time()
            
            # Use threading for timeout (works in Flask threads)
            result = {'transcript_list': None, 'language_used': None, 'error': None}
            
            def fetch_transcript():
                try:
                    # First try to get English transcript directly
                    try:
                        print(f"[{time.time() - start_time:.1f}s] Attempting English transcript...")
                        transcript_list = YouTubeTranscriptApi.get_transcript(
                            video_id, 
                            languages=['en'], 
                            proxies=self.proxies
                        )
                        print(f"[{time.time() - start_time:.1f}s] Successfully fetched English transcript with {len(transcript_list)} entries")
                        result['transcript_list'] = transcript_list
                        result['language_used'] = "en (English)"
                    except Exception as e:
                        print(f"[{time.time() - start_time:.1f}s] English transcript not available: {str(e)}")
                        
                        # If English not available, get the first available transcript
                        try:
                            print(f"[{time.time() - start_time:.1f}s] Attempting to find available transcripts...")
                            transcript_list_data = YouTubeTranscriptApi.list_transcripts(
                                video_id, 
                                proxies=self.proxies
                            )
                            
                            # Get list of available language codes
                            available_languages = []
                            for transcript in transcript_list_data:
                                available_languages.append(transcript.language_code)
                                print(f"[{time.time() - start_time:.1f}s] Available: {transcript.language} ({transcript.language_code})")
                            
                            if available_languages:
                                # Use the first available language code with the standard get_transcript method
                                first_lang = available_languages[0]
                                print(f"[{time.time() - start_time:.1f}s] Fetching {first_lang} transcript...")
                                transcript_list = YouTubeTranscriptApi.get_transcript(
                                    video_id, 
                                    languages=[first_lang], 
                                    proxies=self.proxies
                                )
                                
                                # Get language name for logging
                                first_transcript = next(iter(transcript_list_data))
                                result['transcript_list'] = transcript_list
                                result['language_used'] = f"{first_transcript.language} ({first_transcript.language_code})"
                                print(f"[{time.time() - start_time:.1f}s] Successfully fetched {result['language_used']} transcript with {len(transcript_list)} entries")
                            else:
                                raise Exception("No transcripts found")
                                
                        except Exception as fallback_error:
                            print(f"[{time.time() - start_time:.1f}s] Fallback transcript fetch failed: {str(fallback_error)}")
                            raise Exception(f"No transcripts available for this video: {str(fallback_error)}")
                            
                except Exception as e:
                    result['error'] = str(e)
            
            # Start the fetch in a thread
            thread = threading.Thread(target=fetch_transcript)
            thread.daemon = True
            thread.start()
            thread.join(timeout=timeout)
            
            # Check if thread completed
            if thread.is_alive():
                print(f"[{time.time() - start_time:.1f}s] TIMEOUT: Transcript extraction timed out after {timeout} seconds")
                raise Exception(f"Transcript extraction timed out after {timeout} seconds")
            
            # Check for errors
            if result['error']:
                raise Exception(result['error'])
            
            if not result['transcript_list']:
                raise Exception("Failed to fetch transcript - no result")
                
            transcript_list = result['transcript_list']
            language_used = result['language_used']
                
        except Exception as e:
            print(f"Error extracting transcript for {video_id}: {str(e)}")
            raise
            
        # Format the transcript
        print(f"[{time.time() - start_time:.1f}s] Formatting transcript...")
        formatted_transcript = []
        for entry in transcript_list:
            formatted_transcript.append({
                'time': entry['start'],
                'text': entry['text'],
                'formatted_time': f"{int(entry['start'] // 60):02d}:{int(entry['start'] % 60):02d}"
            })
        
        print(f"[{time.time() - start_time:.1f}s] Transcript language used: {language_used}")
        print(f"[{time.time() - start_time:.1f}s] Transcript extraction completed successfully")
        return formatted_transcript
    
    def get_available_languages(self, video_id: str) -> List[Dict]:
        """
        Get list of available transcript languages for a video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of available languages with codes and names
        """
        try:
            transcript_list_data = YouTubeTranscriptApi.list_transcripts(
                video_id, 
                proxies=self.proxies
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
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id, 
                languages=[language_code], 
                proxies=self.proxies
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