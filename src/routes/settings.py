from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from src.database_storage import DatabaseStorage
from src.summarizer import TranscriptSummarizer
from src.config import Config
import os

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')
db_storage = DatabaseStorage()

@settings_bp.route('/')
def settings_page():
    """Settings page with prompt management."""
    prompts = db_storage.get_ai_prompts()
    return render_template('settings.html', prompts=prompts)

@settings_bp.route('/prompts')
def prompts_api():
    """API endpoint to get all prompts."""
    try:
        prompts = db_storage.get_ai_prompts()
        return jsonify({'status': 'success', 'prompts': prompts})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@settings_bp.route('/prompts', methods=['POST'])
def create_prompt():
    """API endpoint to create a new prompt."""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        prompt_text = data.get('prompt_text', '').strip()
        description = data.get('description', '').strip()
        is_default = data.get('is_default', False)
        
        if not name or not prompt_text:
            return jsonify({'status': 'error', 'message': 'Name and prompt text are required'}), 400
            
        prompt_id = db_storage.create_ai_prompt(name, prompt_text, is_default, description)
        return jsonify({'status': 'success', 'prompt_id': prompt_id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@settings_bp.route('/prompts/<int:prompt_id>', methods=['PUT'])
def update_prompt(prompt_id):
    """API endpoint to update an existing prompt."""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        prompt_text = data.get('prompt_text', '').strip()
        description = data.get('description', '').strip()
        is_default = data.get('is_default', False)
        
        if not name or not prompt_text:
            return jsonify({'status': 'error', 'message': 'Name and prompt text are required'}), 400
            
        success = db_storage.update_ai_prompt(prompt_id, name, prompt_text, is_default, description)
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'Prompt not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@settings_bp.route('/prompts/<int:prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    """API endpoint to delete a prompt."""
    try:
        # Check if this is the default prompt
        prompt = db_storage.get_ai_prompt_by_id(prompt_id)
        if prompt and prompt.get('is_default'):
            return jsonify({'status': 'error', 'message': 'Cannot delete the default prompt'}), 400
            
        success = db_storage.delete_ai_prompt(prompt_id)
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'Prompt not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@settings_bp.route('/prompts/<int:prompt_id>/set-default', methods=['POST'])
def set_default_prompt(prompt_id):
    """API endpoint to set a prompt as default."""
    try:
        success = db_storage.set_default_prompt(prompt_id)
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'Prompt not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Import Settings API endpoints
@settings_bp.route('/import-settings')
def get_import_settings():
    """API endpoint to get all import settings."""
    try:
        settings = db_storage.get_import_settings()
        return jsonify({'status': 'success', 'settings': settings})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@settings_bp.route('/import-settings', methods=['POST'])
def update_import_settings():
    """API endpoint to update import settings."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        success = db_storage.update_import_settings_batch(data)
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to update settings'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Summarizer Settings API endpoints
@settings_bp.route('/summarizer-settings')
def get_summarizer_settings():
    """API endpoint to get current summarizer settings."""
    try:
        # Get settings from database
        db_settings = db_storage.get_summarizer_settings()
        
        # Get current summarizer instance for API key status
        summarizer = TranscriptSummarizer()
        
        # Map database settings to frontend form field names
        settings = {
            'summarizerProvider': db_settings.get('preferred_provider', 'openai'),
            'model': db_settings.get('model', 'gpt-4.1'),
            'temperature': db_settings.get('temperature', 0.7),
            'openaiApiKey': '***' if summarizer.openai_api_key else '',
            'anthropicApiKey': '***' if summarizer.anthropic_api_key else '',
            'maxTokens': db_settings.get('max_tokens', 8192),
            'chapterSummaryModel': db_settings.get('chapter_summary_model', 'claude-sonnet-4-20250514'),
            'enableChapterAwareness': db_settings.get('enable_chapter_awareness', True),
            'enableMetadataInclusion': db_settings.get('enable_metadata_inclusion', True),
            'enableClickableChapters': db_settings.get('enable_clickable_chapters', True)
        }
        
        return jsonify({'status': 'success', 'settings': settings})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@settings_bp.route('/summarizer-settings', methods=['POST'])
def update_summarizer_settings():
    """API endpoint to update summarizer settings."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        # Validate provider
        provider = data.get('summarizerProvider')
        if provider not in ['openai', 'anthropic']:
            return jsonify({'status': 'error', 'message': 'Invalid provider'}), 400
        
        # Validate temperature
        temperature = data.get('temperature', 0.7)
        if not 0 <= temperature <= 2:
            return jsonify({'status': 'error', 'message': 'Temperature must be between 0 and 2'}), 400
        
        # Validate max tokens
        max_tokens = data.get('maxTokens', 8192)
        if not 100 <= max_tokens <= 100000:
            return jsonify({'status': 'error', 'message': 'Max tokens must be between 100 and 100000'}), 400
        
        # Map frontend form field names to database setting keys
        db_settings = {
            'preferred_provider': data.get('summarizerProvider', 'openai'),
            'model': data.get('model', 'gpt-4.1'),
            'temperature': temperature,
            'max_tokens': max_tokens,
            'chapter_summary_model': data.get('chapterSummaryModel', 'claude-sonnet-4-20250514'),
            'enable_chapter_awareness': data.get('enableChapterAwareness', True),
            'enable_metadata_inclusion': data.get('enableMetadataInclusion', True),
            'enable_clickable_chapters': data.get('enableClickableChapters', True)
        }
        
        # Store settings in database
        success = db_storage.update_summarizer_settings_batch(db_settings)
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to update settings'}), 500
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@settings_bp.route('/available-models')
def get_available_models():
    """API endpoint to get available AI models."""
    try:
        summarizer = TranscriptSummarizer()
        models = summarizer.get_available_models()
        return jsonify({'status': 'success', 'models': models})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@settings_bp.route('/test-api', methods=['POST'])
def test_api_connection():
    """API endpoint to test API connections."""
    try:
        data = request.get_json()
        provider = data.get('provider')
        
        if provider not in ['openai', 'anthropic']:
            return jsonify({'status': 'error', 'message': 'Invalid provider'}), 400
        
        summarizer = TranscriptSummarizer()
        
        if provider == 'openai':
            if summarizer.is_configured('openai'):
                return jsonify({'status': 'success', 'message': 'OpenAI API connection successful'})
            else:
                return jsonify({'status': 'error', 'message': 'OpenAI API not configured'})
        
        elif provider == 'anthropic':
            if summarizer.is_configured('anthropic'):
                return jsonify({'status': 'success', 'message': 'Anthropic API connection successful'})
            else:
                return jsonify({'status': 'error', 'message': 'Anthropic API not configured'})
                
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500