"""
Export manager for YouTube Deep Summary application.
Handles export of AI summaries and other data in various formats.
"""

import zipfile
import io
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from .database_storage import database_storage


class ExportManager:
    """
    Manager class for handling exports of AI summaries and other data.
    
    Follows the modular architecture principles:
    - Single responsibility: Only handles export operations
    - Independent component: Can be used standalone
    - Easy to test: Clear interfaces and methods
    - Easy to extend: New export formats can be added easily
    """
    
    def __init__(self):
        """Initialize the export manager."""
        pass
    
    def export_channel_summaries_zip(self, channel_handle: str, format_type: str = 'markdown') -> tuple[io.BytesIO, str]:
        """
        Export all AI summaries for a channel as a ZIP file with individual text files.
        
        Args:
            channel_handle: The channel handle (e.g., 'allin')
            format_type: Export format - 'markdown' (default) or 'plain' text
            
        Returns:
            tuple: (memory_file, zip_filename) where memory_file is the ZIP data
                  and zip_filename is the suggested filename
                  
        Raises:
            ValueError: If channel not found or no summaries available
            Exception: For other export errors
        """
        # Get channel info by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            raise ValueError(f'Channel not found: {channel_handle}')
        
        # Get videos for this channel
        channel_videos = database_storage.get_videos_by_channel(channel_id=channel_info['channel_id'])
        if not channel_videos:
            raise ValueError(f'No videos found for channel: {channel_handle}')
        
        # Collect summaries
        summaries = self._collect_channel_summaries(channel_videos)
        if not summaries:
            raise ValueError(f'No AI summaries found for channel: {channel_handle}')
        
        # Create ZIP file
        memory_file = self._create_summaries_zip(summaries, channel_info, format_type)
        
        # Generate filename
        safe_channel_name = self._sanitize_filename(channel_info['channel_name'])
        format_suffix = "_Plain" if format_type == 'plain' else ""
        zip_filename = f"{safe_channel_name}_AI_Summaries{format_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        return memory_file, zip_filename
    
    def _collect_channel_summaries(self, channel_videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Collect all summaries for the given channel videos.
        
        Args:
            channel_videos: List of video dictionaries from database
            
        Returns:
            List of summary dictionaries with metadata
        """
        summaries = []
        for video in channel_videos:
            video_id = video['video_id']
            summary = database_storage.get_summary(video_id)
            
            if summary:
                summaries.append({
                    'video_id': video_id,
                    'title': video['title'],
                    'summary': summary,
                    'created_at': video['created_at']
                })
        
        return summaries
    
    def _create_summaries_zip(self, summaries: List[Dict[str, Any]], channel_info: Dict[str, Any], format_type: str = 'markdown') -> io.BytesIO:
        """
        Create a ZIP file containing all summaries as individual text files.
        
        Args:
            summaries: List of summary dictionaries
            channel_info: Channel information dictionary
            format_type: Export format - 'markdown' or 'plain'
            
        Returns:
            BytesIO object containing the ZIP file data
        """
        memory_file = io.BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for summary_data in summaries:
                # Create filename and content
                filename = self._generate_summary_filename(summary_data)
                content = self._generate_summary_content(summary_data, channel_info, format_type)
                
                # Add file to ZIP
                zip_file.writestr(filename, content.encode('utf-8'))
        
        memory_file.seek(0)
        return memory_file
    
    def _generate_summary_filename(self, summary_data: Dict[str, Any]) -> str:
        """
        Generate a safe filename for a summary file.
        
        Args:
            summary_data: Summary data dictionary
            
        Returns:
            Safe filename string
        """
        safe_title = self._sanitize_filename(summary_data['title'])
        
        # Limit filename length
        if len(safe_title) > 100:
            safe_title = safe_title[:100] + '...'
        
        return f"{safe_title} - {summary_data['video_id']}.txt"
    
    def _generate_summary_content(self, summary_data: Dict[str, Any], channel_info: Dict[str, Any], format_type: str = 'markdown') -> str:
        """
        Generate the content for a summary text file.
        
        Args:
            summary_data: Summary data dictionary
            channel_info: Channel information dictionary
            format_type: Export format - 'markdown' or 'plain'
            
        Returns:
            Formatted content string
        """
        content = f"Video Title: {summary_data['title']}\n"
        content += f"Video ID: {summary_data['video_id']}\n"
        content += f"Video URL: https://www.youtube.com/watch?v={summary_data['video_id']}\n"
        content += f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"Channel: {channel_info['channel_name']}\n"
        content += f"Format: {format_type}\n"
        content += "=" * 80 + "\n\n"
        
        # Process summary content based on format type
        summary_content = summary_data['summary']
        if format_type == 'plain':
            summary_content = self._strip_markdown_formatting(summary_content)
        
        content += summary_content
        
        return content
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename by removing/replacing invalid characters.
        
        Args:
            filename: Original filename string
            
        Returns:
            Sanitized filename string
        """
        # Remove invalid characters
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        safe_filename = safe_filename.replace('  ', ' ').strip()
        
        return safe_filename
    
    def _strip_markdown_formatting(self, text: str) -> str:
        """
        Strip markdown formatting from text to create plain text version.
        
        Args:
            text: Text with markdown formatting
            
        Returns:
            Plain text without markdown formatting
        """
        if not text:
            return text
        
        # Remove HTML tags first (in case summary contains HTML)
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove markdown formatting
        # Headers (##, ###, etc.)
        text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
        
        # Bold and italic (**bold**, *italic*, __bold__, _italic_)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        
        # Links [text](url)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Code blocks ```code```
        text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
        
        # Inline code `code`
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # Strikethrough ~~text~~
        text = re.sub(r'~~([^~]+)~~', r'\1', text)
        
        # Bullet points (- or * or +)
        text = re.sub(r'^[\s]*[-*+]\s*', '• ', text, flags=re.MULTILINE)
        
        # Numbered lists
        text = re.sub(r'^[\s]*\d+\.\s*', '• ', text, flags=re.MULTILINE)
        
        # Blockquotes
        text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
        
        # Horizontal rules
        text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)
        
        # Clean up multiple newlines
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        
        # Clean up multiple spaces
        text = re.sub(r'  +', ' ', text)
        
        return text.strip()
    
    def get_export_statistics(self, channel_handle: str) -> Dict[str, Any]:
        """
        Get statistics about what can be exported for a channel.
        
        Args:
            channel_handle: The channel handle
            
        Returns:
            Dictionary with export statistics
        """
        try:
            channel_info = database_storage.get_channel_by_handle(channel_handle)
            if not channel_info:
                return {'error': 'Channel not found'}
            
            channel_videos = database_storage.get_videos_by_channel(channel_id=channel_info['channel_id'])
            if not channel_videos:
                return {'error': 'No videos found'}
            
            summaries = self._collect_channel_summaries(channel_videos)
            
            return {
                'channel_name': channel_info['channel_name'],
                'total_videos': len(channel_videos),
                'total_summaries': len(summaries),
                'exportable': len(summaries) > 0
            }
            
        except Exception as e:
            return {'error': str(e)}


# Global instance for easy importing
export_manager = ExportManager()