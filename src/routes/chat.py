"""
Channel chat routes for the YouTube Deep Summary application
Enables GPT-like conversations using channel summaries as context
"""
import uuid
import json
from flask import Blueprint, request, jsonify, render_template
from ..database_storage import database_storage, DatabaseStorage
from ..summarizer import summarizer

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/@<channel_handle>/chat')
def channel_chat_page(channel_handle):
    """Display chat interface for a specific channel"""
    try:
        # Get channel info by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return render_template('error.html', 
                                 error_message=f"Channel not found: {channel_handle}"), 404
        
        # Get recent chat sessions for this channel
        recent_sessions = database_storage.get_channel_chat_sessions(channel_info['channel_id'])
        
        # Get available AI models
        available_models = summarizer.get_available_models()
        
        return render_template('channel_chat.html',
                             channel_info=channel_info,
                             channel_handle=channel_handle,
                             recent_sessions=recent_sessions,
                             available_models=available_models)
        
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading chat: {str(e)}"), 500


@chat_bp.route('/api/chat/send', methods=['POST'])
def send_chat_message():
    """Send a chat message and get AI response based on channel context"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'channel_id' not in data or 'message' not in data:
            return jsonify({'error': 'Missing required fields: channel_id, message'}), 400
        
        channel_id = data['channel_id']
        user_message = data['message']
        session_id = data.get('session_id')
        model = data.get('model', 'gpt-4.1')
        
        # Generate new session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Validate channel exists
        channel_info = database_storage.get_channel_by_id(channel_id)
        if not channel_info:
            return jsonify({'error': 'Channel not found'}), 404
        
        # Save user message
        user_message_saved = database_storage.save_channel_chat_message(
            channel_id=channel_id,
            session_id=session_id,
            message_type='user',
            content=user_message,
            model_used=model
        )
        
        if not user_message_saved:
            return jsonify({'error': 'Failed to save user message. Please ensure the channel_chat table exists in your database. Run the SQL script in sql/create_channel_chat_table.sql to create it.'}), 500
        
        # Get channel context (all summaries for this channel)
        channel_summaries = database_storage.get_channel_summaries_for_chat(channel_id)
        
        # Build context from summaries
        context = _build_channel_context(channel_summaries, channel_info)
        
        # Get recent chat history for this session
        chat_history = database_storage.get_channel_chat_history(channel_id, session_id, limit=10)
        
        # Create chat prompt with context
        chat_prompt = _create_chat_prompt(user_message, context, chat_history, channel_info)
        
        # Generate AI response using direct chat method
        try:
            ai_response = _generate_chat_response(chat_prompt, model)
        except Exception as e:
            return jsonify({'error': f'AI response generation failed: {str(e)}'}), 500
        
        # Save AI response
        ai_message_saved = database_storage.save_channel_chat_message(
            channel_id=channel_id,
            session_id=session_id,
            message_type='assistant',
            content=ai_response,
            model_used=model,
            context_summary=f"Used {len(channel_summaries)} video summaries as context"
        )
        
        if not ai_message_saved:
            return jsonify({'error': 'Failed to save AI response'}), 500
        
        return jsonify({
            'response': ai_response,
            'session_id': session_id,
            'model_used': model,
            'context_used': len(channel_summaries)
        })
        
    except Exception as e:
        return jsonify({'error': f'Chat failed: {str(e)}'}), 500


@chat_bp.route('/api/chat/history/<channel_id>/<session_id>')
def get_chat_history(channel_id, session_id):
    """Get chat history for a specific channel and session"""
    try:
        # Validate channel exists
        channel_info = database_storage.get_channel_by_id(channel_id)
        if not channel_info:
            return jsonify({'error': 'Channel not found'}), 404
        
        # Get chat history
        chat_history = database_storage.get_channel_chat_history(channel_id, session_id)
        
        return jsonify({
            'messages': chat_history,
            'channel_info': channel_info
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get chat history: {str(e)}'}), 500


@chat_bp.route('/api/chat/sessions/<channel_id>')
def get_chat_sessions(channel_id):
    """Get all chat sessions for a channel"""
    try:
        # Validate channel exists
        channel_info = database_storage.get_channel_by_id(channel_id)
        if not channel_info:
            return jsonify({'error': 'Channel not found'}), 404
        
        # Get chat sessions
        sessions = database_storage.get_channel_chat_sessions(channel_id)
        
        return jsonify({
            'sessions': sessions,
            'channel_info': channel_info
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get chat sessions: {str(e)}'}), 500


@chat_bp.route('/api/chat/session/<session_id>', methods=['DELETE'])
def delete_chat_session(session_id):
    """Delete a chat session"""
    try:
        success = database_storage.delete_channel_chat_session(session_id)
        
        if success:
            return jsonify({'message': 'Chat session deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete chat session'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to delete chat session: {str(e)}'}), 500


def _build_channel_context(channel_summaries, channel_info):
    """Build context string from channel summaries"""
    context = f"Channel: {channel_info['channel_name']}\n"
    context += f"Total videos with summaries: {len(channel_summaries)}\n\n"
    
    context += "=== VIDEO SUMMARIES ===\n\n"
    
    for i, summary in enumerate(channel_summaries, 1):
        video_title = summary.get('video_title', 'Unknown Title')
        summary_text = summary.get('summary_text', '')
        
        context += f"Video {i}: {video_title}\n"
        context += f"Summary: {summary_text}\n\n"
        
        # Limit context size to avoid token limits
        if len(context) > 50000:  # Rough token limit
            context += f"... (truncated after {i} videos due to length)\n"
            break
    
    return context


def _generate_chat_response(chat_prompt, model):
    """Generate a chat response using the specified model"""
    # Determine if it's OpenAI or Anthropic model
    if model.startswith('claude') or model.startswith('anthropic'):
        # Use Anthropic
        if not summarizer.is_configured('anthropic'):
            raise Exception("Anthropic client not configured")
        
        response = summarizer.anthropic_client.messages.create(
            model=model,
            max_tokens=4000,
            messages=[
                {"role": "user", "content": chat_prompt}
            ]
        )
        return response.content[0].text
    else:
        # Use OpenAI
        if not summarizer.is_configured('openai'):
            raise Exception("OpenAI client not configured")
        
        response = summarizer.openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": chat_prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content


def _create_chat_prompt(user_message, context, chat_history, channel_info):
    """Create a chat prompt with context and history"""
    prompt = f"""You are a knowledgeable AI assistant having a conversation about the YouTube channel "{channel_info['channel_name']}".

You have complete access to AI-generated summaries from all videos on this channel. Use this information to answer questions naturally and conversationally.

ROLE: You are a helpful assistant discussing this YouTube channel's content with a user.

INSTRUCTIONS:
- Answer questions directly based on the video summaries provided
- Be conversational and friendly
- Provide specific examples from the videos when relevant
- Do NOT ask for transcripts, additional information, or clarification
- You already have all the information you need

CHANNEL SUMMARIES:
{context}

CONVERSATION HISTORY:
"""
    
    # Add recent chat history
    for message in chat_history[-5:]:  # Only last 5 messages
        role = message['message_type']
        content = message['content']
        if role == 'user':
            prompt += f"Human: {content}\n"
        else:
            prompt += f"Assistant: {content}\n"
    
    prompt += f"\nHuman: {user_message}\n\nAssistant:"
    
    return prompt


# Add database methods to DatabaseStorage class
def add_chat_methods_to_database_storage():
    """Add chat-related methods to the DatabaseStorage class"""
    
    def save_channel_chat_message(self, channel_id, session_id, message_type, content, model_used=None, context_summary=None):
        """Save a chat message to the database"""
        try:
            # Check if the table exists first
            try:
                self.supabase.table('channel_chat').select('id').limit(1).execute()
            except Exception as table_error:
                if 'does not exist' in str(table_error) or 'relation' in str(table_error):
                    print("channel_chat table doesn't exist. Please create it using sql/create_channel_chat_table.sql")
                    return False
                else:
                    raise table_error
            
            message_data = {
                'channel_id': channel_id,
                'session_id': session_id,
                'message_type': message_type,
                'content': content,
                'model_used': model_used,
                'context_summary': context_summary
            }
            
            result = self.supabase.table('channel_chat').insert(message_data).execute()
            return bool(result.data)
            
        except Exception as e:
            print(f"Error saving chat message: {e}")
            return False
    
    def get_channel_chat_history(self, channel_id, session_id, limit=50):
        """Get chat history for a specific channel and session"""
        try:
            result = self.supabase.table('channel_chat')\
                .select('*')\
                .eq('channel_id', channel_id)\
                .eq('session_id', session_id)\
                .order('created_at', desc=False)\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error getting chat history: {e}")
            return []
    
    def get_channel_chat_sessions(self, channel_id, limit=10):
        """Get recent chat sessions for a channel"""
        try:
            result = self.supabase.table('channel_chat')\
                .select('session_id, created_at, message_type, content')\
                .eq('channel_id', channel_id)\
                .order('created_at', desc=True)\
                .limit(limit * 2)\
                .execute()
            
            # Group by session_id and get first message of each session
            sessions = {}
            for message in result.data:
                session_id = message['session_id']
                if session_id not in sessions:
                    sessions[session_id] = {
                        'session_id': session_id,
                        'created_at': message['created_at'],
                        'preview': message['content'][:100] + '...' if len(message['content']) > 100 else message['content']
                    }
            
            return list(sessions.values())[:limit]
            
        except Exception as e:
            print(f"Error getting chat sessions: {e}")
            return []
    
    def delete_channel_chat_session(self, session_id):
        """Delete all messages in a chat session"""
        try:
            result = self.supabase.table('channel_chat')\
                .delete()\
                .eq('session_id', session_id)\
                .execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"Error deleting chat session: {e}")
            return False
    
    def get_channel_summaries_for_chat(self, channel_id):
        """Get all summaries for a channel to use as chat context"""
        try:
            # Get videos for this channel
            videos_result = self.supabase.table('youtube_videos')\
                .select('video_id, title')\
                .eq('channel_id', channel_id)\
                .execute()
            
            if not videos_result.data:
                return []
            
            video_ids = [video['video_id'] for video in videos_result.data]
            
            # Get summaries for these videos
            summaries_result = self.supabase.table('summaries')\
                .select('video_id, summary_text, model_used')\
                .in_('video_id', video_ids)\
                .eq('is_current', True)\
                .execute()
            
            # Combine with video titles
            video_titles = {video['video_id']: video['title'] for video in videos_result.data}
            
            summaries = []
            for summary in summaries_result.data:
                video_id = summary['video_id']
                summaries.append({
                    'video_id': video_id,
                    'video_title': video_titles.get(video_id, 'Unknown Title'),
                    'summary_text': summary['summary_text'],
                    'model_used': summary['model_used']
                })
            
            return summaries
            
        except Exception as e:
            print(f"Error getting channel summaries for chat: {e}")
            return []
    
    # Add methods to DatabaseStorage class
    DatabaseStorage.save_channel_chat_message = save_channel_chat_message
    DatabaseStorage.get_channel_chat_history = get_channel_chat_history
    DatabaseStorage.get_channel_chat_sessions = get_channel_chat_sessions
    DatabaseStorage.delete_channel_chat_session = delete_channel_chat_session
    DatabaseStorage.get_channel_summaries_for_chat = get_channel_summaries_for_chat


# Initialize the database methods
add_chat_methods_to_database_storage()