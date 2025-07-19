#!/usr/bin/env python3
"""
YouTube Transcript Summarizer (Legacy)

LEGACY MODULE: This module is deprecated. 
All summarization logic has been consolidated into src/summarizer.py.
This module now serves as a compatibility layer that imports and uses the new module.
"""

import os
import re
import textwrap
from typing import List, Dict, Optional
from .summarizer import TranscriptSummarizer as NewTranscriptSummarizer


class TranscriptSummarizer:
    """Legacy wrapper around the new TranscriptSummarizer in src/summarizer.py"""
    
    def __init__(self):
        """Initialize the legacy summarizer by wrapping the new one"""
        # Use the new summarizer implementation
        self._new_summarizer = NewTranscriptSummarizer()
        
        # Expose the same interface for backward compatibility
        self.api_key = self._new_summarizer.openai_api_key
        self.client = self._new_summarizer.client
        self.model = self._new_summarizer.model
        self.max_tokens = self._new_summarizer.max_tokens
        self.temperature = self._new_summarizer.temperature
    
    def _initialize_client(self):
        """Legacy method - now delegates to new summarizer"""
        # Delegate to the new summarizer
        self._new_summarizer._initialize_client()
        self.client = self._new_summarizer.client
    
    def format_text_for_readability(self, text: str) -> str:
        """Legacy method - delegates to new summarizer"""
        return self._new_summarizer.format_text_for_readability(text)
    
    def create_summary_prompt(self, transcript_content: str, chapters: Optional[List[Dict]] = None) -> str:
        """Legacy method - delegates to new summarizer"""
        return self._new_summarizer.create_summary_prompt(transcript_content, chapters)
    
    def summarize_transcript(self, transcript: List[Dict]) -> str:
        """Legacy method - delegates to new summarizer"""
        return self._new_summarizer.summarize_transcript(transcript)
    
    def summarize_with_openai(self, transcript_content: str, chapters: Optional[List[Dict]] = None, video_id: str = None, video_info: Optional[Dict] = None) -> str:
        """Legacy method - delegates to new summarizer"""
        return self._new_summarizer.summarize_with_openai(transcript_content, chapters, video_id, video_info)
    
    def _create_clickable_chapters_section(self, chapters: List[Dict], video_id: str) -> str:
        """Legacy method - delegates to new summarizer"""
        return self._new_summarizer._create_clickable_chapters_section(chapters, video_id)
    
    def _format_timestamp(self, seconds: float) -> str:
        """Legacy method - delegates to new summarizer"""
        return self._new_summarizer._format_timestamp(seconds)
    
    def _organize_transcript_by_chapters_for_ai(self, transcript_content: str, chapters: List[Dict]) -> str:
        """Legacy method - delegates to new summarizer"""
        return self._new_summarizer._organize_transcript_by_chapters_for_ai(transcript_content, chapters)

    def _create_video_info_section(self, video_info: Dict, video_id: str) -> str:
        """Legacy method - delegates to new summarizer"""
        return self._new_summarizer._create_video_info_section(video_info, video_id)
    
    def is_configured(self) -> bool:
        """Legacy method - delegates to new summarizer"""
        return self._new_summarizer.is_configured()


def format_transcript_for_display(transcript: List[Dict]) -> str:
    """Format transcript entries for display"""
    # Keep this utility function as it's not in the new summarizer
    formatted_lines = []
    for entry in transcript:
        time_str = entry.get('formatted_time', f"{int(entry.get('time', 0) // 60):02d}:{int(entry.get('time', 0) % 60):02d}")
        formatted_lines.append(f"[{time_str}] {entry['text']}")
    
    return "\n".join(formatted_lines)












