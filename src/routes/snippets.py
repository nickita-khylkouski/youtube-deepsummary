"""
Snippets-related routes for the YouTube Deep Summary application
"""
from flask import Blueprint, render_template
from ..snippet_manager import snippet_manager

snippets_bp = Blueprint('snippets', __name__)


@snippets_bp.route('/snippets')
def snippets_page():
    """Display channels that have snippets"""
    try:
        # Get all snippets
        all_snippets = snippet_manager.storage.get_memory_snippets(limit=1000)
        
        # Group snippets by channel using business logic
        channels = snippet_manager.group_snippets_by_channel(all_snippets)
        
        # Get statistics
        stats = snippet_manager.get_snippet_statistics()
        
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
        snippets = snippet_manager.storage.get_memory_snippets(limit=10)
        return f"Channel: {channel_name}, Total snippets: {len(snippets)}, First snippet: {snippets[0] if snippets else 'None'}"
    except Exception as e:
        return f"Error: {e}"


@snippets_bp.route('/@<channel_handle>/snippets')
def snippets_channel_page(channel_handle):
    """Display snippets for a specific channel by handle"""
    try:
        print(f"Loading snippets for channel: {channel_handle}")
        
        # Get snippets for channel using business logic
        result = snippet_manager.get_snippets_by_channel_handle(channel_handle, limit=1000)
        
        if not result['success']:
            return render_template('error.html', 
                                 error_message=result['message']), 404
        
        channel_info = result['channel_info']
        channel_snippets = result['snippets']
        
        print(f"Filtered snippets for channel {channel_handle}: {len(channel_snippets)}")
        
        # If no snippets found, return empty page
        if not channel_snippets:
            return render_template('snippets.html', 
                                 video_groups=[],
                                 channel_name=channel_info['channel_name'],
                                 channel_info=channel_info,
                                 stats={'total_snippets': 0})
        
        # Group snippets by video using business logic
        video_groups = snippet_manager.group_snippets_by_video(channel_snippets)
        
        return render_template('snippets.html', 
                             video_groups=video_groups,
                             channel_name=channel_info['channel_name'],
                             channel_info=channel_info,
                             stats={'total_snippets': result['total_count']})
        
    except Exception as e:
        print(f"Error in snippets_channel_page for channel {channel_handle}: {e}")
        print(f"Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        return render_template('error.html', 
                             error_message=f"Error loading channel snippets: {str(e)}"), 500