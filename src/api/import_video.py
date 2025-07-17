"""
Import Video API endpoint
Handles complete video import/retrieval (transcript, metadata, chapters)
"""
from flask import jsonify
from ..database_storage import database_storage
from ..video_processing import video_processor
from ..utils.helpers import format_summary_html


def import_video(video_id):
    """API endpoint to import/get complete video data (transcript, metadata, chapters)"""
    try:
        # Check database first
        cached_data = database_storage.get(video_id)
        
        if cached_data:
            print(f"API: Using cached data for video: {video_id}")
            transcript = cached_data['transcript']
            video_info = cached_data['video_info']
            formatted_transcript = cached_data['formatted_transcript']
            chapters = video_info.get('chapters')
        else:
            print(f"API: Database MISS for video: {video_id}, importing complete video data")
            
            # Use consolidated import function for full processing (let it handle getting channel_id)
            result = video_processor.process_video_complete(video_id, channel_id=None)
            
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
            'proxy_used': None  # Updated to show no proxy
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500