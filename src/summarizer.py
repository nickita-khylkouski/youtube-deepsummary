#!/usr/bin/env python3
"""
YouTube Transcript Summarizer

A module that generates AI-powered summaries of YouTube transcripts using OpenAI's API.
Handles both chapter-aware and standard summarization with comprehensive formatting.
"""

import os
import re
import textwrap
from typing import List, Dict, Optional
from openai import OpenAI


class TranscriptSummarizer:
    """Handles transcript summarization using OpenAI's API"""
    
    def __init__(self):
        """Initialize the summarizer with OpenAI client and configuration"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.client = None
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4.1')
        self.max_tokens = int(os.getenv('OPENAI_MAX_TOKENS', '100000'))
        self.temperature = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
        
        # Initialize client lazily to avoid proxy conflicts during import
        if self.api_key:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenAI client with proper error handling"""
        if self.client is not None:
            return
        
        try:
            # Simple initialization with latest OpenAI version
            self.client = OpenAI(api_key=self.api_key)
            print("OpenAI client initialized successfully")
        except Exception as e:
            print(f"Warning: Failed to initialize OpenAI client: {e}")
            self.client = None
    
    def is_configured(self) -> bool:
        """Check if the summarizer is properly configured"""
        return self.api_key is not None and self.client is not None
    
    def format_text_for_readability(self, text: str) -> str:
        """Format text for better readability"""
        # Split text into lines
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append('')
                continue
            
            # Handle list items
            if line.startswith(('- ', '* ', '1. ', '2. ', '3. ')):
                formatted_lines.append(line)
            # Handle headers (markdown style)
            elif line.startswith('#'):
                formatted_lines.append(line)
            # Wrap long paragraphs
            else:
                wrapped = textwrap.fill(line, width=80, 
                                      break_long_words=False, 
                                      break_on_hyphens=False)
                formatted_lines.append(wrapped)
        
        return '\n'.join(formatted_lines)
    
    def create_summary_prompt(self, transcript_content: str, chapters: Optional[List[Dict]] = None) -> str:
        """Create a detailed prompt for summarization with enhanced chapter integration"""
        if chapters and len(chapters) > 1:
            # Enhanced prompt for videos with chapters - deeply integrate chapter structure
            chapter_info = "\n".join([f"- {ch.get('title', 'Chapter')} (starts at {self._format_timestamp(ch.get('time', 0))})" for ch in chapters])
            
            # Create chapter-specific content extraction
            chapter_content_prompts = []
            for i, chapter in enumerate(chapters):
                chapter_title = chapter.get('title', f'Chapter {i+1}')
                chapter_time = self._format_timestamp(chapter.get('time', 0))
                chapter_content_prompts.append(f"### {chapter_title} ({chapter_time})\nSummarize the key points, insights, and actionable advice from this chapter specifically.")
            
            chapter_summaries_section = "\n\n".join(chapter_content_prompts)
            
            prompt = f"""Please provide a comprehensive summary of this YouTube video transcript. This video has {len(chapters)} chapters with distinct topics. Please structure your response to deeply utilize the chapter organization.

## Overview
Provide a brief 2-3 sentence overview of what this video covers and how the chapters connect to tell a complete story.

## Chapter-by-Chapter Deep Dive
For each chapter below, provide a detailed summary focusing on:
- Core concepts and main points
- Key insights and takeaways specific to that chapter
- Actionable strategies or advice mentioned
- Important examples, statistics, or case studies
- How this chapter connects to the overall video theme

{chapter_summaries_section}

## Cross-Chapter Synthesis
Identify themes, concepts, or strategies that appear across multiple chapters and how they build upon each other.

Based on the chapter structure, outline how the video guides viewers through a learning journey from start to finish.

Highlight the most important points from across all chapters, noting which chapters they come from.

## Actionable Strategies by Chapter
Organize practical advice and strategies by their respective chapters for easy reference.

List any warnings or pitfalls mentioned, noting which chapters discuss them.

Any resources, tools, or next steps mentioned, organized by chapter when relevant.

Chapter structure for reference:
{chapter_info}

IMPORTANT: Use the chapter timestamps to understand the flow and organization of content. When mentioning insights or advice, reference the specific chapter it comes from to help readers navigate back to the source material.

Please analyze this transcript:

{transcript_content}"""
        else:
            # Standard prompt for videos without chapters or with only one chapter
            prompt = f"""Please provide a comprehensive summary of this YouTube video transcript. Structure your response in the following format:

## Overview
Brief 2-3 sentence summary of the video content.

## Main Topics Covered
List the primary themes and subjects discussed in the video.

## Key Takeaways & Insights
Extract the most important points, conclusions, and insights from the video.

## Actionable Strategies
List practical advice, steps, or strategies that viewers can implement.

## Specific Details & Examples
Include important statistics, case studies, examples, or specific details mentioned.

## Warnings & Common Mistakes
Note any pitfalls, warnings, or common mistakes discussed.

## Resources & Next Steps
List any resources, tools, or next steps mentioned for further learning.

Please analyze this transcript:

{transcript_content}"""
            
            if chapters:
                chapter_info = "\n".join([f"- {ch.get('title', 'Chapter')} (starts at {self._format_timestamp(ch.get('time', 0))})" for ch in chapters])
                prompt += f"\n\nChapter structure:\n{chapter_info}\n"
        
        return prompt
    
    def summarize_with_openai(self, transcript_content: str, chapters: Optional[List[Dict]] = None, video_id: str = None, video_info: Optional[Dict] = None) -> str:
        """Generate summary using OpenAI's chat completion API with enhanced chapter integration"""
        if not self.is_configured():
            raise Exception("OpenAI client not configured properly")
        
        # Enhanced processing for chapter-based content
        if chapters and len(chapters) > 1:
            # Parse transcript content and organize by chapters
            chapter_organized_content = self._organize_transcript_by_chapters_for_ai(transcript_content, chapters)
            prompt = self.create_summary_prompt(chapter_organized_content, chapters)
        else:
            prompt = self.create_summary_prompt(transcript_content, chapters)
        
        try:
            # Enhanced system prompt for chapter-aware summarization
            system_prompt = "You are a helpful assistant that creates clear, comprehensive summaries of educational video transcripts. When chapters are present, you excel at analyzing how content flows between chapters and identifying progressive learning patterns. Focus on extracting key insights, actionable advice, and important details while maintaining readability and respecting the chapter structure."
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature
            )
            
            summary = response.choices[0].message.content
            
            # Post-process summary with additional formatting
            summary = self._post_process_summary(summary, chapters, video_id, video_info)
            
            return summary
            
        except Exception as e:
            print(f"Error during OpenAI summarization: {e}")
            raise Exception(f"Failed to generate summary: {str(e)}")
    
    def _post_process_summary(self, summary: str, chapters: Optional[List[Dict]] = None, video_id: str = None, video_info: Optional[Dict] = None) -> str:
        """Post-process the generated summary with additional formatting"""
        # Add prefix sections if available
        prefix_sections = []
        
        # Add clickable chapters section if chapters and video_id are provided
        if chapters and video_id:
            chapters_section = self._create_clickable_chapters_section(chapters, video_id)
            prefix_sections.append(chapters_section)
        
        # Add video metadata section if available
        if video_info:
            metadata_section = self._create_metadata_section(video_info)
            prefix_sections.append(metadata_section)
        
        # Combine prefix sections with summary
        if prefix_sections:
            return "\n\n".join(prefix_sections) + "\n\n" + summary
        
        return summary
    
    def _create_clickable_chapters_section(self, chapters: List[Dict], video_id: str) -> str:
        """Create a clickable chapters section for the summary"""
        chapters_html = "📚 **Video Chapters** ({} chapters):\n\n".format(len(chapters))
        
        for chapter in chapters:
            title = chapter.get('title', 'Chapter')
            time_seconds = chapter.get('time', 0)
            timestamp = self._format_timestamp(time_seconds)
            
            # Create YouTube URL with timestamp
            youtube_url = f"https://www.youtube.com/watch?v={video_id}&t={int(time_seconds)}s"
            
            chapters_html += f"• [{title}]({youtube_url}) - {timestamp}\n"
        
        return chapters_html
    
    def _create_metadata_section(self, video_info: Dict) -> str:
        """Create a metadata section for the summary"""
        metadata = "📹 **Video Information**:\n\n"
        
        if video_info.get('title'):
            metadata += f"**Title**: {video_info['title']}\n"
        
        if video_info.get('channel_name'):
            metadata += f"**Channel**: {video_info['channel_name']}\n"
        
        if video_info.get('duration'):
            duration_formatted = self._format_timestamp(video_info['duration'])
            metadata += f"**Duration**: {duration_formatted}\n"
        
        if video_info.get('view_count'):
            metadata += f"**Views**: {video_info['view_count']:,}\n"
        
        return metadata
    
    def _organize_transcript_by_chapters_for_ai(self, transcript_content: str, chapters: List[Dict]) -> str:
        """Organize transcript content by chapters for AI processing"""
        if not chapters:
            return transcript_content
        
        # Parse transcript content to extract timing information
        lines = transcript_content.split('\n')
        timed_entries = []
        
        for line in lines:
            # Look for timestamp patterns [MM:SS] or [HH:MM:SS]
            timestamp_match = re.search(r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]', line)
            if timestamp_match:
                timestamp_str = timestamp_match.group(1)
                time_seconds = self._parse_timestamp_to_seconds(timestamp_str)
                text = line.replace(timestamp_match.group(0), '').strip()
                timed_entries.append({
                    'time': time_seconds,
                    'text': text
                })
        
        if not timed_entries:
            return transcript_content
        
        # Organize entries by chapters
        organized_content = ""
        
        for i, chapter in enumerate(chapters):
            chapter_start = chapter.get('time', 0)
            chapter_end = chapters[i + 1].get('time', float('inf')) if i + 1 < len(chapters) else float('inf')
            
            # Filter entries for this chapter
            chapter_entries = [
                entry for entry in timed_entries
                if chapter_start <= entry['time'] < chapter_end
            ]
            
            if chapter_entries:
                chapter_title = chapter.get('title', f'Chapter {i + 1}')
                chapter_time = self._format_timestamp(chapter_start)
                organized_content += f"\n=== {chapter_title} (starts at {chapter_time}) ===\n"
                
                # Add chapter content
                for entry in chapter_entries:
                    formatted_time = self._format_timestamp(entry['time'])
                    organized_content += f"[{formatted_time}] {entry['text']}\n"
        
        return organized_content if organized_content else transcript_content
    
    def _parse_timestamp_to_seconds(self, timestamp_str: str) -> int:
        """Parse timestamp string to seconds"""
        parts = timestamp_str.split(':')
        if len(parts) == 2:  # MM:SS
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        elif len(parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        else:
            return 0
    
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
    
    def summarize_transcript(self, transcript: List[Dict]) -> str:
        """
        Legacy method for backward compatibility
        Summarize a transcript without chapter information
        """
        # Convert transcript list to text format
        transcript_text = "\n".join([
            f"[{entry.get('formatted_time', '00:00')}] {entry.get('text', '')}" 
            for entry in transcript
        ])
        
        return self.summarize_with_openai(transcript_text)


# Global summarizer instance
summarizer = TranscriptSummarizer()


def summarize_transcript_with_chapters(transcript_content: str, chapters: Optional[List[Dict]] = None, video_id: str = None, video_info: Optional[Dict] = None) -> str:
    """
    Convenience function to summarize transcript using the global summarizer
    
    Args:
        transcript_content: Formatted transcript content
        chapters: List of chapter dictionaries (optional)
        video_id: YouTube video ID (optional)
        video_info: Video metadata (optional)
        
    Returns:
        Generated summary text
    """
    return summarizer.summarize_with_openai(transcript_content, chapters, video_id, video_info)


def summarize_transcript_simple(transcript: List[Dict]) -> str:
    """
    Convenience function for simple transcript summarization
    
    Args:
        transcript: List of transcript entries
        
    Returns:
        Generated summary text
    """
    return summarizer.summarize_transcript(transcript)