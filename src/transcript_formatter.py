#!/usr/bin/env python3
"""
Transcript Formatter

A module that handles formatting of YouTube transcripts for better readability
with support for chapter organization and paragraph grouping.
"""

import re
from typing import List, Dict, Optional


class TranscriptFormatter:
    """Handles formatting of transcript data for improved readability"""
    
    def __init__(self):
        """Initialize the formatter"""
        pass
    
    def format_for_readability(self, transcript: List[Dict], chapters: Optional[List[Dict]] = None) -> str:
        """
        Format transcript for improved readability with paragraph grouping and chapter organization
        
        Args:
            transcript: List of transcript entries with time, text, and formatted_time
            chapters: Optional list of chapter dictionaries
            
        Returns:
            Formatted transcript text with proper organization
        """
        # If chapters are available, organize by chapters
        if chapters:
            return self._organize_by_chapters(transcript, chapters)
        else:
            # Standard formatting without chapters
            return self._group_into_paragraphs(transcript)
    
    def _organize_by_chapters(self, transcript: List[Dict], chapters: List[Dict]) -> str:
        """
        Organize transcript content by video chapters for better structure
        
        Args:
            transcript: List of transcript entries
            chapters: List of chapter dictionaries
            
        Returns:
            Chapter-organized transcript text
        """
        if not chapters:
            return self._group_into_paragraphs(transcript)
        
        organized_sections = []
        
        for i, chapter in enumerate(chapters):
            chapter_start = chapter.get('time', 0)
            chapter_end = chapters[i + 1].get('time', float('inf')) if i + 1 < len(chapters) else float('inf')
            
            # Filter transcript entries for this chapter
            chapter_entries = [
                entry for entry in transcript
                if chapter_start <= entry.get('time', 0) < chapter_end
            ]
            
            if chapter_entries:
                # Format chapter header with anchor
                chapter_title = chapter.get('title', f'Chapter {i + 1}')
                chapter_time = self._format_timestamp(chapter_start)
                chapter_id = f"chapter-{int(chapter_start)}"
                header = f"\n<a id='{chapter_id}'></a>## {chapter_title} [{chapter_time}]\n"
                
                # Format chapter content
                chapter_content = self._group_into_paragraphs(chapter_entries, sentences_per_paragraph=4)
                organized_sections.append(header + chapter_content)
        
        return "\n".join(organized_sections)
    
    def _group_into_paragraphs(self, transcript: List[Dict], sentences_per_paragraph: int = 5) -> str:
        """
        Group transcript entries into readable paragraphs
        
        Args:
            transcript: List of transcript entries
            sentences_per_paragraph: Number of sentences per paragraph
            
        Returns:
            Paragraph-grouped transcript text
        """
        if not transcript:
            return ""
        
        paragraphs = []
        current_paragraph = []
        sentence_count = 0
        
        for entry in transcript:
            text = entry.get('text', '').strip()
            
            if not text:
                continue
            
            current_paragraph.append(text)
            
            # Count actual sentences based on punctuation
            sentences_in_text = len(re.findall(r'[.!?]+', text))
            sentence_count += max(1, sentences_in_text)  # At least count the entry itself
            
            # Natural break detection
            ends_with_period = text.rstrip().endswith('.')
            ends_with_strong = text.rstrip().endswith(('!', '?'))
            starts_transition = bool(re.match(r'^(so|now|well|okay|alright|anyway|first|second|next)\b', text.lower().strip()))
            
            # Break when we have enough sentences AND a natural break point
            has_enough_content = sentence_count >= sentences_per_paragraph
            has_natural_break = ends_with_period or ends_with_strong or starts_transition
            
            if has_enough_content and has_natural_break:
                paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []
                sentence_count = 0
        
        # Add remaining content
        if current_paragraph:
            paragraphs.append(" ".join(current_paragraph))
        
        return "\n\n".join(paragraphs)
    
    def format_with_timestamps(self, transcript: List[Dict], interval_seconds: int = 30) -> str:
        """
        Format transcript with timestamps at regular intervals
        
        Args:
            transcript: List of transcript entries
            interval_seconds: Interval between timestamps in seconds
            
        Returns:
            Timestamp-formatted transcript text
        """
        if not transcript:
            return ""
        
        formatted_lines = []
        last_timestamp = -1
        current_line = []
        
        for entry in transcript:
            text = entry.get('text', '').strip()
            time = entry.get('time', 0)
            formatted_time = entry.get('formatted_time', self._format_timestamp(time))
            
            if not text:
                continue
            
            # Add timestamp if enough time has passed
            if time >= last_timestamp + interval_seconds:
                # Finish current line if it has content
                if current_line:
                    formatted_lines.append(" ".join(current_line))
                    current_line = []
                
                # Start new line with timestamp
                current_line.append(f"[{formatted_time}]")
                last_timestamp = time
            
            current_line.append(text)
        
        # Add remaining content
        if current_line:
            formatted_lines.append(" ".join(current_line))
        
        return "\n".join(formatted_lines)
    
    def format_as_srt(self, transcript: List[Dict]) -> str:
        """
        Format transcript as SRT subtitle format
        
        Args:
            transcript: List of transcript entries
            
        Returns:
            SRT-formatted transcript text
        """
        if not transcript:
            return ""
        
        srt_entries = []
        
        for i, entry in enumerate(transcript, 1):
            text = entry.get('text', '').strip()
            start_time = entry.get('time', 0)
            
            # Calculate end time (use next entry's start time or add 3 seconds)
            if i < len(transcript):
                end_time = transcript[i].get('time', start_time + 3)
            else:
                end_time = start_time + 3
            
            # Format timestamps for SRT
            start_srt = self._seconds_to_srt_timestamp(start_time)
            end_srt = self._seconds_to_srt_timestamp(end_time)
            
            srt_entry = f"{i}\n{start_srt} --> {end_srt}\n{text}\n"
            srt_entries.append(srt_entry)
        
        return "\n".join(srt_entries)
    
    def _seconds_to_srt_timestamp(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def _format_timestamp(self, seconds) -> str:
        """Format seconds into readable timestamp"""
        # Convert to int to handle both int and float inputs
        seconds = int(seconds) if seconds is not None else 0
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def create_chapter_navigation(self, chapters: List[Dict], video_id: str = None) -> str:
        """
        Create a chapter navigation section
        
        Args:
            chapters: List of chapter dictionaries
            video_id: YouTube video ID for creating links
            
        Returns:
            Chapter navigation HTML/markdown
        """
        if not chapters:
            return ""
        
        nav_html = "## 📚 Chapters\n\n"
        
        for i, chapter in enumerate(chapters, 1):
            title = chapter.get('title', f'Chapter {i}')
            time_seconds = chapter.get('time', 0)
            timestamp = self._format_timestamp(time_seconds)
            
            if video_id:
                # Create YouTube URL with timestamp
                youtube_url = f"https://www.youtube.com/watch?v={video_id}&t={int(time_seconds)}s"
                nav_html += f"{i}. [{title}]({youtube_url}) - {timestamp}\n"
            else:
                # Create anchor link
                chapter_id = f"chapter-{int(time_seconds)}"
                nav_html += f"{i}. [{title}](#{chapter_id}) - {timestamp}\n"
        
        return nav_html
    
    def extract_key_quotes(self, transcript: List[Dict], min_length: int = 50) -> List[str]:
        """
        Extract potentially important quotes from transcript
        
        Args:
            transcript: List of transcript entries
            min_length: Minimum length for quotes
            
        Returns:
            List of extracted quotes
        """
        quotes = []
        
        for entry in transcript:
            text = entry.get('text', '').strip()
            
            if len(text) >= min_length:
                # Look for complete sentences
                sentences = re.split(r'[.!?]+', text)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) >= min_length:
                        quotes.append(sentence)
        
        return quotes


# Global formatter instance
transcript_formatter = TranscriptFormatter()


def format_transcript_for_readability(transcript: List[Dict], chapters: Optional[List[Dict]] = None) -> str:
    """
    Convenience function to format transcript using the global formatter
    
    Args:
        transcript: List of transcript entries
        chapters: Optional list of chapters
        
    Returns:
        Formatted transcript text
    """
    return transcript_formatter.format_for_readability(transcript, chapters)