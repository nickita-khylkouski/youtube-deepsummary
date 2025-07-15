"""
Snippets-related routes for the YouTube Deep Summary application
"""
from flask import Blueprint, render_template
from ..database_storage import database_storage

snippets_bp = Blueprint('snippets', __name__)


@snippets_bp.route('/snippets')
def snippets_page():
    """Display channels that have snippets"""
    try:
        snippets = database_storage.get_memory_snippets(limit=1000)
        stats = database_storage.get_memory_snippets_stats()
        
        # Group snippets by channel (use channel information from new schema)
        channel_groups = {}
        for snippet in snippets:
            # Use the enhanced channel information from get_memory_snippets
            channel_name = snippet.get('channel_name', 'Unknown Channel')
            channel_id = snippet.get('channel_id')
            handle = snippet.get('handle')
            
            # Use channel_id as key if available, otherwise channel_name
            channel_key = channel_id if channel_id else channel_name
            
            if channel_key not in channel_groups:
                channel_groups[channel_key] = {
                    'channel_name': channel_name,
                    'channel_id': channel_id,
                    'handle': handle,
                    'thumbnail_url': snippet.get('channel_thumbnail_url'),
                    'videos': {},
                    'total_snippets': 0,
                    'latest_date': ''
                }
            
            video_id = snippet['video_id']
            if video_id not in channel_groups[channel_key]['videos']:
                # Get video information from snippet
                video_info = snippet.get('youtube_videos', {})
                if not video_info:
                    video_info = {
                        'title': f'Video {video_id}',
                        'channel_name': snippet.get('channel_name', 'Unknown Channel'),
                        'thumbnail_url': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                    }
                
                channel_groups[channel_key]['videos'][video_id] = {
                    'video_info': video_info,
                    'video_id': video_id,
                    'snippet_count': 0
                }
            
            channel_groups[channel_key]['videos'][video_id]['snippet_count'] += 1
            channel_groups[channel_key]['total_snippets'] += 1
            
            # Track latest snippet date for channel
            snippet_date = snippet.get('created_at', '')
            if snippet_date > channel_groups[channel_key]['latest_date']:
                channel_groups[channel_key]['latest_date'] = snippet_date
        
        # Convert to list and sort by most recent snippet
        channels = []
        for channel_key, group in channel_groups.items():
            group['video_count'] = len(group['videos'])
            channels.append(group)
        
        # Sort channels by latest snippet date (newest first)
        channels.sort(key=lambda x: x['latest_date'], reverse=True)
        
        return render_template('snippet_channels.html', 
                             channels=channels,
                             stats=stats)
        
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading snippets: {str(e)}"), 500


@snippets_bp.route('/test/snippets/<channel_name>')
def test_snippets_channel(channel_name):
    """Test route for debugging snippets"""
    try:
        snippets = database_storage.get_memory_snippets(limit=10)
        return f"Channel: {channel_name}, Total snippets: {len(snippets)}, First snippet: {snippets[0] if snippets else 'None'}"
    except Exception as e:
        return f"Error: {e}"


@snippets_bp.route('/@<channel_handle>/snippets')
def snippets_channel_page(channel_handle):
    """Display snippets for a specific channel by handle"""
    try:
        print(f"Loading snippets for channel: {channel_handle}")
        
        # Get channel info by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return render_template('error.html', 
                                 error_message=f"Channel not found: {channel_handle}"), 404
        
        # Get all snippets and filter by channel_id
        snippets = database_storage.get_memory_snippets(limit=1000)
        print(f"Total snippets retrieved: {len(snippets)}")
        
        channel_snippets = []
        for snippet in snippets:
            if snippet.get('channel_id') == channel_info['channel_id']:
                channel_snippets.append(snippet)
        
        print(f"Filtered snippets for channel {channel_handle}: {len(channel_snippets)}")
        
        # If no snippets found, return empty page
        if not channel_snippets:
            return render_template('snippets.html', 
                                 video_groups=[],
                                 channel_name=channel_info['channel_name'],
                                 channel_info=channel_info,
                                 stats={'total_snippets': 0})
        
        # Group snippets by video_id
        grouped_snippets = {}
        for snippet in channel_snippets:
            video_id = snippet['video_id']
            if video_id not in grouped_snippets:
                # Use the enhanced video information
                video_info = snippet.get('youtube_videos', {})
                if not video_info:
                    video_info = {
                        'title': f'Video {video_id}',
                        'channel_name': snippet.get('channel_name', 'Unknown Channel')
                    }
                
                grouped_snippets[video_id] = {
                    'video_info': video_info,
                    'video_id': video_id,
                    'channel_name': snippet.get('channel_name'),
                    'channel_id': snippet.get('channel_id'),
                    'handle': snippet.get('handle'),
                    'url_path': snippet.get('youtube_videos', {}).get('url_path'),
                    'snippets': []
                }
            grouped_snippets[video_id]['snippets'].append(snippet)
        
        # Convert to list and sort by most recent snippet in each group
        video_groups = []
        for video_id, group in grouped_snippets.items():
            # Sort snippets within group by creation date (newest first)
            group['snippets'].sort(key=lambda x: x.get('created_at', ''), reverse=True)
            # Use the newest snippet's date for group sorting
            group['latest_date'] = group['snippets'][0].get('created_at', '') if group['snippets'] else ''
            video_groups.append(group)
        
        # Sort groups by latest snippet date (newest first)
        video_groups.sort(key=lambda x: x['latest_date'], reverse=True)
        
        return render_template('snippets.html', 
                             video_groups=video_groups,
                             channel_name=channel_info['channel_name'],
                             channel_info=channel_info,
                             stats={'total_snippets': len(channel_snippets)})
        
    except Exception as e:
        print(f"Error in snippets_channel_page for channel {channel_handle}: {e}")
        print(f"Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        return render_template('error.html', 
                             error_message=f"Error loading channel snippets: {str(e)}"), 500