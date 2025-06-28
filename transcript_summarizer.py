#!/usr/bin/env python3
"""
YouTube Transcript Summarizer

A module that generates AI-powered summaries of YouTube transcripts using OpenAI's API.
Based on the implementation from youtube-summarizer project.
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
        api_key = os.getenv('OPENAI_API_KEY')
        self.client = None
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI client: {e}")
        self.model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        self.max_tokens = int(os.getenv('OPENAI_MAX_TOKENS', '2000'))
        self.temperature = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
    
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
        """Create a detailed prompt for summarization"""
        prompt = f"""Please provide a comprehensive summary of this YouTube video transcript. Structure your response with the following sections:

## Overview
Provide a brief 2-3 sentence overview of what this video is about.

## Main Topics Covered
List the primary topics or themes discussed in the video.

## Key Takeaways & Insights
Highlight the most important points, insights, or conclusions from the video.

## Actionable Strategies
If applicable, list any practical advice, strategies, or steps mentioned.

## Specific Details & Examples
Include important specific details, examples, statistics, or case studies mentioned.

## Warnings & Common Mistakes
If the video mentions any warnings, pitfalls, or common mistakes to avoid.

## Resources & Next Steps
Any resources, tools, or next steps mentioned in the video.

Here is the transcript to summarize:

{transcript_content}
"""
        
        if chapters:
            chapter_info = "\n".join([f"- {ch.get('title', 'Chapter')} ({ch.get('time', 'Unknown time')})" for ch in chapters])
            prompt += f"\n\nChapter structure:\n{chapter_info}\n"
        
        return prompt
    
    def summarize_transcript(self, transcript: List[Dict]) -> str:
        """
        Summarize a transcript using OpenAI's API
        
        Args:
            transcript: List of transcript entries with 'text', 'time', etc.
            
        Returns:
            Formatted summary string
        """
        # Convert transcript to text
        transcript_text = "\n".join([f"[{entry.get('formatted_time', entry.get('time', '00:00'))}] {entry['text']}" 
                                   for entry in transcript])
        
        # Check if transcript is too long and truncate if needed
        max_chars = 12000  # Leave room for prompt overhead
        if len(transcript_text) > max_chars:
            transcript_text = transcript_text[:max_chars] + "\n\n[Transcript truncated due to length...]"
        
        return self.summarize_with_openai(transcript_text)
    
    def summarize_with_openai(self, transcript_content: str, chapters: Optional[List[Dict]] = None) -> str:
        """Generate summary using OpenAI's chat completion API"""
        if not self.client:
            raise Exception("OpenAI API key not configured")
            
        prompt = self.create_summary_prompt(transcript_content, chapters)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates clear, comprehensive summaries of educational video transcripts. Focus on extracting key insights, actionable advice, and important details while maintaining readability."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            summary = response.choices[0].message.content.strip()
            formatted_summary = self.format_text_for_readability(summary)
            return formatted_summary
            
        except Exception as e:
            raise Exception(f"Error generating summary: {str(e)}")
    
    def is_configured(self) -> bool:
        """Check if OpenAI API key is configured"""
        return self.client is not None


def format_transcript_for_display(transcript: List[Dict]) -> str:
    """Format transcript entries for display"""
    formatted_lines = []
    for entry in transcript:
        time_str = entry.get('formatted_time', f"{int(entry.get('time', 0) // 60):02d}:{int(entry.get('time', 0) % 60):02d}")
        formatted_lines.append(f"[{time_str}] {entry['text']}")
    
    return "\n".join(formatted_lines)