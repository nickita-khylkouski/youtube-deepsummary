"""
Channel-related routes for the YouTube Deep Summary application
"""
from flask import Blueprint, render_template, request, send_file, jsonify
from ..database_storage import database_storage
from ..utils.helpers import format_summary_html
from ..export_manager import export_manager

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


@channels_bp.route('/@<channel_handle>', strict_slashes=False)
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
                    'published_at': video.get('published_at'),
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


@channels_bp.route('/@<channel_handle>/export-summaries')
def export_summaries(channel_handle):
    """Export all AI summaries for a channel as a ZIP file with individual text files"""
    try:
        # Get format parameter from query string (default to 'markdown')
        format_type = request.args.get('format', 'markdown')
        
        # Validate format type
        if format_type not in ['markdown', 'plain']:
            return jsonify({'error': 'Invalid format. Must be "markdown" or "plain"'}), 400
        
        # Use export manager to handle the export
        memory_file, zip_filename = export_manager.export_channel_summaries_zip(channel_handle, format_type)
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500


@channels_bp.route('/<channel_handle>')
def channel_blog(channel_handle):
    """Display blog-style listing of AI summaries with infinite scrolling"""
    try:
        # Get channel info by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return render_template('error.html', 
                                 error_message=f"Channel not found: {channel_handle}"), 404
        
        # Get summary count for this channel to show if blog should be available
        channel_videos = database_storage.get_videos_by_channel(channel_id=channel_info['channel_id'])
        
        summary_count = 0
        for video in channel_videos:
            summary = database_storage.get_summary(video['video_id'])
            if summary:
                summary_count += 1
        
        # Only show blog if there are summaries available
        if summary_count == 0:
            return render_template('error.html', 
                                 error_message=f"No blog posts available for {channel_info['channel_name']}. Blog requires at least one AI summary."), 404
        
        return render_template('blog.html', 
                             channel_info=channel_info,
                             channel_handle=channel_handle,
                             summary_count=summary_count)
        
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading blog page: {str(e)}"), 500


@channels_bp.route('/<channel_handle>/<post_slug>')
def individual_blog_post(channel_handle, post_slug):
    """Display individual blog post for a specific video"""
    try:
        # Get channel info by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return render_template('error.html', 
                                 error_message=f"Channel not found: {channel_handle}"), 404
        
        # Get all videos for this channel to find the matching post
        channel_videos = database_storage.get_videos_by_channel(channel_id=channel_info['channel_id'])
        
        # Find the video matching the post slug
        target_video = None
        for video in channel_videos:
            # Check if this video has a summary and matches the slug
            if video.get('url_path') and video['url_path'] == post_slug:
                summary = database_storage.get_summary(video['video_id'])
                if summary:
                    target_video = video
                    target_video['summary'] = summary
                    break
        
        if not target_video:
            return render_template('error.html', 
                                 error_message=f"Blog post not found: {post_slug}"), 404
        
        # Get all videos with summaries for navigation (sorted by publish date)
        videos_with_summaries = []
        for video in channel_videos:
            summary = database_storage.get_summary(video['video_id'])
            if summary:
                videos_with_summaries.append({
                    'video_id': video['video_id'],
                    'title': video['title'],
                    'url_path': video.get('url_path'),
                    'published_at': video.get('published_at')
                })
        
        # Sort by published_at descending (most recent first)
        videos_with_summaries.sort(
            key=lambda x: x.get('published_at') or '1970-01-01', 
            reverse=True
        )
        
        # Find previous and next posts
        current_index = next((i for i, v in enumerate(videos_with_summaries) 
                            if v['video_id'] == target_video['video_id']), None)
        
        prev_post = videos_with_summaries[current_index - 1] if current_index and current_index > 0 else None
        next_post = videos_with_summaries[current_index + 1] if current_index is not None and current_index < len(videos_with_summaries) - 1 else None
        
        # Format summary as HTML
        target_video['summary'] = format_summary_html(target_video['summary'])
        
        return render_template('blog_post.html',
                             channel_info=channel_info,
                             channel_handle=channel_handle,
                             post=target_video,
                             prev_post=prev_post,
                             next_post=next_post,
                             total_posts=len(videos_with_summaries))
        
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading blog post: {str(e)}"), 500


@channels_bp.route('/@<channel_handle>/chat', strict_slashes=False)
def channel_chat(channel_handle):
    """Display dedicated chat page for a specific channel"""
    try:
        # Get channel info by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return render_template('error.html', 
                                 error_message=f"Channel not found: {channel_handle}"), 404
        
        # Get summary count for this channel
        channel_videos = database_storage.get_videos_by_channel(channel_id=channel_info['channel_id'])
        
        summary_count = 0
        for video in channel_videos:
            summary = database_storage.get_summary(video['video_id'])
            if summary:
                summary_count += 1
        
        # Only allow chat if there are summaries available
        if summary_count == 0:
            return render_template('error.html', 
                                 error_message=f"No AI summaries available for {channel_info['channel_name']}. Chat requires at least one video summary."), 404
        
        return render_template('chat.html', 
                             current_channel=channel_info,
                             summary_count=summary_count)
        
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading chat page: {str(e)}"), 500


@channels_bp.route('/chat')
def global_chat():
    """Display global chat page across all channels"""
    try:
        # Get total number of summaries across all channels
        total_summaries = database_storage.get_summaries_count()
        
        if total_summaries == 0:
            return render_template('error.html', 
                                 error_message="No AI summaries available. Global chat requires at least one video summary."), 404
        
        return render_template('chat.html', 
                             current_channel=None,
                             summary_count=total_summaries)
        
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading global chat page: {str(e)}"), 500