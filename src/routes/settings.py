from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from src.database_storage import DatabaseStorage

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