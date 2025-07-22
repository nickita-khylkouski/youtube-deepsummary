"""
Chat Manager Module
Handles core chat business logic including session management, message processing,
and AI response generation following modular architecture principles.
"""

import uuid
from typing import Dict, List, Optional, Any
from .database_storage import database_storage
from .summarizer import summarizer
from .conversation_context import conversation_context
from .chat_formatter import chat_formatter


class ChatManager:
    """
    Core chat management functionality following modular architecture principles.
    
    Responsibilities:
    - Session management (create, load, delete)
    - Message processing and validation
    - AI response generation coordination
    - Chat history management
    """
    
    def __init__(self):
        self.default_model = 'gpt-4.1'
    
    def create_chat_session(self, channel_id: str) -> str:
        """Create a new chat session for a channel"""
        return str(uuid.uuid4())
    
    def send_message(self, channel_id: str, user_message: str, 
                    session_id: Optional[str] = None, 
                    model: str = None) -> Dict[str, Any]:
        """
        Process a user message and generate AI response
        
        Args:
            channel_id: YouTube channel ID
            user_message: User's message content
            session_id: Optional session ID (creates new if None)
            model: AI model to use (defaults to gpt-4.1)
            
        Returns:
            Dictionary with response data or error information
        """
        try:
            # Validate inputs
            if not channel_id or not user_message:
                return {'error': 'Missing required fields: channel_id, message'}
            
            # Generate session ID if not provided
            if not session_id:
                session_id = self.create_chat_session(channel_id)
            
            # Use default model if not specified
            if not model:
                model = self.default_model
            
            # Validate channel exists
            channel_info = database_storage.get_channel_by_id(channel_id)
            if not channel_info:
                return {'error': 'Channel not found'}
            
            # Save user message
            user_saved = database_storage.save_channel_chat_message(
                channel_id=channel_id,
                session_id=session_id,
                message_type='user',
                content=user_message,
                model_used=model
            )
            
            if not user_saved:
                return {'error': 'Failed to save user message. Please ensure the channel_chat table exists.'}
            
            # Build conversation context
            context = conversation_context.build_channel_context(channel_id)
            if not context:
                return {'error': 'No AI summaries available for this channel'}
            
            # Get chat history for this session
            chat_history = database_storage.get_channel_chat_history(channel_id, session_id, limit=10)
            
            # Generate AI response
            ai_response = self._generate_ai_response(
                user_message=user_message,
                context=context,
                chat_history=chat_history,
                channel_info=channel_info,
                model=model
            )
            
            if 'error' in ai_response:
                return ai_response
            
            # Save AI response
            ai_saved = database_storage.save_channel_chat_message(
                channel_id=channel_id,
                session_id=session_id,
                message_type='assistant',
                content=ai_response['content'],
                model_used=model,
                context_summary=ai_response.get('context_summary', '')
            )
            
            if not ai_saved:
                return {'error': 'Failed to save AI response'}
            
            return {
                'response': ai_response['content'],
                'session_id': session_id,
                'model_used': model,
                'context_used': ai_response.get('context_count', 0)
            }
            
        except Exception as e:
            return {'error': f'Chat processing failed: {str(e)}'}
    
    def _generate_ai_response(self, user_message: str, context: Dict[str, Any], 
                             chat_history: List[Dict], channel_info: Dict,
                             model: str) -> Dict[str, Any]:
        """
        Generate AI response using the specified model
        
        Args:
            user_message: User's message
            context: Channel context data
            chat_history: Previous chat messages
            channel_info: Channel information
            model: AI model to use
            
        Returns:
            Dictionary with AI response or error
        """
        try:
            # Create chat prompt
            prompt = chat_formatter.create_chat_prompt(
                user_message=user_message,
                context=context,
                chat_history=chat_history,
                channel_info=channel_info
            )
            
            # Generate response using appropriate AI service
            if model.startswith('claude') or model.startswith('anthropic'):
                response_text = self._generate_anthropic_response(prompt, model)
            else:
                response_text = self._generate_openai_response(prompt, model)
            
            return {
                'content': response_text,
                'context_summary': f"Used {context.get('summary_count', 0)} video summaries as context",
                'context_count': context.get('summary_count', 0)
            }
            
        except Exception as e:
            return {'error': f'AI response generation failed: {str(e)}'}
    
    def _generate_anthropic_response(self, prompt: str, model: str) -> str:
        """Generate response using Anthropic Claude"""
        if not summarizer.is_configured('anthropic'):
            raise Exception("Anthropic client not configured")
        
        response = summarizer.anthropic_client.messages.create(
            model=model,
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text
    
    def _generate_openai_response(self, prompt: str, model: str) -> str:
        """Generate response using OpenAI GPT"""
        if not summarizer.is_configured('openai'):
            raise Exception("OpenAI client not configured")
        
        response = summarizer.openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    
    def get_chat_history(self, channel_id: str, session_id: str) -> Dict[str, Any]:
        """Get chat history for a specific session"""
        try:
            # Validate channel exists
            channel_info = database_storage.get_channel_by_id(channel_id)
            if not channel_info:
                return {'error': 'Channel not found'}
            
            # Get chat history
            chat_history = database_storage.get_channel_chat_history(channel_id, session_id)
            
            return {
                'messages': chat_history,
                'channel_info': channel_info
            }
            
        except Exception as e:
            return {'error': f'Failed to get chat history: {str(e)}'}
    
    def get_chat_sessions(self, channel_id: str) -> Dict[str, Any]:
        """Get all chat sessions for a channel"""
        try:
            # Validate channel exists
            channel_info = database_storage.get_channel_by_id(channel_id)
            if not channel_info:
                return {'error': 'Channel not found'}
            
            # Get chat sessions
            sessions = database_storage.get_channel_chat_sessions(channel_id)
            
            return {
                'sessions': sessions,
                'channel_info': channel_info
            }
            
        except Exception as e:
            return {'error': f'Failed to get chat sessions: {str(e)}'}
    
    def delete_chat_session(self, session_id: str) -> Dict[str, Any]:
        """Delete a chat session"""
        try:
            success = database_storage.delete_channel_chat_session(session_id)
            
            if success:
                return {'message': 'Chat session deleted successfully'}
            else:
                return {'error': 'Failed to delete chat session'}
                
        except Exception as e:
            return {'error': f'Failed to delete chat session: {str(e)}'}
    
    def get_available_models(self) -> Dict[str, List[str]]:
        """Get available AI models"""
        try:
            return summarizer.get_available_models()
        except Exception as e:
            return {'error': f'Failed to get available models: {str(e)}'}


# Create singleton instance
chat_manager = ChatManager()