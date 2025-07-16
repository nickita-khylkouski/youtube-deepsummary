"""
Channel-related routes for the YouTube Deep Summary application
"""
from flask import Blueprint, render_template, request
from ..database_storage import database_storage
from ..utils.helpers import format_summary_html

channels_bp = Blueprint('channels', __name__)


@channels_bp.route('/channels')
def channels_page():
    """Display all channels with video counts"""
    try:
        # Get parameters from query string
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Ensure page is at least 1 and per_page is reasonable
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 20
        
        # Get paginated channels data
        result = database_storage.get_all_channels(page=page, per_page=per_page)
        channels = result['channels']
        pagination = result['pagination']
        
        return render_template('channels.html', 
                             channels=channels, 
                             pagination=pagination)
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading channels: {str(e)}"), 500


@channels_bp.route('/@<channel_handle>')
def channel_overview(channel_handle):
    """Display channel overview with stats and navigation links"""
    try:
        # Get channel info by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return render_template('error.html', 
                                 error_message=f"Channel not found: {channel_handle}"), 404
        
        # Get videos for this channel
        channel_videos = database_storage.get_videos_by_channel(channel_id=channel_info['channel_id'])
        
        # Get summary count and videos without summaries
        summary_count = 0
        videos_without_summaries = []
        if channel_videos:
            for video in channel_videos:
                if database_storage.get_summary(video['video_id']):
                    summary_count += 1
                else:
                    videos_without_summaries.append(video['video_id'])
        
        # Get snippet count for this channel
        snippets = database_storage.get_memory_snippets(limit=1000)
        snippet_count = 0
        for snippet in snippets:
            if snippet.get('channel_id') == channel_info['channel_id']:
                snippet_count += 1
        
        # Get recent videos (latest 6)
        recent_videos = channel_videos[:6] if channel_videos else []
        for video in recent_videos:
            video['thumbnail_url'] = f"https://img.youtube.com/vi/{video['video_id']}/maxresdefault.jpg"
            video['has_summary'] = database_storage.get_summary(video['video_id']) is not None
        
        return render_template('channel_overview.html',
                             channel_info=channel_info,
                             channel_handle=channel_handle,
                             total_videos=len(channel_videos) if channel_videos else 0,
                             summary_count=summary_count,
                             videos_without_summaries_count=len(videos_without_summaries),
                             videos_without_summaries=videos_without_summaries,
                             snippet_count=snippet_count,
                             recent_videos=recent_videos)
        
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading channel: {str(e)}"), 500


@channels_bp.route('/@<channel_handle>/videos')
def channel_videos(channel_handle):
    """Display all videos from a specific channel by handle"""
    try:
        # Get channel info by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return render_template('error.html', 
                                 error_message=f"Channel not found: {channel_handle}"), 404
        
        # Get videos for this channel
        channel_videos_list = database_storage.get_videos_by_channel(channel_id=channel_info['channel_id'])
        
        if not channel_videos_list:
            return render_template('error.html', 
                                 error_message=f"No videos found for channel: {channel_handle}"), 404
        
        # Check which videos have summaries
        for video in channel_videos_list:
            video['has_summary'] = database_storage.get_summary(video['video_id']) is not None
            video['thumbnail_url'] = f"https://img.youtube.com/vi/{video['video_id']}/maxresdefault.jpg"
        
        # Use channel name from channel_info
        display_name = channel_info['channel_name']
        
        return render_template('channel_videos.html', 
                             channel_name=display_name,
                             channel_info=channel_info,
                             videos=channel_videos_list,
                             total_videos=len(channel_videos_list))
        
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading channel videos: {str(e)}"), 500


@channels_bp.route('/@<channel_handle>/summaries')
def channel_summaries(channel_handle):
    """Display AI summaries for all videos from a specific channel by handle"""
    try:
        # Get channel info by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return render_template('error.html', 
                                 error_message=f"Channel not found: {channel_handle}"), 404
        
        # Get videos for this channel
        channel_videos = database_storage.get_videos_by_channel(channel_id=channel_info['channel_id'])
        
        if not channel_videos:
            return render_template('error.html', 
                                 error_message=f"No videos found for channel: {channel_handle}"), 404
        
        # Get summaries for each video
        summaries = []
        for video in channel_videos:
            video_id = video['video_id']
            summary = database_storage.get_summary(video_id)
            
            if summary:
                summary_html = format_summary_html(summary)
                print(f"Converted summary for {video_id}: markdown -> HTML conversion applied")
                
                summaries.append({
                    'video_id': video_id,
                    'title': video['title'],
                    'channel_name': video.get('channel_name'),
                    'channel_id': video.get('channel_id'),
                    'duration': video['duration'],
                    'thumbnail_url': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                    'summary': summary_html,
                    'created_at': video['created_at'],
                    'url_path': video.get('url_path')
                })
        
        # Use channel name from channel_info
        display_name = channel_info['channel_name']
        
        return render_template('channel_summaries.html', 
                             channel_name=display_name,
                             channel_info=channel_info,
                             summaries=summaries,
                             total_videos=len(channel_videos),
                             summarized_videos=len(summaries))
        
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading channel summaries: {str(e)}"), 500