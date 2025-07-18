"""
Video-related routes for the YouTube Deep Summary application
"""
from flask import Blueprint, render_template, request
from ..database_storage import database_storage
from ..utils.helpers import format_summary_html
from ..video_processing import video_processor

videos_bp = Blueprint('videos', __name__)


@videos_bp.route('/videos')
def videos_page():
    """Display all saved videos with pagination"""
    try:
        # Get parameters from query string
        page = request.args.get('page', 1, type=int)
        group_by_channel = request.args.get('group_by', 'false').lower() == 'true'
        
        # Set different per_page values for different modes
        if group_by_channel:
            per_page = 5  # Show 5 channels per page when grouped
        else:
            per_page = 20  # Show 20 videos per page when not grouped
        
        # Ensure page is at least 1
        if page < 1:
            page = 1
        
        # Get paginated videos and metadata
        result = database_storage.get_cached_videos_paginated(
            page=page, 
            per_page=per_page, 
            group_by_channel=group_by_channel
        )
        cached_videos = result['videos']
        pagination = result['pagination']
        is_grouped = result.get('is_grouped', False)
        
        cache_stats = database_storage.get_cache_info()
        
        return render_template('videos.html', 
                             cached_videos=cached_videos,
                             cache_stats=cache_stats,
                             pagination=pagination,
                             is_grouped=is_grouped,
                             group_by_channel=group_by_channel)
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading videos page: {str(e)}"), 500


@videos_bp.route('/@<channel_handle>/<url_path>')
def video_by_url_path(channel_handle, url_path):
    """Display transcript for YouTube video using SEO-friendly URL"""
    try:
        # Get video by URL path
        video = database_storage.get_video_by_url_path(url_path)
        
        if not video:
            return render_template('error.html', 
                                 error_message=f"Video not found: {url_path}"), 404
        
        # Verify the channel handle matches
        if video.get('handle') != channel_handle and video.get('handle') != f"@{channel_handle}":
            return render_template('error.html', 
                                 error_message=f"Video not found in channel: {channel_handle}"), 404
        
        video_id = video['video_id']
        
        # Get full video data from database
        video_data = database_storage.get(video_id)
        
        if not video_data:
            return render_template('error.html', 
                                 error_message="Video data not found"), 404
        
        transcript = video_data['transcript']
        video_info = video_data['video_info']
        formatted_transcript_text = video_data['formatted_transcript']
        
        # Check if transcript exists
        has_transcript = transcript and len(transcript) > 0
        
        video_title = video_info.get('title') or video['title']
        chapters = video_info.get('chapters')
        video_duration = video_info.get('duration') or video['duration']
        
        # Check if chapters exist
        has_chapters = chapters and len(chapters) > 0
        channel_name = video['channel_name']
        
        # Get enhanced channel information from video data or use basic video data
        channel_info = None
        if 'youtube_channels' in video_data.get('video_info', {}) and video_data['video_info']['youtube_channels']:
            # Use channel info from database (preferred)
            channel_info = video_data['video_info']['youtube_channels']
            # Ensure handle is properly processed
            if channel_info.get('handle'):
                channel_info['handle'] = channel_info['handle'].lstrip('@')
                if not channel_info['handle']:
                    channel_info['handle'] = None
        else:
            # Use channel info from video data (fallback)
            video_handle = video.get('handle', '')
            if video_handle:
                # Remove leading @ if present
                video_handle = video_handle.lstrip('@')
                # Ensure handle is not empty after stripping
                if not video_handle:
                    video_handle = None
            else:
                video_handle = None
            
            channel_info = {
                'handle': video_handle,
                'channel_name': video.get('channel_name'),
                'channel_id': video.get('channel_id')
            }
        
        # Get summary from database and convert markdown to HTML
        summary = database_storage.get_summary(video_id)
        if summary:
            summary = format_summary_html(summary)
        
        # Get memory snippets for this video
        snippets = database_storage.get_memory_snippets(video_id=video_id)
        
        # Add thumbnail URL
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        
        # Get published_at from the video data
        published_at = video.get('published_at')
        
        return render_template('video.html', 
                             video_id=video_id,
                             video_title=video_title,
                             channel_name=channel_name,
                             channel_info=channel_info,
                             transcript=transcript,
                             formatted_transcript=formatted_transcript_text,
                             chapters=chapters,
                             video_duration=video_duration,
                             summary=summary,
                             snippets=snippets,
                             thumbnail_url=thumbnail_url,
                             has_transcript=has_transcript,
                             has_chapters=has_chapters,
                             published_at=published_at,
                             summarize_enabled=video_processor.summarizer and video_processor.summarizer.is_configured())
        
    except Exception as e:
        print(f"Error in video_by_url_path for {channel_handle}/{url_path}: {e}")
        import traceback
        traceback.print_exc()
        return render_template('error.html', 
                             error_message=f"Error loading video: {str(e)}"), 500