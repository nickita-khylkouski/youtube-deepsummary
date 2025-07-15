#!/usr/bin/env python3
"""
Snippet Manager Module

A module that handles business logic for memory snippets including grouping,
filtering, validation, and processing operations.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from .database_storage import database_storage


class SnippetManager:
    """Handles business logic for memory snippets"""
    
    def __init__(self):
        """Initialize the snippet manager"""
        self.storage = database_storage
    
    def create_snippet(self, video_id: str, snippet_text: str, 
                      context_before: str = None, context_after: str = None, 
                      tags: List[str] = None) -> Dict[str, Any]:
        """
        Create a new memory snippet with validation
        
        Args:
            video_id: YouTube video ID
            snippet_text: The selected text content
            context_before: Text before the selected content
            context_after: Text after the selected content
            tags: List of tags for organization
            
        Returns:
            Dictionary with success status and message
        """
        # Validate inputs
        validation_result = self._validate_snippet_input(video_id, snippet_text)
        if not validation_result['valid']:
            return {
                'success': False,
                'message': validation_result['message']
            }
        
        # Clean and process the snippet
        processed_snippet = self._process_snippet_content(snippet_text, context_before, context_after)
        processed_tags = self._process_tags(tags)
        
        # Save to database
        success = self.storage.save_memory_snippet(
            video_id=video_id,
            snippet_text=processed_snippet['text'],
            context_before=processed_snippet['context_before'],
            context_after=processed_snippet['context_after'],
            tags=processed_tags
        )
        
        return {
            'success': success,
            'message': 'Snippet saved successfully' if success else 'Failed to save snippet'
        }
    
    def get_snippets_by_video(self, video_id: str, limit: int = 100) -> List[Dict]:
        """
        Get snippets for a specific video
        
        Args:
            video_id: YouTube video ID
            limit: Maximum number of snippets to return
            
        Returns:
            List of snippet dictionaries
        """
        snippets = self.storage.get_memory_snippets(video_id=video_id, limit=limit)
        return self._enrich_snippets_with_metadata(snippets)
    
    def get_snippets_by_channel(self, channel_id: str, limit: int = 1000) -> List[Dict]:
        """
        Get snippets for a specific channel
        
        Args:
            channel_id: YouTube channel ID
            limit: Maximum number of snippets to return
            
        Returns:
            List of snippet dictionaries filtered by channel
        """
        all_snippets = self.storage.get_memory_snippets(limit=limit)
        
        # Filter by channel_id
        channel_snippets = [
            snippet for snippet in all_snippets 
            if snippet.get('channel_id') == channel_id
        ]
        
        return self._enrich_snippets_with_metadata(channel_snippets)
    
    def get_snippets_by_channel_handle(self, channel_handle: str, limit: int = 1000) -> Dict[str, Any]:
        """
        Get snippets for a specific channel by handle
        
        Args:
            channel_handle: YouTube channel handle
            limit: Maximum number of snippets to return
            
        Returns:
            Dictionary with channel info and filtered snippets
        """
        # Get channel info by handle
        channel_info = self.storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return {
                'success': False,
                'message': f'Channel not found: {channel_handle}',
                'channel_info': None,
                'snippets': []
            }
        
        # Get snippets for this channel
        snippets = self.get_snippets_by_channel(channel_info['channel_id'], limit)
        
        return {
            'success': True,
            'channel_info': channel_info,
            'snippets': snippets,
            'total_count': len(snippets)
        }
    
    def group_snippets_by_channel(self, snippets: List[Dict]) -> List[Dict]:
        """
        Group snippets by channel with statistics
        
        Args:
            snippets: List of snippet dictionaries
            
        Returns:
            List of channel groups with video and snippet counts
        """
        channel_groups = {}
        
        for snippet in snippets:
            channel_name = snippet.get('channel_name', 'Unknown Channel')
            channel_id = snippet.get('channel_id')
            handle = snippet.get('handle')
            
            # Use channel_id as key if available, otherwise channel_name
            channel_key = channel_id if channel_id else channel_name
            
            if channel_key not in channel_groups:
                channel_groups[channel_key] = {
                    'channel_name': channel_name,
                    'channel_id': channel_id,
                    'handle': handle,
                    'thumbnail_url': snippet.get('channel_thumbnail_url'),
                    'videos': {},
                    'total_snippets': 0,
                    'latest_date': ''
                }
            
            # Process video information
            video_id = snippet['video_id']
            if video_id not in channel_groups[channel_key]['videos']:
                video_info = self._extract_video_info_from_snippet(snippet)
                channel_groups[channel_key]['videos'][video_id] = {
                    'video_info': video_info,
                    'video_id': video_id,
                    'snippet_count': 0
                }
            
            channel_groups[channel_key]['videos'][video_id]['snippet_count'] += 1
            channel_groups[channel_key]['total_snippets'] += 1
            
            # Track latest snippet date for channel
            snippet_date = snippet.get('created_at', '')
            if snippet_date > channel_groups[channel_key]['latest_date']:
                channel_groups[channel_key]['latest_date'] = snippet_date
        
        # Convert to list and add video counts
        channels = []
        for channel_key, group in channel_groups.items():
            group['video_count'] = len(group['videos'])
            channels.append(group)
        
        # Sort channels by latest snippet date (newest first)
        channels.sort(key=lambda x: x['latest_date'], reverse=True)
        
        return channels
    
    def group_snippets_by_video(self, snippets: List[Dict]) -> List[Dict]:
        """
        Group snippets by video with sorting
        
        Args:
            snippets: List of snippet dictionaries
            
        Returns:
            List of video groups with sorted snippets
        """
        grouped_snippets = {}
        
        for snippet in snippets:
            video_id = snippet['video_id']
            if video_id not in grouped_snippets:
                video_info = self._extract_video_info_from_snippet(snippet)
                grouped_snippets[video_id] = {
                    'video_info': video_info,
                    'video_id': video_id,
                    'channel_name': snippet.get('channel_name'),
                    'channel_id': snippet.get('channel_id'),
                    'handle': snippet.get('handle'),
                    'url_path': snippet.get('youtube_videos', {}).get('url_path'),
                    'snippets': []
                }
            grouped_snippets[video_id]['snippets'].append(snippet)
        
        # Convert to list and sort
        video_groups = []
        for video_id, group in grouped_snippets.items():
            # Sort snippets within group by creation date (newest first)
            group['snippets'].sort(key=lambda x: x.get('created_at', ''), reverse=True)
            # Use the newest snippet's date for group sorting
            group['latest_date'] = group['snippets'][0].get('created_at', '') if group['snippets'] else ''
            video_groups.append(group)
        
        # Sort groups by latest snippet date (newest first)
        video_groups.sort(key=lambda x: x['latest_date'], reverse=True)
        
        return video_groups
    
    def update_snippet_tags(self, snippet_id: str, tags: List[str]) -> Dict[str, Any]:
        """
        Update tags for a snippet
        
        Args:
            snippet_id: Snippet ID
            tags: List of new tags
            
        Returns:
            Dictionary with success status and message
        """
        processed_tags = self._process_tags(tags)
        
        success = self.storage.update_memory_snippet_tags(snippet_id, processed_tags)
        
        return {
            'success': success,
            'message': 'Tags updated successfully' if success else 'Failed to update tags'
        }
    
    def delete_snippet(self, snippet_id: str) -> Dict[str, Any]:
        """
        Delete a snippet
        
        Args:
            snippet_id: Snippet ID
            
        Returns:
            Dictionary with success status and message
        """
        success = self.storage.delete_memory_snippet(snippet_id)
        
        return {
            'success': success,
            'message': 'Snippet deleted successfully' if success else 'Failed to delete snippet'
        }
    
    def get_snippet_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about snippets
        
        Returns:
            Dictionary with snippet statistics
        """
        stats = self.storage.get_memory_snippets_stats()
        
        # Add additional computed statistics
        all_snippets = self.storage.get_memory_snippets(limit=10000)  # Large limit for stats
        
        if all_snippets:
            # Calculate tags statistics
            all_tags = []
            for snippet in all_snippets:
                tags = snippet.get('tags', [])
                if tags:
                    all_tags.extend(tags)
            
            unique_tags = list(set(all_tags))
            
            # Calculate average snippets per video
            videos_with_snippets = {}
            for snippet in all_snippets:
                video_id = snippet['video_id']
                if video_id not in videos_with_snippets:
                    videos_with_snippets[video_id] = 0
                videos_with_snippets[video_id] += 1
            
            avg_snippets_per_video = (
                sum(videos_with_snippets.values()) / len(videos_with_snippets)
                if videos_with_snippets else 0
            )
            
            stats.update({
                'total_tags': len(all_tags),
                'unique_tags': len(unique_tags),
                'average_snippets_per_video': round(avg_snippets_per_video, 2),
                'most_common_tags': self._get_most_common_tags(all_tags)
            })
        
        return stats
    
    def search_snippets(self, query: str, limit: int = 100) -> List[Dict]:
        """
        Search snippets by text content
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching snippets
        """
        all_snippets = self.storage.get_memory_snippets(limit=limit * 2)  # Get more for filtering
        
        # Simple text search (case-insensitive)
        query_lower = query.lower()
        matching_snippets = []
        
        for snippet in all_snippets:
            snippet_text = snippet.get('snippet_text', '').lower()
            context_before = snippet.get('context_before', '').lower()
            context_after = snippet.get('context_after', '').lower()
            tags = [tag.lower() for tag in snippet.get('tags', [])]
            
            if (query_lower in snippet_text or 
                query_lower in context_before or 
                query_lower in context_after or 
                any(query_lower in tag for tag in tags)):
                matching_snippets.append(snippet)
        
        # Limit results and sort by relevance (creation date for now)
        matching_snippets.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return matching_snippets[:limit]
    
    def _validate_snippet_input(self, video_id: str, snippet_text: str) -> Dict[str, Any]:
        """Validate snippet input data"""
        if not video_id:
            return {'valid': False, 'message': 'Video ID is required'}
        
        if not snippet_text or not snippet_text.strip():
            return {'valid': False, 'message': 'Snippet text is required'}
        
        if len(video_id) != 11:
            return {'valid': False, 'message': 'Invalid video ID format'}
        
        if len(snippet_text) > 10000:  # Reasonable limit
            return {'valid': False, 'message': 'Snippet text too long (max 10000 characters)'}
        
        return {'valid': True, 'message': 'Valid input'}
    
    def _process_snippet_content(self, snippet_text: str, context_before: str = None, 
                                context_after: str = None) -> Dict[str, str]:
        """Process and clean snippet content"""
        # Clean up whitespace and formatting
        cleaned_text = snippet_text.strip()
        cleaned_context_before = context_before.strip() if context_before else None
        cleaned_context_after = context_after.strip() if context_after else None
        
        return {
            'text': cleaned_text,
            'context_before': cleaned_context_before,
            'context_after': cleaned_context_after
        }
    
    def _process_tags(self, tags: List[str] = None) -> List[str]:
        """Process and clean tags"""
        if not tags:
            return []
        
        # Clean tags: remove empty strings, strip whitespace, convert to lowercase
        processed_tags = []
        for tag in tags:
            if tag and isinstance(tag, str):
                cleaned_tag = tag.strip().lower()
                if cleaned_tag and cleaned_tag not in processed_tags:
                    processed_tags.append(cleaned_tag)
        
        return processed_tags
    
    def _enrich_snippets_with_metadata(self, snippets: List[Dict]) -> List[Dict]:
        """Add additional metadata to snippets"""
        # For now, just return as-is since database already includes metadata
        # Could be extended to add computed fields, formatting, etc.
        return snippets
    
    def _extract_video_info_from_snippet(self, snippet: Dict) -> Dict:
        """Extract video information from snippet data"""
        video_info = snippet.get('youtube_videos', {})
        if not video_info:
            video_info = {
                'title': f'Video {snippet["video_id"]}',
                'channel_name': snippet.get('channel_name', 'Unknown Channel'),
                'thumbnail_url': f"https://img.youtube.com/vi/{snippet['video_id']}/maxresdefault.jpg"
            }
        return video_info
    
    def _get_most_common_tags(self, all_tags: List[str], limit: int = 10) -> List[Dict]:
        """Get most common tags with counts"""
        from collections import Counter
        
        tag_counts = Counter(all_tags)
        most_common = tag_counts.most_common(limit)
        
        return [{'tag': tag, 'count': count} for tag, count in most_common]


# Global snippet manager instance
snippet_manager = SnippetManager()


def create_memory_snippet(video_id: str, snippet_text: str, 
                         context_before: str = None, context_after: str = None, 
                         tags: List[str] = None) -> Dict[str, Any]:
    """
    Convenience function to create a memory snippet
    
    Args:
        video_id: YouTube video ID
        snippet_text: The selected text content
        context_before: Text before the selected content
        context_after: Text after the selected content
        tags: List of tags for organization
        
    Returns:
        Dictionary with success status and message
    """
    return snippet_manager.create_snippet(video_id, snippet_text, context_before, context_after, tags)


def get_snippets_for_video(video_id: str, limit: int = 100) -> List[Dict]:
    """
    Convenience function to get snippets for a video
    
    Args:
        video_id: YouTube video ID
        limit: Maximum number of snippets to return
        
    Returns:
        List of snippet dictionaries
    """
    return snippet_manager.get_snippets_by_video(video_id, limit)


def get_snippets_for_channel_handle(channel_handle: str, limit: int = 1000) -> Dict[str, Any]:
    """
    Convenience function to get snippets for a channel by handle
    
    Args:
        channel_handle: YouTube channel handle
        limit: Maximum number of snippets to return
        
    Returns:
        Dictionary with channel info and snippets
    """
    return snippet_manager.get_snippets_by_channel_handle(channel_handle, limit)


def search_memory_snippets(query: str, limit: int = 100) -> List[Dict]:
    """
    Convenience function to search snippets
    
    Args:
        query: Search query
        limit: Maximum number of results
        
    Returns:
        List of matching snippets
    """
    return snippet_manager.search_snippets(query, limit)