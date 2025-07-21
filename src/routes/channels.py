"""
Channel-related routes for the YouTube Deep Summary application
"""
from flask import Blueprint, render_template, request, send_file, jsonify
from ..database_storage import database_storage
from ..utils.helpers import format_summary_html, format_duration
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


@channels_bp.route('/<channel_handle>')
def channel_blog(channel_handle):
    """Display blog-style page with all current AI summaries for a channel at /channelhandle"""
    try:
        # Get channel info by handle - add @ prefix if not present
        handle_to_lookup = channel_handle if channel_handle.startswith('@') else f'@{channel_handle}'
        channel_info = database_storage.get_channel_by_handle(handle_to_lookup)
        if not channel_info:
            return render_template('error.html', 
                                 error_message=f"Channel not found: {channel_handle}"), 404
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = 5  # Load 5 posts per page for better infinite scroll experience
        
        # Get videos for this channel
        channel_videos = database_storage.get_videos_by_channel(channel_id=channel_info['channel_id'])
        
        if not channel_videos:
            return render_template('error.html', 
                                 error_message=f"No videos found for channel: {channel_handle}"), 404
        
        # Get current summaries for each video
        all_blog_posts = []
        for video in channel_videos:
            video_id = video['video_id']
            # Get only the current/default summary (where is_current = true)
            summary = database_storage.get_summary(video_id)
            
            if summary:
                summary_html = format_summary_html(summary)
                
                all_blog_posts.append({
                    'video_id': video_id,
                    'title': video['title'],
                    'channel_name': video.get('channel_name'),
                    'channel_id': video.get('channel_id'),
                    'duration': format_duration(video['duration']),
                    'thumbnail_url': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                    'summary': summary_html,
                    'published_at': video.get('published_at'),
                    'url_path': video.get('url_path'),
                    'created_at': video.get('created_at')
                })
        
        # Sort blog posts by published date (newest first)
        all_blog_posts.sort(key=lambda x: x.get('published_at') or x.get('created_at'), reverse=True)
        
        # Calculate pagination
        total_posts = len(all_blog_posts)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        blog_posts = all_blog_posts[start_idx:end_idx]
        
        # Check if there are more posts
        has_more = end_idx < total_posts
        
        # For AJAX requests (infinite scroll), return JSON
        if request.headers.get('Content-Type') == 'application/json' or request.args.get('format') == 'json':
            return jsonify({
                'success': True,
                'posts': blog_posts,
                'has_more': has_more,
                'page': page,
                'total_posts': total_posts
            })
        
        return render_template('channel_blog.html', 
                             channel_info=channel_info,
                             channel_handle=channel_handle,
                             blog_posts=blog_posts,
                             total_posts=total_posts,
                             has_more=has_more,
                             current_page=page)
        
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading channel blog: {str(e)}"), 500


@channels_bp.route('/<channel_handle>/<post_slug>')
def blog_post_detail(channel_handle, post_slug):
    """Display individual blog post page with just the AI summary"""
    try:
        # Get channel info by handle - add @ prefix if not present
        handle_to_lookup = channel_handle if channel_handle.startswith('@') else f'@{channel_handle}'
        channel_info = database_storage.get_channel_by_handle(handle_to_lookup)
        if not channel_info:
            return render_template('error.html', 
                                 error_message=f"Channel not found: {channel_handle}"), 404
        
        # Get videos for this channel
        channel_videos = database_storage.get_videos_by_channel(channel_id=channel_info['channel_id'])
        
        if not channel_videos:
            return render_template('error.html', 
                                 error_message=f"No videos found for channel: {channel_handle}"), 404
        
        # Get all blog posts with summaries first (for navigation)
        all_blog_posts = []
        for video in channel_videos:
            video_id = video['video_id']
            summary = database_storage.get_summary(video_id)
            if summary:
                all_blog_posts.append(video)
        
        # Sort by published date (newest first)
        all_blog_posts.sort(key=lambda x: x.get('published_at') or x.get('created_at'), reverse=True)
        
        # Find the target video and get next/previous
        target_video = None
        current_index = None
        for i, video in enumerate(all_blog_posts):
            if video.get('url_path') == post_slug:
                target_video = video
                current_index = i
                break
        
        if not target_video:
            return render_template('error.html', 
                                 error_message=f"Blog post not found: {post_slug}"), 404
        
        # Get the current summary for this video
        summary = database_storage.get_summary(target_video['video_id'])
        
        if not summary:
            return render_template('error.html', 
                                 error_message=f"No AI summary available for this post"), 404
        
        summary_html = format_summary_html(summary)
        
        # Get next and previous posts
        prev_post = all_blog_posts[current_index + 1] if current_index + 1 < len(all_blog_posts) else None
        next_post = all_blog_posts[current_index - 1] if current_index > 0 else None
        
        blog_post = {
            'video_id': target_video['video_id'],
            'title': target_video['title'],
            'channel_name': target_video.get('channel_name'),
            'channel_id': target_video.get('channel_id'),
            'duration': format_duration(target_video['duration']),
            'thumbnail_url': f"https://img.youtube.com/vi/{target_video['video_id']}/maxresdefault.jpg",
            'summary': summary_html,
            'published_at': target_video.get('published_at'),
            'url_path': target_video.get('url_path'),
            'created_at': target_video.get('created_at')
        }
        
        return render_template('blog_post_detail.html', 
                             channel_info=channel_info,
                             channel_handle=channel_handle,
                             blog_post=blog_post,
                             prev_post=prev_post,
                             next_post=next_post)
        
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading blog post: {str(e)}"), 500


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