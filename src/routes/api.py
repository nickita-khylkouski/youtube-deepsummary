"""
API routes for the YouTube Deep Summary application
"""
from flask import Blueprint, request, jsonify
from urllib.parse import unquote
from ..chapter_extractor import extract_video_info
from ..database_storage import database_storage
from ..video_processing import video_processor
from ..youtube_api import youtube_api
from ..snippet_manager import snippet_manager
from ..utils.helpers import extract_video_id, format_summary_html
from ..config import Config

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/transcript/<video_id>')
def transcript(video_id):
    """API endpoint to get transcript as JSON"""
    try:
        # Check database first for API endpoint too
        cached_data = database_storage.get(video_id)
        
        if cached_data:
            print(f"API: Using cached data for video: {video_id}")
            transcript = cached_data['transcript']
            video_info = cached_data['video_info']
            formatted_transcript = cached_data['formatted_transcript']
            chapters = video_info.get('chapters')
        else:
            print(f"API: Database MISS for video: {video_id}, downloading fresh data")
            
            # Extract channel_id from video_info if available
            try:
                video_info = extract_video_info(video_id)
                channel_id = video_info.get('channel_id') if video_info else None
            except Exception:
                channel_id = None
            
            # Use consolidated import function
            result = video_processor.process_video_complete(video_id, channel_id)
            
            if result['status'] == 'error':
                return jsonify({
                    'success': False,
                    'error': f"Failed to import video: {result['error']}"
                }), 500
            
            # Get the data that was just stored
            cached_data = database_storage.get(video_id)
            transcript = cached_data['transcript']
            formatted_transcript = cached_data['formatted_transcript']
            video_info = cached_data['video_info']
            chapters = video_info.get('chapters')
        
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        
        # Get enhanced video data with channel information
        enhanced_video_data = database_storage.get(video_id)
        channel_info = None
        if enhanced_video_data and 'video_info' in enhanced_video_data:
            if 'youtube_channels' in enhanced_video_data['video_info']:
                channel_info = enhanced_video_data['video_info']['youtube_channels']
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'video_title': video_info.get('title'),
            'video_duration': video_info.get('duration'),
            'channel_info': channel_info,
            'transcript': transcript,
            'formatted_transcript': formatted_transcript,
            'chapters': chapters,
            'thumbnail_url': thumbnail_url,
            'proxy_used': Config.YOUTUBE_PROXY
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/summary/<video_id>')
def summary_legacy(video_id):
    """API endpoint to get transcript summary as JSON (legacy - downloads transcript)"""
    try:
        if not video_processor.summarizer or not video_processor.summarizer.is_configured():
            return jsonify({
                'success': False,
                'error': 'OpenAI API key not configured'
            }), 400
        
        transcript = video_processor.get_transcript(video_id)
        summary = video_processor.summarizer.summarize_transcript(transcript)
        
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


@api_bp.route('/summary', methods=['POST'])
def summary():
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
        
        summary, from_cache = video_processor.generate_summary(video_id, formatted_transcript, force_regenerate)
        
        # Format the summary as HTML for frontend display
        summary_html = format_summary_html(summary)
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'summary': summary_html,
            'from_cache': from_cache
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/summary/regenerate', methods=['POST'])
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


@api_bp.route('/models')
def get_available_models():
    """API endpoint to get available AI models"""
    try:
        available_models = video_processor.summarizer.get_available_models()
        return jsonify({
            'success': True,
            'models': available_models
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/summary/history/<video_id>')
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


@api_bp.route('/summary/set-current', methods=['POST'])
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


@api_bp.route('/summary/delete/<int:summary_id>', methods=['DELETE'])
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


@api_bp.route('/cache/info')
def cache_info():
    """API endpoint to get database statistics"""
    try:
        cache_info = database_storage.get_cache_info()
        return jsonify({
            'success': True,
            'cache_info': cache_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/cache/cleanup', methods=['POST'])
def cache_cleanup():
    """API endpoint to clean up expired cache files (no-op for database)"""
    try:
        database_storage.clear_expired()
        cache_info = database_storage.get_cache_info()
        return jsonify({
            'success': True,
            'message': 'Database cleanup completed (no action needed)',
            'cache_info': cache_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/delete/<video_id>', methods=['DELETE'])
def delete_video(video_id):
    """API endpoint to delete a video from storage"""
    try:
        success = database_storage.delete(video_id)
        if success:
            return jsonify({'success': True, 'message': f'Video {video_id} deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete video'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/delete-channel/<channel_handle>', methods=['DELETE'])
def delete_channel(channel_handle):
    """API endpoint to delete a channel and all its associated data"""
    try:
        # Get channel by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return jsonify({'success': False, 'message': f'Channel not found: {channel_handle}'}), 404
        
        channel_id = channel_info['channel_id']
        channel_name = channel_info['channel_name']
        
        # Delete the channel and all associated data
        success = database_storage.delete_channel(channel_id)
        if success:
            return jsonify({
                'success': True, 
                'message': f'Channel "{channel_name}" and all associated data deleted successfully'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to delete channel'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/<channel_handle>/generate-missing-summaries', methods=['POST'])
def generate_missing_summaries(channel_handle):
    """API endpoint to generate summaries for videos without summaries"""
    try:
        # Get channel info by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return jsonify({
                'success': False,
                'error': f'Channel not found: {channel_handle}'
            }), 404
        
        data = request.get_json() if request.content_type == 'application/json' else {}
        model = data.get('model', 'claude-sonnet-4-20250514')  # Default to Claude Sonnet 4
        
        # Check if model is available
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
        
        # Get videos for this channel
        channel_videos = database_storage.get_videos_by_channel(channel_id=channel_info['channel_id'])
        
        # Find videos without summaries
        videos_without_summaries = []
        if channel_videos:
            for video in channel_videos:
                if not database_storage.get_summary(video['video_id']):
                    videos_without_summaries.append(video)
        
        if not videos_without_summaries:
            return jsonify({
                'success': True,
                'message': 'All videos already have summaries',
                'processed': 0,
                'errors': 0,
                'results': []
            })
        
        # Process each video without summary
        results = []
        processed_count = 0
        error_count = 0
        
        for video in videos_without_summaries:
            video_id = video['video_id']
            print(f"Generating summary for video: {video_id} - {video.get('title', 'Unknown')}")
            
            try:
                # Get existing video data
                cached_data = database_storage.get(video_id)
                if not cached_data:
                    results.append({
                        'video_id': video_id,
                        'status': 'error',
                        'message': 'Video data not found in database'
                    })
                    error_count += 1
                    continue
                
                formatted_transcript = cached_data['formatted_transcript']
                video_info = cached_data['video_info']
                chapters = video_info.get('chapters')
                
                # Generate summary with specified model
                summary = video_processor.summarizer.summarize_with_model(
                    formatted_transcript, 
                    model, 
                    chapters, 
                    video_id, 
                    video_info
                )
                
                # Save the summary to database
                database_storage.save_summary(video_id, summary, model)
                
                results.append({
                    'video_id': video_id,
                    'title': video.get('title', 'Unknown'),
                    'status': 'success',
                    'model_used': model,
                    'message': 'Summary generated successfully'
                })
                processed_count += 1
                
            except Exception as e:
                print(f"Error generating summary for {video_id}: {e}")
                results.append({
                    'video_id': video_id,
                    'title': video.get('title', 'Unknown'),
                    'status': 'error',
                    'message': f'Failed to generate summary: {str(e)}'
                })
                error_count += 1
        
        return jsonify({
            'success': True,
            'channel_name': channel_info['channel_name'],
            'total_videos_without_summaries': len(videos_without_summaries),
            'processed': processed_count,
            'errors': error_count,
            'model_used': model,
            'results': results
        })
        
    except Exception as e:
        print(f"Error generating missing summaries: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Snippets API endpoints
@api_bp.route('/snippets', methods=['POST'])
def save_snippet():
    """API endpoint to save a snippet"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        video_id = data.get('video_id')
        snippet_text = data.get('snippet_text')
        context_before = data.get('context_before')
        context_after = data.get('context_after')
        tags = data.get('tags', [])

        if not video_id or not snippet_text:
            return jsonify({'success': False, 'message': 'video_id and snippet_text are required'}), 400

        result = snippet_manager.create_snippet(
            video_id=video_id,
            snippet_text=snippet_text,
            context_before=context_before,
            context_after=context_after,
            tags=tags
        )

        if result['success']:
            return jsonify({'success': True, 'message': result['message']})
        else:
            return jsonify({'success': False, 'message': result['message']}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/snippets')
def get_snippets():
    """API endpoint to get snippets"""
    try:
        video_id = request.args.get('video_id')
        limit = int(request.args.get('limit', 100))

        if video_id:
            snippets = snippet_manager.get_snippets_by_video(video_id, limit)
        else:
            snippets = snippet_manager.storage.get_memory_snippets(limit=limit)
        
        return jsonify({'success': True, 'snippets': snippets})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/snippets/<snippet_id>', methods=['DELETE'])
def delete_snippet(snippet_id):
    """API endpoint to delete a snippet"""
    try:
        result = snippet_manager.delete_snippet(snippet_id)
        if result['success']:
            return jsonify({'success': True, 'message': result['message']})
        else:
            return jsonify({'success': False, 'message': result['message']}), 404

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/snippets/<snippet_id>/tags', methods=['PUT'])
def update_snippet_tags(snippet_id):
    """API endpoint to update snippet tags"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        tags = data.get('tags', [])

        result = snippet_manager.update_snippet_tags(snippet_id, tags)
        if result['success']:
            return jsonify({'success': True, 'message': result['message']})
        else:
            return jsonify({'success': False, 'message': result['message']}), 404

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/<channel_handle>/import', methods=['POST'])
def import_channel_videos(channel_handle):
    """API endpoint to import latest videos from a channel by handle"""
    try:
        # Get channel info by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return jsonify({
                'success': False,
                'error': f'Channel not found: {channel_handle}'
            }), 404
        
        # Decode URL-encoded channel handle
        decoded_channel_handle = unquote(channel_handle)
        print(f"Original channel handle: {channel_handle}")
        print(f"Decoded channel handle: {decoded_channel_handle}")
        print(f"Channel name: {channel_info['channel_name']}")
        
        data = request.get_json() if request.content_type == 'application/json' else {}
        
        # Get default values from import settings
        import_settings = database_storage.get_import_settings()
        default_max_results = import_settings.get('default_max_results', 20)
        default_days_back = import_settings.get('default_days_back', 30)
        max_results_limit = import_settings.get('max_results_limit', 50)
        
        max_results = int(data.get('max_results', default_max_results))
        days_back = int(data.get('days_back', default_days_back))
        
        # Validate parameters using settings
        if max_results > max_results_limit:
            max_results = max_results_limit
        if days_back < 1 or days_back > 365:  # Reasonable range: 1 day to 1 year
            days_back = default_days_back
        
        # Check if YouTube API is configured
        if not youtube_api.is_available():
            return jsonify({
                'success': False,
                'error': 'YouTube Data API not configured. Please set YOUTUBE_API_KEY environment variable.'
            }), 400
        
        # Get latest videos from channel using channel name for the YouTube API
        print(f"Fetching {max_results} videos from channel: {channel_info['channel_name']} within {days_back} days")
        videos = youtube_api.get_channel_videos(channel_info['channel_name'], max_results, days_back)
        
        if not videos:
            return jsonify({
                'success': False,
                'error': f'No videos found for channel: {channel_handle}'
            }), 404
        
        # Process each video
        results = []
        processed_count = 0
        skipped_count = 0
        error_count = 0
        
        for video in videos:
            video_id = video['video_id']
            channel_id = video.get('channel_id')
            print(f"Processing video: {video_id} - {video['title']}")
            
            result = video_processor.process_video_complete(video_id, channel_id)
            results.append(result)
            
            if result['status'] == 'processed':
                processed_count += 1
            elif result['status'] == 'exists':
                skipped_count += 1
            else:
                error_count += 1
        
        return jsonify({
            'success': True,
            'channel_name': channel_info['channel_name'],
            'total_videos': len(videos),
            'processed': processed_count,
            'skipped': skipped_count,
            'errors': error_count,
            'results': results
        })
        
    except Exception as e:
        print(f"Error importing channel videos: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500