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
        max_results = int(data.get('max_results', 5))
        
        if max_results > 20:  # Reasonable limit
            max_results = 20
        
        # Check if YouTube API is configured
        if not youtube_api.is_available():
            return jsonify({
                'success': False,
                'error': 'YouTube Data API not configured. Please set YOUTUBE_API_KEY environment variable.'
            }), 400
        
        # Get latest videos from channel using channel name for the YouTube API
        print(f"Fetching {max_results} videos from channel: {channel_info['channel_name']}")
        videos = youtube_api.get_channel_videos(channel_info['channel_name'], max_results)
        
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