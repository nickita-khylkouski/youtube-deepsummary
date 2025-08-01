"""
API routes for the YouTube Deep Summary application
"""
from flask import Blueprint, request, jsonify
from urllib.parse import unquote
from ..database_storage import database_storage
from ..video_processing import video_processor
from ..youtube_api import youtube_api
from ..snippet_manager import snippet_manager
from ..utils.helpers import extract_video_id, format_summary_html
from ..config import Config
from ..api.import_video import import_video
from ..api.transcript import transcript_only
from ..api.chapters import chapters_only
from ..api.summary import (
    summary_legacy, summary_from_data, regenerate_summary, 
    get_summary_history, set_current_summary, delete_summary
)

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/import-video/<video_id>')
def import_video_route(video_id):
    """Route wrapper for import video functionality"""
    return import_video(video_id)


@api_bp.route('/transcript/<video_id>')
def transcript_route(video_id):
    """Route wrapper for transcript functionality"""
    return transcript_only(video_id)


@api_bp.route('/chapters/<video_id>')
def chapters_route(video_id):
    """Route wrapper for chapters functionality"""
    return chapters_only(video_id)


@api_bp.route('/summary/<video_id>')
def summary_legacy_route(video_id):
    """Route wrapper for legacy summary functionality"""
    return summary_legacy(video_id)


@api_bp.route('/summary', methods=['POST'])
def summary_route():
    """Route wrapper for summary generation functionality"""
    return summary_from_data()


@api_bp.route('/summary/regenerate', methods=['POST'])
def regenerate_summary_route():
    """Route wrapper for summary regeneration functionality"""
    return regenerate_summary()


@api_bp.route('/models')
def get_available_models():
    """API endpoint to get available AI models"""
    try:
        available_models_dict = video_processor.summarizer.get_available_models()
        
        # Return dictionary format grouped by provider
        return jsonify({
            'success': True,
            'models': available_models_dict
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/prompts')
def get_available_prompts():
    """API endpoint to get available AI prompts"""
    try:
        prompts = database_storage.get_ai_prompts()
        return jsonify({
            'success': True,
            'prompts': prompts
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/<channel_handle>/regenerate-summaries', methods=['POST'])
def regenerate_channel_summaries(channel_handle):
    """API endpoint to regenerate summaries for a channel"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        count = data.get('count', '5')
        model = data.get('model')
        prompt_id = data.get('prompt_id')

        if not model or not prompt_id:
            return jsonify({'success': False, 'error': 'Model and prompt_id are required'}), 400

        # Get channel ID from handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return jsonify({'success': False, 'error': 'Channel not found'}), 404

        channel_id = channel_info['channel_id']

        # Get summaries to regenerate based on count
        if count == 'all':
            summaries = database_storage.get_summaries_by_channel(channel_id)
        else:
            try:
                limit = int(count)
                summaries = database_storage.get_recent_summaries_by_channel(channel_id, limit)
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid count value'}), 400

        if not summaries:
            return jsonify({'success': False, 'error': 'No summaries found to regenerate'}), 404

        # Get prompt details
        prompt = database_storage.get_ai_prompt_by_id(prompt_id)
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt not found'}), 404

        processed_count = 0
        error_count = 0

        # Regenerate each summary
        for summary in summaries:
            try:
                video_id = summary['video_id']
                
                # Get video and transcript data
                video_data = database_storage.get(video_id)
                if not video_data:
                    print(f"Skipping video {video_id}: No video data available")
                    error_count += 1
                    continue

                # Get formatted transcript - handle both old and new data structures
                transcript_content = None
                if video_data.get('formatted_transcript'):
                    transcript_content = video_data['formatted_transcript']
                elif video_data.get('transcript') and isinstance(video_data['transcript'], dict):
                    transcript_content = video_data['transcript'].get('formatted')
                elif video_data.get('transcript') and isinstance(video_data['transcript'], list):
                    # If transcript is still a list, try to get formatted content
                    transcript_content = video_data.get('formatted_transcript')
                
                if not transcript_content:
                    print(f"Skipping video {video_id}: No transcript content available")
                    error_count += 1
                    continue
                
                # Skip videos with failed transcript extraction
                if not transcript_content or 'Transcript extraction failed' in transcript_content or len(transcript_content.strip()) < 50:
                    print(f"Skipping video {video_id}: Invalid or failed transcript - consider re-importing this video")
                    error_count += 1
                    continue

                # Get chapters data if available for better summarization
                chapters = None
                if video_data.get('chapters'):
                    chapters = video_data['chapters']

                # Generate new summary using the specified model and prompt
                new_summary = video_processor.summarizer.summarize_with_model(
                    transcript_content=transcript_content,
                    model=model,
                    chapters=chapters,
                    video_id=video_id,
                    custom_prompt=prompt['prompt_text']
                )

                if new_summary and len(new_summary.strip()) > 100:  # Ensure meaningful summary
                    # Save the new summary with versioning
                    database_storage.save_summary_with_versioning(
                        video_id=video_id,
                        summary_text=new_summary,
                        model_used=model,
                        prompt_id=prompt_id,
                        prompt_name=prompt['name']
                    )
                    processed_count += 1
                    print(f"Successfully regenerated summary for video {video_id}")
                else:
                    print(f"Failed to generate valid summary for video {video_id}")
                    error_count += 1

            except Exception as e:
                print(f"Error regenerating summary for video {summary['video_id']}: {str(e)}")
                error_count += 1

        return jsonify({
            'success': True,
            'processed': processed_count,
            'errors': error_count,
            'model_used': model,
            'prompt_used': prompt['name']
        })

    except Exception as e:
        print(f"Error in regenerate_channel_summaries: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/<channel_handle>/failed-transcripts')
def get_failed_transcripts(channel_handle):
    """API endpoint to get videos with failed transcript extraction"""
    try:
        # Get channel ID from handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return jsonify({'success': False, 'error': 'Channel not found'}), 404

        channel_id = channel_info['channel_id']

        # Find summaries that indicate failed transcript extraction
        failed_summaries = database_storage.supabase.table('summaries')\
            .select('*, youtube_videos!inner(channel_id, title)')\
            .eq('youtube_videos.channel_id', channel_id)\
            .eq('is_current', True)\
            .execute()

        failed_videos = []
        for summary in failed_summaries.data:
            summary_text = summary.get('summary_text', '')
            if ('Transcript extraction failed' in summary_text or 
                'transcript you\'ve shared appears to be empty' in summary_text or
                'cannot provide a comprehensive summary' in summary_text):
                failed_videos.append({
                    'video_id': summary['video_id'],
                    'title': summary.get('youtube_videos', {}).get('title', 'Unknown'),
                    'summary_id': summary['summary_id']
                })

        return jsonify({
            'success': True,
            'failed_videos': failed_videos,
            'count': len(failed_videos)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/summary/history/<video_id>')
def get_summary_history_route(video_id):
    """Route wrapper for summary history functionality"""
    return get_summary_history(video_id)


@api_bp.route('/summary/set-current', methods=['POST'])
def set_current_summary_route():
    """Route wrapper for set current summary functionality"""
    return set_current_summary()


@api_bp.route('/summary/delete/<int:summary_id>', methods=['DELETE'])
def delete_summary_route(summary_id):
    """Route wrapper for delete summary functionality"""
    return delete_summary(summary_id)


@api_bp.route('/chapter-summary', methods=['POST'])
def generate_chapter_summary():
    """API endpoint to generate summary for a specific chapter"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        video_id = data.get('video_id')
        chapter_time = data.get('chapter_time')
        chapter_title = data.get('chapter_title')
        force_regenerate = data.get('force_regenerate', False)
        model = data.get('model')
        prompt_id = data.get('prompt_id')

        if not video_id or chapter_time is None:
            return jsonify({'success': False, 'error': 'video_id and chapter_time are required'}), 400

        # Get the video data including transcript and chapters
        video_data = database_storage.get(video_id)
        if not video_data:
            return jsonify({'success': False, 'error': 'Video not found'}), 404

        transcript = video_data.get('transcript')
        chapters = video_data.get('video_info', {}).get('chapters')
        
        if not transcript:
            return jsonify({'success': False, 'error': 'No transcript available for this video'}), 400

        if not chapters:
            return jsonify({'success': False, 'error': 'No chapters available for this video'}), 400

        # Extract transcript for the specific chapter
        chapter_transcript = extract_chapter_transcript(transcript, chapters, chapter_time)
        
        if not chapter_transcript:
            return jsonify({'success': False, 'error': 'Could not extract transcript for this chapter'}), 400

        # Check if chapter summary already exists and if we should use it
        existing_summary = database_storage.get_chapter_summary(video_id, chapter_time)
        if existing_summary and not force_regenerate:
            # Return existing summary
            formatted_summary = format_summary_html(existing_summary['summary_text'])
            return jsonify({
                'success': True,
                'summary': formatted_summary,
                'chapter_title': chapter_title,
                'video_id': video_id,
                'model_used': existing_summary['model_used'],
                'prompt_id': existing_summary.get('prompt_id'),
                'prompt_name': existing_summary.get('prompt_name'),
                'cached': True
            })

        # Determine model to use
        if model:
            # Use custom model for regeneration
            model_to_use = model
        else:
            # Get the main AI model from settings (same as used for video summaries)
            summarizer_settings = database_storage.get_summarizer_settings()
            model_to_use = summarizer_settings.get('model', 'gpt-4.1-mini')  # Use main model setting
        
        # Generate summary for the chapter
        if force_regenerate and model and prompt_id:
            # Get the custom prompt text
            prompt_data = database_storage.get_ai_prompt_by_id(prompt_id)
            custom_prompt = prompt_data['prompt_text'] if prompt_data else None
            
            if custom_prompt:
                # Replace placeholder in custom prompt with chapter-specific content
                chapter_context = f"Chapter: {chapter_title}\n\nChapter Content: {chapter_transcript}"
                custom_prompt_filled = custom_prompt.replace('{transcript}', chapter_context)
                
                # Use custom model and prompt for regeneration
                summary = video_processor.summarizer.summarize_with_model(
                    chapter_transcript, 
                    model_to_use,
                    chapters=None,
                    video_id=video_id,
                    video_info=video_data.get('video_info', {}),
                    custom_prompt=custom_prompt_filled
                )
            else:
                # Fall back to standard chapter summarization if prompt not found
                summary = video_processor.summarizer.summarize_chapter(
                    chapter_transcript, 
                    chapter_title,
                    video_id,
                    video_data.get('video_info', {})
                )
        else:
            # Use standard chapter summarization
            summary = video_processor.summarizer.summarize_chapter(
                chapter_transcript, 
                chapter_title,
                video_id,
                video_data.get('video_info', {})
            )

        # Get prompt name if prompt_id was used for regeneration
        prompt_name = None
        if prompt_id:
            prompt_data = database_storage.get_ai_prompt_by_id(prompt_id)
            prompt_name = prompt_data['name'] if prompt_data else None
        
        # Save the summary to database
        summary_id = database_storage.save_chapter_summary(
            video_id, 
            chapter_time, 
            chapter_title, 
            summary,
            model_to_use,
            prompt_id,
            prompt_name
        )

        if not summary_id:
            return jsonify({
                'success': False,
                'error': 'Failed to save chapter summary to database'
            }), 500

        # Format the summary for display
        formatted_summary = format_summary_html(summary)

        return jsonify({
            'success': True,
            'summary': formatted_summary,
            'chapter_title': chapter_title,
            'video_id': video_id,
            'model_used': model_to_use,
            'prompt_id': prompt_id,
            'prompt_name': prompt_name,
            'cached': False
        })

    except Exception as e:
        print(f"Error generating chapter summary: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def extract_chapter_transcript(transcript, chapters, chapter_time):
    """Extract transcript text for a specific chapter"""
    try:
        # Find the current chapter and next chapter
        current_chapter = None
        next_chapter = None
        
        for i, chapter in enumerate(chapters):
            if chapter['time'] == chapter_time:
                current_chapter = chapter
                if i + 1 < len(chapters):
                    next_chapter = chapters[i + 1]
                break
        
        if not current_chapter:
            return None
        
        # Determine the time range for this chapter
        start_time = current_chapter['time']
        end_time = next_chapter['time'] if next_chapter else float('inf')
        
        # Extract transcript entries within this time range
        chapter_entries = []
        for entry in transcript:
            entry_time = entry.get('time', 0)
            if start_time <= entry_time < end_time:
                chapter_entries.append(entry)
        
        # Convert to formatted text
        chapter_text = ""
        for entry in chapter_entries:
            chapter_text += f"{entry.get('text', '')} "
        
        return chapter_text.strip()
        
    except Exception as e:
        print(f"Error extracting chapter transcript: {e}")
        return None


@api_bp.route('/chapter-summary/history/<video_id>/<int:chapter_time>', methods=['GET'])
def get_chapter_summary_history(video_id, chapter_time):
    """API endpoint to get chapter summary version history"""
    try:
        history = database_storage.get_chapter_summary_history(video_id, chapter_time)
        
        if history:
            # Sort by version number descending (newest first)
            history.sort(key=lambda x: x.get('version_number', 1), reverse=True)
            
            return jsonify({
                'success': True,
                'history': history
            })
        else:
            return jsonify({
                'success': True,
                'history': []
            })
            
    except Exception as e:
        print(f"Error getting chapter summary history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/chapter-summary/set-current', methods=['POST'])
def set_current_chapter_summary():
    """API endpoint to set a specific chapter summary version as current"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        video_id = data.get('video_id')
        chapter_time = data.get('chapter_time')
        chapter_summary_id = data.get('chapter_summary_id')

        if not all([video_id, chapter_time is not None, chapter_summary_id]):
            return jsonify({
                'success': False, 
                'error': 'Missing required fields: video_id, chapter_time, chapter_summary_id'
            }), 400

        # Set the specified chapter summary as current
        success = database_storage.set_current_chapter_summary(video_id, chapter_time, chapter_summary_id)
        
        if success:
            # Get the updated summary for display
            chapter_summary = database_storage.get_chapter_summary_by_id(chapter_summary_id)
            if chapter_summary:
                formatted_summary = format_summary_html(chapter_summary['summary_text'])
                return jsonify({
                    'success': True,
                    'summary': formatted_summary,
                    'model_used': chapter_summary['model_used'],
                    'prompt_name': chapter_summary.get('prompt_name'),
                    'version_number': chapter_summary.get('version_number', 1)
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Chapter summary not found after setting as current'
                }), 404
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to set chapter summary as current'
            }), 500

    except Exception as e:
        print(f"Error setting current chapter summary: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/cache/info')
def cache_info():
    """API endpoint to get database statistics"""
    try:
        cache_info = database_storage.get_cache_info()
        return jsonify({
            'success': True,
            'cache_info': cache_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/cache/cleanup', methods=['POST'])
def cache_cleanup():
    """API endpoint to clean up expired cache files (no-op for database)"""
    try:
        database_storage.clear_expired()
        cache_info = database_storage.get_cache_info()
        return jsonify({
            'success': True,
            'message': 'Database cleanup completed (no action needed)',
            'cache_info': cache_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/delete/<video_id>', methods=['DELETE'])
def delete_video(video_id):
    """API endpoint to delete a video from storage"""
    try:
        success = database_storage.delete(video_id)
        if success:
            return jsonify({'success': True, 'message': f'Video {video_id} deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete video'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/delete-channel/<channel_handle>', methods=['DELETE'])
def delete_channel(channel_handle):
    """API endpoint to delete a channel and all its associated data"""
    try:
        # Get channel by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return jsonify({'success': False, 'message': f'Channel not found: {channel_handle}'}), 404
        
        channel_id = channel_info['channel_id']
        channel_name = channel_info['channel_name']
        
        # Delete the channel and all associated data
        success = database_storage.delete_channel(channel_id)
        if success:
            return jsonify({
                'success': True, 
                'message': f'Channel "{channel_name}" and all associated data deleted successfully'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to delete channel'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/<channel_handle>/generate-missing-summaries', methods=['POST'])
def generate_missing_summaries(channel_handle):
    """API endpoint to generate summaries for videos without summaries"""
    try:
        # Get channel info by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return jsonify({
                'success': False,
                'error': f'Channel not found: {channel_handle}'
            }), 404
        
        data = request.get_json() if request.content_type == 'application/json' else {}
        model = data.get('model', 'claude-sonnet-4-20250514')  # Default to Claude Sonnet 4
        
        # Check if model is available
        available_models = video_processor.summarizer.get_available_models()
        model_found = False
        for provider_models in available_models.values():
            if model in provider_models:
                model_found = True
                break
        
        if not model_found:
            return jsonify({
                'success': False,
                'error': f'Model not available. Available models: {available_models}'
            }), 400
        
        # Get videos for this channel
        channel_videos = database_storage.get_videos_by_channel(channel_id=channel_info['channel_id'])
        
        # Find videos without summaries
        videos_without_summaries = []
        if channel_videos:
            for video in channel_videos:
                if not database_storage.get_summary(video['video_id']):
                    videos_without_summaries.append(video)
        
        if not videos_without_summaries:
            return jsonify({
                'success': True,
                'message': 'All videos already have summaries',
                'processed': 0,
                'errors': 0,
                'results': []
            })
        
        # Process each video without summary
        results = []
        processed_count = 0
        error_count = 0
        
        for video in videos_without_summaries:
            video_id = video['video_id']
            print(f"Generating summary for video: {video_id} - {video.get('title', 'Unknown')}")
            
            try:
                # Get existing video data
                cached_data = database_storage.get(video_id)
                if not cached_data:
                    results.append({
                        'video_id': video_id,
                        'status': 'error',
                        'message': 'Video data not found in database'
                    })
                    error_count += 1
                    continue
                
                formatted_transcript = cached_data['formatted_transcript']
                video_info = cached_data['video_info']
                chapters = video_info.get('chapters')
                
                # Generate summary with specified model
                summary = video_processor.summarizer.summarize_with_model(
                    formatted_transcript, 
                    model, 
                    chapters, 
                    video_id, 
                    video_info
                )
                
                # Save the summary to database
                database_storage.save_summary(video_id, summary, model)
                
                results.append({
                    'video_id': video_id,
                    'title': video.get('title', 'Unknown'),
                    'status': 'success',
                    'model_used': model,
                    'message': 'Summary generated successfully'
                })
                processed_count += 1
                
            except Exception as e:
                print(f"Error generating summary for {video_id}: {e}")
                results.append({
                    'video_id': video_id,
                    'title': video.get('title', 'Unknown'),
                    'status': 'error',
                    'message': f'Failed to generate summary: {str(e)}'
                })
                error_count += 1
        
        return jsonify({
            'success': True,
            'channel_name': channel_info['channel_name'],
            'total_videos_without_summaries': len(videos_without_summaries),
            'processed': processed_count,
            'errors': error_count,
            'model_used': model,
            'results': results
        })
        
    except Exception as e:
        print(f"Error generating missing summaries: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/@<channel_handle>/add-missing-transcripts', methods=['POST'])
def add_missing_transcripts(channel_handle):
    """Add missing transcripts for videos in a channel with optional chapters and summaries"""
    try:
        # Get channel info by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return jsonify({
                'success': False,
                'error': f'Channel not found: {channel_handle}'
            }), 404
        
        channel_id = channel_info['channel_id']
        
        # Get request parameters
        data = request.get_json() or {}
        extract_chapters = data.get('extract_chapters', False)
        generate_summaries = data.get('generate_summaries', False)
        
        print(f"Adding missing transcripts for channel {channel_handle} (extract_chapters: {extract_chapters}, generate_summaries: {generate_summaries})")
        
        # Get videos without transcripts
        videos_without_transcripts = database_storage.get_videos_without_transcripts(channel_id)
        
        if not videos_without_transcripts:
            return jsonify({
                'success': True,
                'message': 'All videos in this channel already have transcripts',
                'videos_processed': 0,
                'results': []
            })
        
        print(f"Found {len(videos_without_transcripts)} videos without transcripts")
        
        # Process each video using the existing video processor
        results = []
        for video in videos_without_transcripts:
            video_id = video['video_id']
            video_title = video.get('title', 'Unknown Title')
            
            try:
                # Force transcript extraction and set other options based on parameters
                # We need to temporarily override import settings for this operation
                original_settings = database_storage.get_import_settings()
                
                # Set temporary settings for this operation
                temp_settings = {
                    'enableTranscriptExtraction': True,  # Always extract transcripts
                    'enableChapterExtraction': extract_chapters,
                    'enableAutoSummary': generate_summaries
                }
                database_storage.update_import_settings_batch(temp_settings)
                
                # Process the video with forced transcript extraction
                result = video_processor.process_video_complete(
                    video_id, 
                    channel_id=channel_id,
                    force_transcript_extraction=True
                )
                
                # Restore original settings
                database_storage.update_import_settings_batch(original_settings)
                
                if result['status'] == 'processed':
                    results.append({
                        'video_id': video_id,
                        'title': video_title,
                        'status': 'success',
                        'transcript_extracted': result.get('transcript_extracted', False),
                        'summary_generated': result.get('summary_generated', False)
                    })
                    print(f"Successfully processed {video_title}")
                else:
                    results.append({
                        'video_id': video_id,
                        'title': video_title,
                        'status': 'error',
                        'error': result.get('error', 'Unknown error')
                    })
                    print(f"Failed to process {video_title}: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                results.append({
                    'video_id': video_id,
                    'title': video_title,
                    'status': 'error',
                    'error': str(e)
                })
                print(f"Error processing {video_title}: {e}")
        
        # Count successes
        successful_count = len([r for r in results if r['status'] == 'success'])
        
        return jsonify({
            'success': True,
            'message': f'Processed {successful_count}/{len(videos_without_transcripts)} videos successfully',
            'videos_processed': len(videos_without_transcripts),
            'successful_count': successful_count,
            'results': results
        })
        
    except Exception as e:
        print(f"Error adding missing transcripts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Snippets API endpoints
@api_bp.route('/snippets', methods=['POST'])
def save_snippet():
    """API endpoint to save a snippet"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        video_id = data.get('video_id')
        snippet_text = data.get('snippet_text')
        context_before = data.get('context_before')
        context_after = data.get('context_after')
        tags = data.get('tags', [])

        if not video_id or not snippet_text:
            return jsonify({'success': False, 'message': 'video_id and snippet_text are required'}), 400

        result = snippet_manager.create_snippet(
            video_id=video_id,
            snippet_text=snippet_text,
            context_before=context_before,
            context_after=context_after,
            tags=tags
        )

        if result['success']:
            return jsonify({'success': True, 'message': result['message']})
        else:
            return jsonify({'success': False, 'message': result['message']}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/snippets')
def get_snippets():
    """API endpoint to get snippets"""
    try:
        video_id = request.args.get('video_id')
        limit = int(request.args.get('limit', 100))

        if video_id:
            snippets = snippet_manager.get_snippets_by_video(video_id, limit)
        else:
            snippets = snippet_manager.storage.get_memory_snippets(limit=limit)
        
        return jsonify({'success': True, 'snippets': snippets})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/snippets/<snippet_id>', methods=['DELETE'])
def delete_snippet(snippet_id):
    """API endpoint to delete a snippet"""
    try:
        result = snippet_manager.delete_snippet(snippet_id)
        if result['success']:
            return jsonify({'success': True, 'message': result['message']})
        else:
            return jsonify({'success': False, 'message': result['message']}), 404

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/snippets/<snippet_id>/tags', methods=['PUT'])
def update_snippet_tags(snippet_id):
    """API endpoint to update snippet tags"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        tags = data.get('tags', [])

        result = snippet_manager.update_snippet_tags(snippet_id, tags)
        if result['success']:
            return jsonify({'success': True, 'message': result['message']})
        else:
            return jsonify({'success': False, 'message': result['message']}), 404

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/<channel_handle>/import', methods=['POST'])
def import_channel_videos(channel_handle):
    """API endpoint to import latest videos from a channel by handle"""
    try:
        # Get channel info by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return jsonify({
                'success': False,
                'error': f'Channel not found: {channel_handle}'
            }), 404
        
        # Decode URL-encoded channel handle
        decoded_channel_handle = unquote(channel_handle)
        print(f"Original channel handle: {channel_handle}")
        print(f"Decoded channel handle: {decoded_channel_handle}")
        print(f"Channel name: {channel_info['channel_name']}")
        
        data = request.get_json() if request.content_type == 'application/json' else {}
        
        # Get default values from import settings
        import_settings = database_storage.get_import_settings()
        # Prioritize camelCase settings (from frontend) over underscore settings (original)
        default_max_results = import_settings.get('defaultMaxResults', import_settings.get('default_max_results', 20))
        default_days_back = import_settings.get('defaultDaysBack', import_settings.get('default_days_back', 30))
        max_results_limit = import_settings.get('maxResultsLimit', import_settings.get('max_results_limit', 50))
        
        # Ensure all values are converted to integers to prevent type comparison errors
        max_results = int(data.get('max_results', default_max_results))
        days_back = int(data.get('days_back', default_days_back))
        max_results_limit = int(max_results_limit)
        
        # 🎯 TIME-BASED IMPORT: Get videos from selected time period up to safety limit
        # The max_results_limit serves as a safety limit to prevent runaway imports
        # For time-based imports, we want to get ALL videos from the period (up to the limit)
        original_max_results = max_results
        
        # For time-based selections, use the maxResultsLimit as the target
        # (This allows getting all videos from the time period up to a reasonable safety limit)
        max_results = max_results_limit
        
        if max_results != original_max_results:
            print(f"🎯 Time-based import for {days_back} days: targeting {max_results} videos (safety limit)")
        
        # Support per-request override of import_shorts setting
        request_import_shorts = data.get('import_shorts')
        if request_import_shorts is not None:
            # Temporarily override the import_shorts setting for this request
            original_import_shorts = import_settings.get('import_shorts', False)
            import_settings['import_shorts'] = bool(request_import_shorts)
            print(f"Overriding import_shorts setting for this request: {bool(request_import_shorts)}")
        
        # Validate parameters using (possibly adjusted) settings
        if max_results > max_results_limit:
            max_results = max_results_limit
        if days_back < 1 or days_back > 365:  # Reasonable range: 1 day to 1 year
            days_back = default_days_back
        
        # Check if YouTube API is configured
        if not youtube_api.is_available():
            return jsonify({
                'success': False,
                'error': 'YouTube Data API not configured. Please set YOUTUBE_API_KEY environment variable.'
            }), 400
        
        # Get latest videos from channel using channel name for the YouTube API
        print(f"Fetching {max_results} videos from channel: {channel_info['channel_name']} within {days_back} days")
        import_result = youtube_api.get_channel_videos(channel_info['channel_name'], max_results, days_back, import_settings)
        
        videos = import_result['videos']
        metadata = import_result['metadata']
        
        # Check if no videos were found
        if not videos:
            # Distinguish between different scenarios
            if metadata['total_found'] == 0:
                # No videos exist in the time range
                return jsonify({
                    'success': False,
                    'error': f'No videos found for channel "{channel_info["channel_name"]}" within {days_back} days',
                    'metadata': {
                        'total_found': metadata['total_found'],
                        'existing_count': metadata['existing_count'],
                        'days_back': days_back
                    }
                }), 404
            elif metadata['existing_count'] > 0:
                # Videos exist but all are already imported
                return jsonify({
                    'success': True,
                    'message': f'All {metadata["existing_count"]} videos from "{channel_info["channel_name"]}" within {days_back} days are already imported',
                    'channel_name': channel_info['channel_name'],
                    'total_videos': 0,
                    'processed': 0,
                    'skipped': metadata['existing_count'],
                    'errors': 0,
                    'metadata': {
                        'total_found': metadata['total_found'],
                        'existing_count': metadata['existing_count'],
                        'days_back': days_back,
                        'strategy_used': metadata['strategy_used']
                    },
                    'results': []
                })
            else:
                # Fallback generic message
                return jsonify({
                    'success': False,
                    'error': f'No videos found for channel: {channel_handle}'
                }), 404
        
        # Process each video (existing videos are already filtered out by YouTube API layer)
        results = []
        processed_count = 0
        skipped_count = 0
        error_count = 0
        
        print(f"🚀 Processing {len(videos)} videos (existing videos already filtered out)")
        
        for video in videos:
            video_id = video['video_id']
            channel_id = video.get('channel_id')
            print(f"Processing video: {video_id} - {video['title']}")
            
            result = video_processor.process_video_complete(video_id, channel_id)
            results.append(result)
            
            if result['status'] == 'processed':
                processed_count += 1
            elif result['status'] == 'exists':
                skipped_count += 1
            else:
                error_count += 1
        
        return jsonify({
            'success': True,
            'channel_name': channel_info['channel_name'],
            'total_videos': len(videos),
            'processed': processed_count,
            'skipped': skipped_count + metadata['existing_count'],  # Include both API-level and processing-level skips
            'errors': error_count,
            'metadata': {
                'total_found': metadata['total_found'],
                'existing_count': metadata['existing_count'],
                'days_back': days_back,
                'strategy_used': metadata['strategy_used']
            },
            'results': results
        })
        
    except Exception as e:
        print(f"Error importing channel videos: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/@<channel_handle>/blog-posts')
def get_blog_posts(channel_handle):
    """API endpoint to get paginated blog posts (videos with summaries) for infinite scrolling"""
    try:
        # Get channel info by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return jsonify({
                'success': False,
                'error': f'Channel not found: {channel_handle}'
            }), 404
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Ensure reasonable pagination limits
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 50:
            per_page = 10
        
        # Get videos for this channel
        channel_videos = database_storage.get_videos_by_channel(channel_id=channel_info['channel_id'])
        
        if not channel_videos:
            return jsonify({
                'success': True,
                'posts': [],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': 0,
                    'total_pages': 0,
                    'has_next': False,
                    'has_prev': False
                }
            })
        
        # Filter videos that have summaries and sort by published_at (most recent first)
        videos_with_summaries = []
        for video in channel_videos:
            summary = database_storage.get_summary(video['video_id'])
            if summary:
                videos_with_summaries.append({
                    'video_id': video['video_id'],
                    'title': video['title'],
                    'channel_name': video.get('channel_name'),
                    'channel_id': video.get('channel_id'),
                    'duration': video['duration'],
                    'thumbnail_url': f"https://img.youtube.com/vi/{video['video_id']}/maxresdefault.jpg",
                    'summary': summary,
                    'published_at': video.get('published_at'),
                    'url_path': video.get('url_path'),
                    'uploader': video.get('uploader')
                })
        
        # Sort by published_at descending (most recent first), then by created_at as fallback
        videos_with_summaries.sort(
            key=lambda x: x.get('published_at') or '1970-01-01', 
            reverse=True
        )
        
        # Calculate pagination
        total_posts = len(videos_with_summaries)
        total_pages = (total_posts + per_page - 1) // per_page
        
        # Get posts for current page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        posts_page = videos_with_summaries[start_idx:end_idx]
        
        # Format summaries as HTML
        for post in posts_page:
            post['summary'] = format_summary_html(post['summary'])
        
        return jsonify({
            'success': True,
            'posts': posts_page,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_posts,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/@<channel_handle>/chat', methods=['POST'])
def chat_with_channel(channel_handle):
    """API endpoint to chat with AI using channel summaries as context"""
    try:
        # Get channel info by handle
        channel_info = database_storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return jsonify({
                'success': False,
                'error': f'Channel not found: {channel_handle}'
            }), 404
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No request data provided'
            }), 400
        
        user_message = data.get('message', '').strip()
        selected_model = data.get('model', 'gpt-4.1-mini')
        conversation_id = data.get('conversation_id')
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': 'No message provided'
            }), 400
        
        # Get all videos for this channel
        channel_videos = database_storage.get_videos_by_channel(channel_id=channel_info['channel_id'])
        if not channel_videos:
            return jsonify({
                'success': False,
                'error': 'No videos found for this channel'
            }), 404
        
        # Gather all AI summaries for context (NOT transcripts as requested)
        summaries_context = []
        total_tokens_estimate = 0
        max_tokens_for_context = 20000  # Leave room for prompt and response
        
        for video in channel_videos:
            summary = database_storage.get_summary(video['video_id'])
            if summary:
                # Truncate very long summaries to manage token usage
                truncated_summary = summary[:2000] + "..." if len(summary) > 2000 else summary
                
                # Add video metadata for better context
                video_context = f"""
Video: {video['title']}
Published: {video.get('published_at', 'Unknown')}
Summary: {truncated_summary}
"""
                
                # Rough token estimate (1 token ≈ 4 characters)
                context_tokens = len(video_context) // 4
                
                if total_tokens_estimate + context_tokens > max_tokens_for_context:
                    print(f"Token limit reached, using {len(summaries_context)} of {len(channel_videos)} videos")
                    break
                    
                summaries_context.append(video_context)
                total_tokens_estimate += context_tokens
        
        if not summaries_context:
            return jsonify({
                'success': False,
                'error': 'No AI summaries found for this channel. Generate some summaries first.'
            }), 404
        
        # Prepare context for AI
        context = f"""You are an AI assistant with access to AI summaries from the YouTube channel "{channel_info['channel_name']}". 

Here are all the AI summaries from this channel's videos:

{chr(10).join(summaries_context)}

Based on these summaries, please answer the user's question about this channel's content. You have comprehensive knowledge of all topics, themes, and insights covered in this channel's videos.

User question: {user_message}"""
        
        # Use the summarizer to chat (it handles multiple AI providers)
        try:
            response = video_processor.summarizer.summarize_with_model(
                transcript_content=context,
                model=selected_model,
                chapters=None,
                custom_prompt="""You are a helpful AI assistant answering questions about a YouTube channel based on AI summaries of its videos. 

Format your responses with proper markdown for readability:
- Use bullet points (-) for lists
- Use **bold text** for emphasis
- Use clear section headers when appropriate
- Structure information logically with line breaks
- Be conversational, helpful, and reference specific videos when relevant

Always format your response with clear structure and markdown formatting."""
            )
            
            # Handle conversation persistence
            if conversation_id:
                # Update existing conversation
                database_storage.add_chat_message(conversation_id, 'user', user_message)
                database_storage.add_chat_message(conversation_id, 'assistant', response)
                database_storage.update_chat_conversation(conversation_id, selected_model)
            else:
                # Create new conversation
                conversation_title = user_message[:50] + ('...' if len(user_message) > 50 else '')
                conversation_id = database_storage.create_chat_conversation(
                    channel_info['channel_id'], 
                    conversation_title, 
                    selected_model
                )
                database_storage.add_chat_message(conversation_id, 'user', user_message)
                database_storage.add_chat_message(conversation_id, 'assistant', response)
            
            return jsonify({
                'success': True,
                'response': response,
                'model_used': selected_model,
                'channel_name': channel_info['channel_name'],
                'summaries_count': len(summaries_context),
                'total_videos': len(channel_videos),
                'tokens_estimate': total_tokens_estimate,
                'conversation_id': conversation_id
            })
            
        except Exception as e:
            error_message = str(e)
            
            # If still hitting token limits, try with fewer summaries
            if 'rate_limit_exceeded' in error_message or 'Request too large' in error_message:
                if len(summaries_context) > 2:
                    # Retry with only the most recent 2 summaries
                    reduced_context = summaries_context[:2]
                    reduced_context_str = f"""You are an AI assistant with access to AI summaries from the YouTube channel "{channel_info['channel_name']}". 

Here are some AI summaries from this channel's videos (showing {len(reduced_context)} most recent):

{chr(10).join(reduced_context)}

Based on these summaries, please answer the user's question about this channel's content. Note: This is a subset of the channel's content due to length limits.

User question: {user_message}"""
                    
                    try:
                        response = video_processor.summarizer.summarize_with_model(
                            transcript_content=reduced_context_str,
                            model=selected_model,
                            chapters=None,
                            custom_prompt="You are a helpful AI assistant answering questions about a YouTube channel based on AI summaries of its videos. Be conversational, helpful, and reference specific videos when relevant. Note that you only have access to a subset of the channel's content."
                        )
                        
                        return jsonify({
                            'success': True,
                            'response': response + "\n\n*Note: Response based on limited summaries due to token constraints.*",
                            'model_used': selected_model,
                            'channel_name': channel_info['channel_name'],
                            'summaries_count': len(reduced_context),
                            'total_videos': len(channel_videos),
                            'tokens_estimate': sum(len(ctx) // 4 for ctx in reduced_context),
                            'truncated': True
                        })
                    except Exception as retry_error:
                        return jsonify({
                            'success': False,
                            'error': f'AI model error (even with reduced context): {str(retry_error)}'
                        }), 500
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Content too large for selected model. Try using a model with higher token limits or contact support.'
                    }), 400
            else:
                return jsonify({
                    'success': False,
                    'error': f'AI model error: {error_message}'
                }), 500
            
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/@<channel_handle>/chat-history', methods=['GET'])
def get_chat_history(channel_handle):
    """Get chat history for a channel."""
    try:
        from src.database_storage import DatabaseStorage
        storage = DatabaseStorage()
        
        # Get channel info
        channel_info = storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return jsonify({'error': 'Channel not found'}), 404
        
        # Get conversations
        conversations = storage.get_chat_conversations(channel_info['channel_id'])
        
        return jsonify({
            'success': True,
            'conversations': conversations
        })
        
    except Exception as e:
        print(f"Error getting chat history: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/@<channel_handle>/chat-history/<conversation_id>', methods=['GET'])
def get_chat_conversation(channel_handle, conversation_id):
    """Get specific conversation with messages."""
    try:
        from src.database_storage import DatabaseStorage
        storage = DatabaseStorage()
        
        # Get channel info
        channel_info = storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return jsonify({'error': 'Channel not found'}), 404
        
        # Get conversation
        conversation = storage.get_chat_conversation(conversation_id, channel_info['channel_id'])
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Get messages
        messages = storage.get_chat_messages(conversation_id)
        
        return jsonify({
            'success': True,
            'conversation': conversation,
            'messages': messages
        })
        
    except Exception as e:
        print(f"Error getting conversation: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/@<channel_handle>/chat-history/<conversation_id>', methods=['DELETE'])
def delete_chat_conversation(channel_handle, conversation_id):
    """Delete a conversation."""
    try:
        from src.database_storage import DatabaseStorage
        storage = DatabaseStorage()
        
        # Get channel info
        channel_info = storage.get_channel_by_handle(channel_handle)
        if not channel_info:
            return jsonify({'error': 'Channel not found'}), 404
        
        # Delete conversation
        success = storage.delete_chat_conversation(conversation_id, channel_info['channel_id'])
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Conversation not found'}), 404
        
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        return jsonify({'error': str(e)}), 500

# Global Chat API Routes
@api_bp.route('/chat/global', methods=['POST'])
def global_chat():
    """Handle global chat messages across all channels."""
    try:
        from src.database_storage import DatabaseStorage
        from src.summarizer import summarizer
        
        storage = DatabaseStorage()
        data = request.get_json()
        
        if not data or 'message' not in data or 'model' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        message = data['message'].strip()
        model = data['model']
        conversation_id = data.get('conversation_id')
        
        if not message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Get all summaries for global context
        all_summaries = storage.get_all_summaries_for_global_chat()
        
        if not all_summaries:
            return jsonify({'error': 'No video summaries available for chat context'}), 400
        
        # Create conversation context from all summaries
        context_parts = []
        for summary in all_summaries:
            context_parts.append(
                f"Channel: {summary['channel_name']} (@{summary['channel_handle']})\n"
                f"Video: {summary['video_title']}\n"
                f"Summary: {summary['summary_text']}\n"
            )
        
        full_context = "\n---\n".join(context_parts)
        
        # Limit context to avoid token limits (approximately 20,000 tokens)
        max_context_length = 60000  # roughly 20k tokens
        if len(full_context) > max_context_length:
            # Truncate and add note
            full_context = full_context[:max_context_length] + "\n\n[Context truncated due to length]"
        
        # Prepare the prompt
        system_prompt = f"""You are an AI assistant helping analyze YouTube video content. You have access to summaries from multiple YouTube channels and videos. Answer questions based on this content.

Context from video summaries:
{full_context}

Instructions:
- Answer questions based on the provided video summaries
- If asked about specific channels, focus on content from those channels
- Provide insights, analysis, and connections between different videos/channels
- Be helpful and informative
- If you cannot answer based on the available content, say so
- Reference specific videos or channels when relevant
"""
        
        # Create or get conversation
        if not conversation_id:
            # For global chat, we need an original channel - use the first available channel
            if all_summaries:
                # Extract channel_id from the first summary (we need to get it from the database)
                first_channel_handle = all_summaries[0]['channel_handle']
                channel_info = storage.get_channel_by_handle(first_channel_handle)
                original_channel_id = channel_info['channel_id'] if channel_info else None
                
                if original_channel_id:
                    conversation_id = storage.create_global_chat_conversation(
                        original_channel_id=original_channel_id,
                        title=message[:50] + '...' if len(message) > 50 else message,
                        model_used=model,
                        chat_type='global'
                    )
        
        if not conversation_id:
            return jsonify({'error': 'Failed to create conversation'}), 500
        
        # Add user message to database
        storage.add_chat_message(conversation_id, 'user', message)
        
        # Get AI response
        try:
            response_text = summarizer.chat_with_context(
                message=message,
                context=system_prompt,
                model=model
            )
            
            if not response_text:
                response_text = "I apologize, but I couldn't generate a response at the moment. Please try again."
            
        except Exception as e:
            print(f"Error getting AI response: {e}")
            response_text = "I encountered an error while processing your request. Please try again."
        
        # Add assistant response to database
        storage.add_chat_message(conversation_id, 'assistant', response_text)
        
        # Update conversation timestamp
        storage.update_chat_conversation(conversation_id, model)
        
        return jsonify({
            'success': True,
            'response': response_text,
            'conversation_id': conversation_id
        })
        
    except Exception as e:
        print(f"Error in global chat: {e}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your request'
        }), 500

@api_bp.route('/chat/global/history', methods=['GET'])
def get_global_chat_history():
    """Get global chat history across all channels."""
    try:
        from src.database_storage import DatabaseStorage
        storage = DatabaseStorage()
        
        # Get all conversations with channel info
        conversations = storage.get_global_chat_conversations()
        
        return jsonify({
            'success': True,
            'conversations': conversations
        })
        
    except Exception as e:
        print(f"Error getting global chat history: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/chat/global/history/<conversation_id>', methods=['GET'])
def get_global_chat_conversation(conversation_id):
    """Get specific global conversation with messages."""
    try:
        from src.database_storage import DatabaseStorage
        storage = DatabaseStorage()
        
        # Get conversation with channel info
        conversation = storage.get_global_chat_conversation(conversation_id)
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Get messages
        messages = storage.get_chat_messages(conversation_id)
        
        return jsonify({
            'success': True,
            'conversation': conversation,
            'messages': messages
        })
        
    except Exception as e:
        print(f"Error getting global conversation: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/chat/global/history/<conversation_id>', methods=['DELETE'])
def delete_global_chat_conversation(conversation_id):
    """Delete a global conversation."""
    try:
        from src.database_storage import DatabaseStorage
        storage = DatabaseStorage()
        
        # Delete conversation
        success = storage.delete_global_chat_conversation(conversation_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Conversation not found'}), 404
        
    except Exception as e:
        print(f"Error deleting global conversation: {e}")
        return jsonify({'error': str(e)}), 500

