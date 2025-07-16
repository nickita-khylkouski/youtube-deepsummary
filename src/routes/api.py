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
from ..api.import_video import import_video
from ..api.transcript import transcript_only
from ..api.chapters import chapters_only
from ..api.summary import (
    summary_legacy, summary_from_data, regenerate_summary, 
    get_summary_history, set_current_summary, delete_summary
)

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/import-video/<video_id>')
def import_video_route(video_id):
    """Route wrapper for import video functionality"""
    return import_video(video_id)


@api_bp.route('/transcript/<video_id>')
def transcript_route(video_id):
    """Route wrapper for transcript functionality"""
    return transcript_only(video_id)


@api_bp.route('/chapters/<video_id>')
def chapters_route(video_id):
    """Route wrapper for chapters functionality"""
    return chapters_only(video_id)


@api_bp.route('/summary/<video_id>')
def summary_legacy_route(video_id):
    """Route wrapper for legacy summary functionality"""
    return summary_legacy(video_id)


@api_bp.route('/summary', methods=['POST'])
def summary_route():
    """Route wrapper for summary generation functionality"""
    return summary_from_data()


@api_bp.route('/summary/regenerate', methods=['POST'])
def regenerate_summary_route():
    """Route wrapper for summary regeneration functionality"""
    return regenerate_summary()


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
def get_summary_history_route(video_id):
    """Route wrapper for summary history functionality"""
    return get_summary_history(video_id)


@api_bp.route('/summary/set-current', methods=['POST'])
def set_current_summary_route():
    """Route wrapper for set current summary functionality"""
    return set_current_summary()


@api_bp.route('/summary/delete/<int:summary_id>', methods=['DELETE'])
def delete_summary_route(summary_id):
    """Route wrapper for delete summary functionality"""
    return delete_summary(summary_id)


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
        
        # Get import settings for processing behavior
        skip_existing_videos = import_settings.get('skip_existing_videos', True)
        
        # Process each video
        results = []
        processed_count = 0
        skipped_count = 0
        error_count = 0
        
        for video in videos:
            video_id = video['video_id']
            channel_id = video.get('channel_id')
            print(f"Processing video: {video_id} - {video['title']}")
            
            # Check if video already exists and skip if configured
            if skip_existing_videos:
                existing_video = database_storage.get(video_id)
                if existing_video:
                    print(f"Skipping existing video: {video_id}")
                    results.append({
                        'status': 'exists',
                        'video_id': video_id,
                        'title': video['title'],
                        'message': 'Video already exists in database'
                    })
                    skipped_count += 1
                    continue
            
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