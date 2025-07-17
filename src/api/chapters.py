"""
Chapters API endpoint
Handles chapter-specific operations only
"""
from flask import request, jsonify
from ..chapter_extractor import extract_video_info
from ..database_storage import database_storage


def chapters_only(video_id):
    """API endpoint to get/extract chapters as JSON"""
    try:
        # Check for extract_chapters parameter
        extract_chapters = request.args.get('extract_chapters', 'false').lower() == 'true'
        
        # Check database first
        cached_data = database_storage.get(video_id)
        
        # If extract_chapters is True, or if we have cached data but no chapters, force re-extraction
        needs_extraction = (
            extract_chapters or 
            not cached_data or 
            not cached_data.get('video_info', {}).get('chapters') or 
            len(cached_data.get('video_info', {}).get('chapters', [])) == 0
        )
        
        if cached_data and not needs_extraction:
            print(f"API: Using cached chapters for video: {video_id}")
            video_info = cached_data['video_info']
            chapters = video_info.get('chapters')
        else:
            if extract_chapters:
                print(f"API: Extracting chapters for video: {video_id}")
            else:
                print(f"API: No chapters found for video: {video_id}, extracting")
            
            # Extract video info with chapters forced
            try:
                video_info = extract_video_info(video_id, extract_chapters=True)
                chapters = video_info.get('chapters')
                
                # Update the database with new chapter information
                if cached_data:
                    # Update existing video info with chapters and re-save
                    existing_transcript = cached_data.get('transcript', [])
                    existing_formatted = cached_data.get('formatted_transcript', '')
                    channel_id = video_info.get('channel_id')
                    
                    # Get existing channel info or fetch new if needed
                    existing_channel_info = cached_data.get('video_info', {}).get('youtube_channels')
                    if not existing_channel_info and channel_id:
                        from ..youtube_api import youtube_api
                        existing_channel_info = youtube_api.get_channel_info(channel_id)
                    
                    # Merge the updated video info
                    merged_video_info = cached_data['video_info'].copy()
                    merged_video_info.update(video_info)
                    
                    database_storage.set(video_id, existing_transcript, merged_video_info, existing_formatted, channel_id, existing_channel_info)
                else:
                    # Video doesn't exist yet, create a minimal entry with chapters
                    channel_id = video_info.get('channel_id')
                    channel_info = None
                    if channel_id:
                        from ..youtube_api import youtube_api
                        channel_info = youtube_api.get_channel_info(channel_id)
                    
                    database_storage.set(video_id, [], video_info, "Chapters extracted, transcript not yet available.", channel_id, channel_info)
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f"Failed to extract chapters: {str(e)}"
                }), 500
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'chapters': chapters,
            'chapter_count': len(chapters) if chapters else 0,
            'video_title': video_info.get('title') if 'video_info' in locals() else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500