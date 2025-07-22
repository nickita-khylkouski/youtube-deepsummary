"""
Channel chat routes for the YouTube Deep Summary application
Enables GPT-like conversations using channel summaries as context
Refactored to use modular architecture principles
"""

from flask import Blueprint, request, jsonify, render_template
from ..chat_manager import chat_manager
from ..database_storage import database_storage

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
        sessions_result = chat_manager.get_chat_sessions(channel_info['channel_id'])
        if 'error' in sessions_result:
            recent_sessions = []
        else:
            recent_sessions = sessions_result['sessions']
        
        # Get available AI models
        models_result = chat_manager.get_available_models()
        if 'error' in models_result:
            available_models = {'openai': ['gpt-4.1']}  # fallback
        else:
            available_models = models_result
        
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
        
        # Use chat manager to process the message
        result = chat_manager.send_message(
            channel_id=channel_id,
            user_message=user_message,
            session_id=session_id,
            model=model
        )
        
        # Return result (either success or error)
        if 'error' in result:
            return jsonify(result), 500
        else:
            return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Chat failed: {str(e)}'}), 500


@chat_bp.route('/api/chat/history/<channel_id>/<session_id>')
def get_chat_history(channel_id, session_id):
    """Get chat history for a specific channel and session"""
    try:
        result = chat_manager.get_chat_history(channel_id, session_id)
        
        if 'error' in result:
            return jsonify(result), 404 if 'not found' in result['error'].lower() else 500
        else:
            return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Failed to get chat history: {str(e)}'}), 500


@chat_bp.route('/api/chat/sessions/<channel_id>')
def get_chat_sessions(channel_id):
    """Get all chat sessions for a channel"""
    try:
        result = chat_manager.get_chat_sessions(channel_id)
        
        if 'error' in result:
            return jsonify(result), 404 if 'not found' in result['error'].lower() else 500
        else:
            return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Failed to get chat sessions: {str(e)}'}), 500


@chat_bp.route('/api/chat/session/<session_id>', methods=['DELETE'])
def delete_chat_session(session_id):
    """Delete a chat session"""
    try:
        result = chat_manager.delete_chat_session(session_id)
        
        if 'error' in result:
            return jsonify(result), 500
        else:
            return jsonify(result)
            
    except Exception as e:
        return jsonify({'error': f'Failed to delete chat session: {str(e)}'}), 500