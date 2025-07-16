"""
Chat Formatter Module
Handles chat message formatting, prompt creation, and response processing
following modular architecture principles.
"""

from typing import Dict, List, Any, Optional
import re


class ChatFormatter:
    """
    Manages chat message formatting and prompt creation.
    
    Responsibilities:
    - Create AI chat prompts with context
    - Format chat messages for display
    - Handle message validation and cleanup
    - Process AI responses for presentation
    """
    
    def __init__(self):
        self.system_role = "knowledgeable AI assistant"
        self.max_history_messages = 10
    
    def create_chat_prompt(self, user_message: str, context: Dict[str, Any], 
                          chat_history: List[Dict], channel_info: Dict) -> str:
        """
        Create a chat prompt with context and history
        
        Args:
            user_message: User's current message
            context: Channel context data
            chat_history: Previous chat messages
            channel_info: Channel information
            
        Returns:
            Formatted prompt string for AI
        """
        # Build the base prompt
        prompt_parts = [
            f'You are a {self.system_role} having a conversation about the YouTube channel "{channel_info["channel_name"]}".',
            "",
            "You have complete access to AI-generated summaries from all videos on this channel. Use this information to answer questions naturally and conversationally.",
            "",
            "ROLE: You are a helpful assistant discussing this YouTube channel's content with a user.",
            "",
            "INSTRUCTIONS:",
            "- Answer questions directly based on the video summaries provided",
            "- Be conversational and friendly",
            "- Provide specific examples from the videos when relevant",
            "- Do NOT ask for transcripts, additional information, or clarification",
            "- You already have all the information you need",
            "",
            "CHANNEL SUMMARIES:",
            context['context_text'],
            "",
            "CONVERSATION HISTORY:"
        ]
        
        # Add recent chat history
        recent_history = chat_history[-self.max_history_messages:] if chat_history else []
        for message in recent_history:
            role = message['message_type']
            content = message['content']
            if role == 'user':
                prompt_parts.append(f"Human: {content}")
            else:
                prompt_parts.append(f"Assistant: {content}")
        
        # Add current user message
        prompt_parts.extend([
            "",
            f"Human: {user_message}",
            "",
            "Assistant:"
        ])
        
        return '\n'.join(prompt_parts)
    
    def format_message_for_display(self, content: str, message_type: str = 'assistant') -> str:
        """
        Format message content for display in chat interface
        
        Args:
            content: Raw message content
            message_type: Type of message ('user' or 'assistant')
            
        Returns:
            Formatted message content
        """
        if not content:
            return ''
        
        # Clean up any transcript-related artifacts for assistant messages
        if message_type == 'assistant':
            content = self._clean_assistant_response(content)
        
        # Format markdown elements
        formatted = self._format_markdown(content)
        
        # Handle lists
        formatted = self._format_lists(formatted)
        
        # Handle paragraphs
        formatted = self._format_paragraphs(formatted)
        
        return formatted
    
    def _clean_assistant_response(self, content: str) -> str:
        """Clean up assistant response from transcript-related artifacts"""
        # Remove transcript-related prompts
        cleaned = re.sub(r'.*Please provide the transcript[^.]*\.', '', content, flags=re.IGNORECASE)
        cleaned = re.sub(r'.*Once you send the transcript[^.]*\.', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'.*I need the transcript[^.]*\.', '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _format_markdown(self, content: str) -> str:
        """Format basic markdown elements"""
        # Bold text
        content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
        
        # Italic text
        content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
        
        # Headers
        content = re.sub(r'^#{1,3}\s+(.+)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
        
        return content
    
    def _format_lists(self, content: str) -> str:
        """Format bullet points and lists"""
        # Convert bullet points to list items
        content = re.sub(r'^[-•]\s+(.+)$', r'<li>\1</li>', content, flags=re.MULTILINE)
        
        # Wrap consecutive list items in ul tags
        content = re.sub(r'(<li>.*?</li>(?:\s*<li>.*?</li>)*)', r'<ul>\1</ul>', content, flags=re.DOTALL)
        
        return content
    
    def _format_paragraphs(self, content: str) -> str:
        """Format paragraphs and line breaks"""
        # Handle paragraph breaks
        content = re.sub(r'\n\n+', '</p><p>', content)
        
        # Handle single line breaks
        content = re.sub(r'\n', '<br>', content)
        
        # Wrap in paragraph tags if not already formatted
        if not re.search(r'<ul>|<h\d>|<p>', content):
            content = f'<p>{content}</p>'
        
        return content
    
    def validate_message(self, message: str) -> Dict[str, Any]:
        """
        Validate a chat message
        
        Args:
            message: Message content to validate
            
        Returns:
            Dictionary with validation results
        """
        if not message:
            return {'valid': False, 'error': 'Message cannot be empty'}
        
        if len(message.strip()) == 0:
            return {'valid': False, 'error': 'Message cannot be empty'}
        
        if len(message) > 10000:  # Reasonable message length limit
            return {'valid': False, 'error': 'Message too long (max 10,000 characters)'}
        
        return {'valid': True}
    
    def create_session_preview(self, first_message: str, max_length: int = 100) -> str:
        """
        Create a preview of the first message for session display
        
        Args:
            first_message: First message in the session
            max_length: Maximum preview length
            
        Returns:
            Formatted preview string
        """
        if not first_message:
            return "New conversation"
        
        # Clean message
        cleaned = re.sub(r'<[^>]+>', '', first_message)  # Remove HTML tags
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace
        cleaned = cleaned.strip()
        
        # Truncate if necessary
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length] + '...'
        
        return cleaned
    
    def format_error_message(self, error: str) -> str:
        """
        Format error messages for display
        
        Args:
            error: Error message
            
        Returns:
            Formatted error message
        """
        return f'<div class="error-message"><i class="fas fa-exclamation-triangle"></i> {error}</div>'
    
    def format_system_message(self, message: str) -> str:
        """
        Format system messages for display
        
        Args:
            message: System message
            
        Returns:
            Formatted system message
        """
        return f'<div class="system-message"><i class="fas fa-info-circle"></i> {message}</div>'
    
    def extract_message_metadata(self, message: str) -> Dict[str, Any]:
        """
        Extract metadata from message content
        
        Args:
            message: Message content
            
        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            'word_count': len(message.split()),
            'character_count': len(message),
            'has_markdown': bool(re.search(r'[\*#\-•]', message)),
            'has_urls': bool(re.search(r'https?://', message)),
            'has_mentions': bool(re.search(r'@\w+', message))
        }
        
        return metadata


# Create singleton instance
chat_formatter = ChatFormatter()