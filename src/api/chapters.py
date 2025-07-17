"""
Chapters API endpoint
Handles chapter-specific operations only
"""
from flask import request, jsonify
from ..chapter_extractor import extract_video_chapters
from ..database_storage import database_storage
from ..youtube_api import youtube_api


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
            
            # Extract chapters only
            try:
                chapters = extract_video_chapters(video_id)
                
                # Update the database with new chapter information
                if cached_data:
                    # Update existing video info with chapters and re-save
                    existing_transcript = cached_data.get('transcript', [])
                    existing_formatted = cached_data.get('formatted_transcript', '')
                    existing_video_info = cached_data.get('video_info', {})
                    channel_id = existing_video_info.get('channel_id')
                    
                    # Get existing channel info
                    existing_channel_info = existing_video_info.get('youtube_channels')
                    
                    # Update video info with chapters
                    updated_video_info = existing_video_info.copy()
                    updated_video_info['chapters'] = chapters
                    
                    database_storage.set(video_id, existing_transcript, updated_video_info, existing_formatted, channel_id, existing_channel_info)
                    video_info = updated_video_info
                else:
                    # Video doesn't exist yet, need to get basic video info first
                    video_info = youtube_api.get_video_info(video_id)
                    if not video_info:
                        return jsonify({
                            'success': False,
                            'error': "Failed to get video information"
                        }), 500
                    
                    # Add chapters to video info
                    video_info['chapters'] = chapters
                    
                    # Get channel info
                    channel_id = video_info.get('channel_id')
                    channel_info = None
                    if channel_id:
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