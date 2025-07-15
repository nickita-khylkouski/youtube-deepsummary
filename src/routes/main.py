"""
Main routes for the YouTube Deep Summary application
"""
from flask import Blueprint, request, render_template, redirect
from ..chapter_extractor import extract_video_info
from ..database_storage import database_storage
from ..video_processing import video_processor
from ..utils.helpers import extract_video_id

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page with instructions"""
    return render_template('index.html')


@main_bp.route('/watch')
def watch():
    """Redirect old /watch?v= URLs to new /@handle/url-path format"""
    video_id_param = request.args.get('v')
    
    if not video_id_param:
        return render_template('error.html', 
                             error_message="No video ID provided. Please use /watch?v=VIDEO_ID"), 400
    
    video_id = extract_video_id(video_id_param)
    
    if not video_id:
        return render_template('error.html', 
                             error_message="Invalid video ID format"), 400
    
    try:
        # Get video from database to find channel handle and URL path
        video_data = database_storage.get_all_cached_videos()
        
        # Find the video by video_id
        target_video = None
        for video in video_data:
            if video['video_id'] == video_id:
                target_video = video
                break
        
        if not target_video:
            # Video not found in database, try to automatically import it
            print(f"Video {video_id} not found in database, attempting automatic import...")
            
            # Extract channel_id from video_info if available
            try:
                video_info = extract_video_info(video_id)
                channel_id = video_info.get('channel_id') if video_info else None
            except Exception:
                channel_id = None
            
            # Use consolidated import function
            result = video_processor.process_video_complete(video_id, channel_id)
            
            if result['status'] == 'error':
                return render_template('error.html', 
                                     error_message=f"Video not found and automatic import failed: {video_id}. Error: {result['error']}"), 404
            
            # Now try to find the video again
            video_data = database_storage.get_all_cached_videos()
            for video in video_data:
                if video['video_id'] == video_id:
                    target_video = video
                    break
            
            if not target_video:
                return render_template('error.html', 
                                     error_message=f"Video imported but not found in database: {video_id}"), 500
        
        # Check if video has handle and url_path for redirect
        handle = target_video.get('handle')
        url_path = target_video.get('url_path')
        
        if handle and url_path:
            # Redirect to new URL format
            # Remove @ from handle if present for URL construction
            clean_handle = handle.lstrip('@')
            new_url = f"/@{clean_handle}/{url_path}"
            print(f"Redirecting /watch?v={video_id} to {new_url}")
            return redirect(new_url)
        else:
            # Missing handle or url_path, show error
            return render_template('error.html', 
                                 error_message=f"Video exists but missing channel handle or URL path. Please re-import."), 400
        
    except Exception as e:
        print(f"Error processing video {video_id}: {e}")
        import traceback
        traceback.print_exc()
        return render_template('error.html', 
                             error_message=f"Error loading video: {str(e)}"), 500


@main_bp.route('/favicon.ico')
def favicon():
    """Serve favicon from static directory"""
    from flask import current_app
    return current_app.send_static_file('favicon.ico')