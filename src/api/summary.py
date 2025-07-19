"""
Summary API endpoints
Handles summary generation, regeneration, history, and management
"""
from flask import request, jsonify
from ..database_storage import database_storage
from ..video_processing import video_processor
from ..utils.helpers import format_summary_html
from ..config import Config


def summary_legacy(video_id):
    """API endpoint to get transcript summary as JSON (legacy - downloads transcript)"""
    try:
        if not video_processor.summarizer or not video_processor.summarizer.is_configured():
            return jsonify({
                'success': False,
                'error': 'OpenAI API key not configured'
            }), 400
        
        transcript = video_processor.get_transcript(video_id)
        # Convert transcript to formatted text
        transcript_text = "\n".join([
            f"[{entry.get('formatted_time', '00:00')}] {entry.get('text', '')}" 
            for entry in transcript
        ])
        summary = video_processor.summarizer.summarize_with_preferred_provider(transcript_text)
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'summary': summary,
            'proxy_used': Config.YOUTUBE_PROXY
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def summary_from_data():
    """API endpoint to generate summary from provided transcript data"""
    try:
        if not video_processor.summarizer or not video_processor.summarizer.is_configured():
            return jsonify({
                'success': False,
                'error': 'OpenAI API key not configured'
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        video_id = data.get('video_id')
        formatted_transcript = data.get('formatted_transcript')
        force_regenerate = data.get('force_regenerate', False)
        
        if not video_id or not formatted_transcript:
            return jsonify({
                'success': False,
                'error': 'video_id and formatted_transcript are required'
            }), 400
        
        # Check if we already have a summary and not forcing regeneration
        if not force_regenerate:
            existing_summary = database_storage.get_summary(video_id)
            if existing_summary:
                summary_html = format_summary_html(existing_summary)
                return jsonify({
                    'success': True,
                    'video_id': video_id,
                    'summary': summary_html,
                    'from_cache': True
                })
        
        # Get default prompt from database
        default_prompt_data = database_storage.get_default_prompt()
        custom_prompt = default_prompt_data['prompt_text'] if default_prompt_data else None
        
        # Get video info and chapters from database to include in summary
        cached_data = database_storage.get(video_id)
        chapters = None
        video_info = None
        if cached_data and cached_data.get('video_info'):
            video_info = cached_data['video_info']
            chapters = video_info.get('chapters')
        
        # Generate new summary using the default prompt from database
        summary = video_processor.summarizer.summarize_with_preferred_provider(
            formatted_transcript, 
            chapters=chapters, 
            video_id=video_id, 
            video_info=video_info,
            custom_prompt=custom_prompt
        )
        
        # Save the summary to database with default prompt information
        prompt_id = default_prompt_data['id'] if default_prompt_data else None
        prompt_name = default_prompt_data['name'] if default_prompt_data else None
        database_storage.save_summary(video_id, summary, video_processor.summarizer.model, prompt_id, prompt_name)
        
        # Format the summary as HTML for frontend display
        summary_html = format_summary_html(summary)
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'summary': summary_html,
            'from_cache': False
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def regenerate_summary():
    """API endpoint to regenerate summary with specified model and optional custom prompt"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        video_id = data.get('video_id')
        model = data.get('model')
        prompt_id = data.get('prompt_id')
        
        if not video_id:
            return jsonify({
                'success': False,
                'error': 'video_id is required'
            }), 400
        
        if not model:
            return jsonify({
                'success': False,
                'error': 'model is required'
            }), 400
        
        # Check if model is supported
        available_models = video_processor.summarizer.get_available_models()
        model_found = False
        for provider_models in available_models.values():
            if model in provider_models:
                model_found = True
                break
        
        if not model_found:
            return jsonify({
                'success': False,
                'error': f'Model not available. Available models: {available_models}'
            }), 400
        
        # Get existing video data
        cached_data = database_storage.get(video_id)
        if not cached_data:
            return jsonify({
                'success': False,
                'error': 'Video not found in database'
            }), 404
        
        formatted_transcript = cached_data['formatted_transcript']
        video_info = cached_data['video_info']
        chapters = video_info.get('chapters')
        
        # Get custom prompt if prompt_id is provided
        custom_prompt = None
        if prompt_id:
            try:
                prompt_id_int = int(prompt_id)
                prompt_data = database_storage.get_ai_prompt_by_id(prompt_id_int)
                if prompt_data:
                    custom_prompt = prompt_data['prompt_text']
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Prompt with ID {prompt_id} not found'
                    }), 404
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid prompt_id format'
                }), 400
        
        # Generate new summary with specified model and optional custom prompt
        summary = video_processor.summarizer.summarize_with_model(
            formatted_transcript, 
            model, 
            chapters, 
            video_id, 
            video_info,
            custom_prompt
        )
        
        # Get prompt name for history
        prompt_name = None
        if prompt_id:
            try:
                prompt_id_int = int(prompt_id)
                prompt_data = database_storage.get_ai_prompt_by_id(prompt_id_int)
                if prompt_data:
                    prompt_name = prompt_data['name']
            except:
                pass

        # Save the new summary to database (creates new history entry)
        summary_id = database_storage.save_summary(video_id, summary, model, prompt_id, prompt_name)
        
        # Format the summary as HTML for frontend display
        summary_html = format_summary_html(summary)
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'summary': summary_html,
            'model_used': model,
            'prompt_id': prompt_id,
            'prompt_name': prompt_name,
            'from_cache': False
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def get_summary_history(video_id):
    """API endpoint to get summary history for a video"""
    try:
        history = database_storage.get_summary_history(video_id)
        
        # Format the history for frontend display
        formatted_history = []
        for entry in history:
            formatted_entry = {
                'summary_id': entry['summary_id'],
                'summary_text': format_summary_html(entry['summary_text']),
                'model_used': entry['model_used'],
                'prompt_id': entry['prompt_id'],
                'prompt_name': entry['prompt_name'],
                'is_current': entry['is_current'],
                'version_number': entry['version_number'],
                'created_at': entry['created_at'],
                'updated_at': entry['updated_at']
            }
            formatted_history.append(formatted_entry)
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'history': formatted_history
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def set_current_summary():
    """API endpoint to set a specific summary as current"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        video_id = data.get('video_id')
        summary_id = data.get('summary_id')
        
        if not video_id or not summary_id:
            return jsonify({
                'success': False,
                'error': 'video_id and summary_id are required'
            }), 400
        
        success = database_storage.set_current_summary(video_id, summary_id)
        
        if success:
            # Get the updated summary data
            summary_data = database_storage.get_summary_by_id(summary_id)
            if summary_data:
                summary_html = format_summary_html(summary_data['summary_text'])
                return jsonify({
                    'success': True,
                    'video_id': video_id,
                    'summary_id': summary_id,
                    'summary': summary_html,
                    'model_used': summary_data['model_used'],
                    'prompt_name': summary_data['prompt_name']
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Summary not found after update'
                }), 404
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to set current summary'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def delete_summary(summary_id):
    """API endpoint to delete a specific summary"""
    try:
        success = database_storage.delete_summary_by_id(summary_id)
        
        if success:
            return jsonify({
                'success': True,
                'summary_id': summary_id,
                'message': 'Summary deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete summary or summary not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500