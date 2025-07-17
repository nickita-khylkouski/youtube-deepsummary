"""
Transcript API endpoint
Handles transcript-specific operations only
"""
from flask import request, jsonify
from ..chapter_extractor import extract_video_info
from ..database_storage import database_storage
from ..video_processing import video_processor


def transcript_only(video_id):
    """API endpoint to get/extract transcript only"""
    try:
        # Check for extract_transcript parameter
        extract_transcript = request.args.get('extract_transcript', 'false').lower() == 'true'
        
        # Check database first
        cached_data = database_storage.get(video_id)
        
        # If extract_transcript is True, or if we have cached data but no transcript, force re-extraction
        needs_extraction = (
            extract_transcript or 
            not cached_data or 
            not cached_data.get('transcript') or 
            len(cached_data.get('transcript', [])) == 0 or
            cached_data.get('formatted_transcript') == "Transcript extraction is disabled in import settings."
        )
        
        if cached_data and not needs_extraction:
            print(f"API: Using cached transcript for video: {video_id}")
            transcript = cached_data['transcript']
            video_info = cached_data['video_info']
            formatted_transcript = cached_data['formatted_transcript']
        else:
            if extract_transcript:
                print(f"API: Extracting transcript for video: {video_id}")
            else:
                print(f"API: No transcript found for video: {video_id}, extracting")
            
            # Extract transcript only
            try:
                transcript = video_processor.get_transcript(video_id)
                
                # Format transcript  
                formatted_transcript = video_processor.transcript_formatter.format_for_readability(transcript, None)
                
                # Get minimal video info (just for metadata)
                try:
                    video_info = extract_video_info(video_id, extract_chapters=False)
                except Exception:
                    video_info = {'title': 'Unknown Title'}
                
                # Update existing video data with transcript only
                if cached_data:
                    # Update existing entry with new transcript data
                    existing_video_info = cached_data['video_info']
                    existing_video_info.update(video_info)  # Merge any new metadata
                    
                    # Get existing channel info to avoid re-fetching
                    channel_id = existing_video_info.get('channel_id')
                    existing_channel_info = existing_video_info.get('youtube_channels')
                    
                    database_storage.set(video_id, transcript, existing_video_info, formatted_transcript, channel_id, existing_channel_info)
                else:
                    # New video, minimal setup
                    channel_id = video_info.get('channel_id')
                    database_storage.set(video_id, transcript, video_info, formatted_transcript, channel_id, None)
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f"Failed to extract transcript: {str(e)}"
                }), 500
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'transcript': transcript,
            'transcript_count': len(transcript) if transcript else 0,
            'formatted_transcript': formatted_transcript,
            'video_title': video_info.get('title') if 'video_info' in locals() else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500