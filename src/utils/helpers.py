"""
Utility helper functions for the YouTube Deep Summary application
"""
import re
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    print("Warning: markdown library not available. Install with: pip install markdown")


def extract_video_id(url_or_id):
    """Extract video ID from YouTube URL or return if already an ID"""
    # If it's already an 11-character ID, return it
    if len(url_or_id) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
        return url_or_id
    
    # Extract from URL patterns
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/.*[?&]v=([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    
    return None


def extract_channel_id_or_name(channel_url_or_name):
    """Extract channel ID or name from YouTube channel URL"""
    if not channel_url_or_name:
        return None, None
    
    # If it's already a channel ID (starts with UC)
    if channel_url_or_name.startswith('UC') and len(channel_url_or_name) == 24:
        return channel_url_or_name, 'id'
    
    # Extract from channel URL patterns
    patterns = [
        r'youtube\.com\/channel\/([a-zA-Z0-9_-]{24})',  # Channel ID
        r'youtube\.com\/c\/([a-zA-Z0-9_-]+)',          # Custom URL
        r'youtube\.com\/@([a-zA-Z0-9_.-]+)',           # Handle format
        r'youtube\.com\/user\/([a-zA-Z0-9_-]+)',       # Legacy username
    ]
    
    for pattern in patterns:
        match = re.search(pattern, channel_url_or_name)
        if match:
            return match.group(1), 'custom' if '/c/' in pattern or '/@' in pattern or '/user/' in pattern else 'id'
    
    # If no URL pattern matched, treat as custom name
    return channel_url_or_name, 'custom'


def convert_markdown_to_html(text):
    """Convert markdown text to HTML for display"""
    if not text or not MARKDOWN_AVAILABLE:
        return text
    
    try:
        # Convert markdown to HTML with extensions for better formatting
        html = markdown.markdown(text, extensions=['extra', 'codehilite', 'toc'])
        return html
    except Exception as e:
        print(f"Error converting markdown to HTML: {e}")
        return text


def get_channel_url_identifier(channel_info=None, channel_name=None):
    """Get the best identifier for channel URLs - prefer channel_id over name"""
    if channel_info and channel_info.get('channel_id'):
        return channel_info['channel_id']
    elif channel_name:
        return channel_name
    else:
        return 'Unknown'


def format_duration(seconds):
    """Format duration from seconds to human-readable format"""
    if not seconds:
        return "Unknown"
    
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except (ValueError, TypeError):
        return "Unknown"


def format_summary_html(summary):
    """Format AI summary text to HTML with markdown conversion"""
    if not summary:
        return None
        
    if MARKDOWN_AVAILABLE:
        # Pre-process bullet points to proper markdown lists
        processed_summary = summary.replace('• ', '* ')
        return markdown.markdown(processed_summary, extensions=['nl2br', 'tables'])
    else:
        # Fallback if markdown library not available
        return summary.replace('\n', '<br>').replace('• ', '• ')