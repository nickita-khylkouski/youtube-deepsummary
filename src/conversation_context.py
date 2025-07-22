"""
Conversation Context Module
Handles building conversation context from channel summaries and video data
following modular architecture principles.
"""

from typing import Dict, List, Optional, Any
from .database_storage import database_storage


class ConversationContext:
    """
    Manages conversation context building from channel data.
    
    Responsibilities:
    - Build context from channel summaries
    - Format context for AI consumption
    - Manage context size and truncation
    - Provide context metadata
    """
    
    def __init__(self):
        self.max_context_length = 50000  # Rough token limit
        self.max_summaries_per_context = 20  # Limit number of summaries
    
    def build_channel_context(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Build conversation context from channel summaries
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            Dictionary with context data or None if no summaries available
        """
        try:
            # Get channel information
            channel_info = database_storage.get_channel_by_id(channel_id)
            if not channel_info:
                return None
            
            # Get channel summaries
            summaries = database_storage.get_channel_summaries_for_chat(channel_id)
            if not summaries:
                return None
            
            # Build context string
            context_data = self._build_context_string(summaries, channel_info)
            
            return {
                'context_text': context_data['context_text'],
                'summary_count': len(summaries),
                'total_summaries': len(summaries),
                'truncated': context_data['truncated'],
                'truncated_at': context_data.get('truncated_at', None),
                'channel_info': channel_info
            }
            
        except Exception as e:
            print(f"Error building channel context: {e}")
            return None
    
    def _build_context_string(self, summaries: List[Dict], channel_info: Dict) -> Dict[str, Any]:
        """
        Build formatted context string from summaries
        
        Args:
            summaries: List of video summaries
            channel_info: Channel information
            
        Returns:
            Dictionary with context text and metadata
        """
        # Start with channel header
        context_parts = [
            f"Channel: {channel_info['channel_name']}",
            f"Total videos with summaries: {len(summaries)}",
            "",
            "=== VIDEO SUMMARIES ===",
            ""
        ]
        
        current_length = len('\n'.join(context_parts))
        truncated = False
        truncated_at = None
        
        # Add summaries with length checking
        for i, summary in enumerate(summaries, 1):
            if i > self.max_summaries_per_context:
                truncated = True
                truncated_at = i - 1
                context_parts.append(f"... (truncated after {i-1} videos due to summary limit)")
                break
            
            video_title = summary.get('video_title', 'Unknown Title')
            summary_text = summary.get('summary_text', '')
            
            summary_block = f"Video {i}: {video_title}\nSummary: {summary_text}\n"
            
            # Check if adding this summary would exceed length limit
            if current_length + len(summary_block) > self.max_context_length:
                truncated = True
                truncated_at = i - 1
                context_parts.append(f"... (truncated after {i-1} videos due to length limit)")
                break
            
            context_parts.append(summary_block)
            current_length += len(summary_block)
        
        return {
            'context_text': '\n'.join(context_parts),
            'truncated': truncated,
            'truncated_at': truncated_at
        }
    
    def get_context_summary(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Get context summary information without building full context
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            Dictionary with context metadata
        """
        try:
            # Get channel information
            channel_info = database_storage.get_channel_by_id(channel_id)
            if not channel_info:
                return None
            
            # Get summary count
            summaries = database_storage.get_channel_summaries_for_chat(channel_id)
            
            return {
                'channel_name': channel_info['channel_name'],
                'summary_count': len(summaries),
                'has_context': len(summaries) > 0
            }
            
        except Exception as e:
            print(f"Error getting context summary: {e}")
            return None
    
    def validate_context_availability(self, channel_id: str) -> bool:
        """
        Check if context is available for a channel
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            True if context is available, False otherwise
        """
        try:
            summaries = database_storage.get_channel_summaries_for_chat(channel_id)
            return len(summaries) > 0
        except Exception as e:
            print(f"Error validating context availability: {e}")
            return False
    
    def get_context_stats(self, channel_id: str) -> Dict[str, Any]:
        """
        Get detailed context statistics
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            Dictionary with context statistics
        """
        try:
            # Get channel information
            channel_info = database_storage.get_channel_by_id(channel_id)
            if not channel_info:
                return {'error': 'Channel not found'}
            
            # Get summaries
            summaries = database_storage.get_channel_summaries_for_chat(channel_id)
            
            # Calculate statistics
            total_summaries = len(summaries)
            total_content_length = sum(len(s.get('summary_text', '')) for s in summaries)
            
            # Get model distribution
            models_used = {}
            for summary in summaries:
                model = summary.get('model_used', 'unknown')
                models_used[model] = models_used.get(model, 0) + 1
            
            return {
                'channel_name': channel_info['channel_name'],
                'total_summaries': total_summaries,
                'total_content_length': total_content_length,
                'average_summary_length': total_content_length / total_summaries if total_summaries > 0 else 0,
                'models_used': models_used,
                'context_available': total_summaries > 0
            }
            
        except Exception as e:
            return {'error': f'Failed to get context stats: {str(e)}'}


# Create singleton instance
conversation_context = ConversationContext()