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
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.client = None
        self.model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        self.max_tokens = int(os.getenv('OPENAI_MAX_TOKENS', '2000'))
        self.temperature = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
        
        # Initialize client lazily to avoid proxy conflicts during import
        if self.api_key:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenAI client with proper error handling"""
        if self.client is not None:
            return
        
        try:
            # Import fresh OpenAI module to avoid any cached proxy settings
            import importlib
            import openai
            importlib.reload(openai)
            from openai import OpenAI as FreshOpenAI
            
            # Create OpenAI client with explicit http_client to bypass proxy issues
            import httpx
            http_client = httpx.Client(proxies=None)  # Explicitly disable proxies
            
            self.client = FreshOpenAI(
                api_key=self.api_key,
                http_client=http_client
            )
            print("OpenAI client initialized successfully")
        except Exception as e:
            print(f"Warning: Failed to initialize OpenAI client with custom http_client: {e}")
            # Fallback: try basic initialization
            try:
                from openai import OpenAI as BasicOpenAI
                self.client = BasicOpenAI(api_key=self.api_key)
                print("OpenAI client initialized with fallback method")
            except Exception as e2:
                print(f"Warning: Fallback OpenAI initialization also failed: {e2}")
                self.client = None
    
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
        # Ensure client is initialized
        if not self.client:
            self._initialize_client()
        
        if not self.client:
            raise Exception("OpenAI API key not configured or client initialization failed")
            
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
        return bool(self.api_key)


def format_transcript_for_display(transcript: List[Dict]) -> str:
    """Format transcript entries for display"""
    formatted_lines = []
    for entry in transcript:
        time_str = entry.get('formatted_time', f"{int(entry.get('time', 0) // 60):02d}:{int(entry.get('time', 0) % 60):02d}")
        formatted_lines.append(f"[{time_str}] {entry['text']}")
    
    return "\n".join(formatted_lines)