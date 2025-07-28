"""
Video processing module for transcript extraction and summarization
"""
from .transcript_extractor import transcript_extractor
from .chapter_extractor import chapter_extractor
from .summarizer import summarizer
from .transcript_formatter import transcript_formatter
from .database_storage import database_storage
from .youtube_api import youtube_api
from .config import Config


class VideoProcessor:
    """Handles video processing including transcript extraction and AI summarization"""
    
    def __init__(self):
        # Use global instances of the separated components
        self.transcript_extractor = transcript_extractor
        self.chapter_extractor = chapter_extractor
        self.summarizer = summarizer
        self.transcript_formatter = transcript_formatter
        print(f"VideoProcessor initialized. OpenAI configured: {self.summarizer.is_configured()}")
    
    def get_transcript(self, video_id):
        """Download transcript for given video ID using transcript extractor"""
        return self.transcript_extractor.extract_transcript(video_id)
    
    def process_video_complete(self, video_id, channel_id=None, force_transcript_extraction=False):
        """Process a video completely: get transcript, video info, and AI summary"""
        try:
            # Check if video already exists in database (unless forcing transcript extraction)
            cached_data = database_storage.get(video_id)
            if cached_data and not force_transcript_extraction:
                print(f"Video {video_id} already processed, skipping")
                return {'status': 'exists', 'video_id': video_id}
            
            # Get import settings to check if features are enabled
            import_settings = database_storage.get_import_settings()
            # Prioritize camelCase settings (from frontend) over underscore settings (original)
            enable_transcript_extraction = force_transcript_extraction or import_settings.get('enableTranscriptExtraction', import_settings.get('enable_transcript_extraction', True))
            enable_auto_summary = import_settings.get('enableAutoSummary', import_settings.get('enable_auto_summary', True))
            enable_chapter_extraction = import_settings.get('enableChapterExtraction', import_settings.get('enable_chapter_extraction', True))
            
            if force_transcript_extraction:
                print(f"Force transcript extraction enabled for {video_id}")
            print(f"Import settings - Transcript extraction: {enable_transcript_extraction}, Auto summary: {enable_auto_summary}, Chapter extraction: {enable_chapter_extraction}")
            
            # Get video info from YouTube API (always needed for metadata)
            print(f"Getting video info for {video_id}")
            video_info = youtube_api.get_video_info(video_id)
            
            if not video_info:
                print(f"Failed to get video info for {video_id}")
                return {'status': 'failed', 'error': 'Failed to get video information'}
            
            # Get chapters separately if enabled
            chapters = None
            if enable_chapter_extraction:
                print(f"Getting chapters for {video_id}")
                chapters = self.chapter_extractor.extract_chapters(video_id)
                video_info['chapters'] = chapters
            else:
                print(f"Chapter extraction disabled for {video_id} (disabled in settings)")
                video_info['chapters'] = None
            
            # Get transcript only if enabled
            transcript = None
            formatted_transcript = None
            if enable_transcript_extraction:
                print(f"Getting transcript for {video_id}")
                try:
                    transcript = self.get_transcript(video_id)
                    # Format transcript
                    formatted_transcript = self.transcript_formatter.format_for_readability(transcript, video_info.get('chapters'))
                except Exception as e:
                    print(f"Failed to get transcript for {video_id}: {e}")
                    # Continue without transcript if it fails
                    transcript = []
                    formatted_transcript = "Transcript extraction failed or not available."
            else:
                print(f"Skipping transcript extraction for {video_id} (disabled in settings)")
                # Don't create any transcript record when disabled
                transcript = None
                formatted_transcript = None
            
            # Store in database
            # Get channel_id from video_info if not provided
            if not channel_id and video_info:
                channel_id = video_info.get('channel_id')
            
            # Get channel information if channel_id is available
            channel_info = None
            if channel_id:
                channel_info = youtube_api.get_channel_info(channel_id)
            database_storage.set(video_id, transcript, video_info, formatted_transcript, channel_id, channel_info)
            
            # Generate AI summary if summarizer is configured and auto summary is enabled
            summary_generated = False
            if enable_auto_summary and self.summarizer and self.summarizer.is_configured():
                try:
                    print(f"Generating AI summary for {video_id}")
                    
                    # Get default prompt from database
                    default_prompt_data = database_storage.get_default_prompt()
                    custom_prompt = default_prompt_data['prompt_text'] if default_prompt_data else None
                    
                    summary = self.summarizer.summarize_with_preferred_provider(
                        formatted_transcript, 
                        chapters=video_info.get('chapters'), 
                        video_id=video_id, 
                        video_info=video_info,
                        custom_prompt=custom_prompt
                    )
                    
                    # Save summary with default prompt information
                    prompt_id = default_prompt_data['id'] if default_prompt_data else None
                    prompt_name = default_prompt_data['name'] if default_prompt_data else None
                    database_storage.save_summary(video_id, summary, self.summarizer.model, prompt_id, prompt_name)
                    summary_generated = True
                    print(f"AI summary generated and saved for {video_id}")
                except Exception as e:
                    print(f"Failed to generate summary for {video_id}: {e}")
            elif not enable_auto_summary:
                print(f"Skipping AI summary generation for {video_id} (disabled in settings)")
            
            return {
                'status': 'processed',
                'video_id': video_id,
                'title': video_info.get('title', ''),
                'summary_generated': summary_generated,
                'transcript_extracted': enable_transcript_extraction and transcript is not None
            }
            
        except Exception as e:
            print(f"Error processing video {video_id}: {e}")
            return {
                'status': 'error',
                'video_id': video_id,
                'error': str(e)
            }
    
    def generate_summary(self, video_id, formatted_transcript, force_regenerate=False):
        """Generate AI summary for a video"""
        if not self.summarizer or not self.summarizer.is_configured():
            raise Exception('OpenAI API key not configured')
        
        # First check if summary already exists in database (unless force regeneration)
        if not force_regenerate:
            existing_summary = database_storage.get_summary(video_id)
            if existing_summary:
                print(f"Using existing summary for video {video_id}")
                return existing_summary, True
        else:
            print(f"Force regenerating summary for video {video_id}")
        
        # Get default prompt from database
        default_prompt_data = database_storage.get_default_prompt()
        custom_prompt = default_prompt_data['prompt_text'] if default_prompt_data else None
        
        # Get video info and chapters from database to include in summary
        cached_data = database_storage.get(video_id)
        chapters = None
        video_info = None
        if cached_data and cached_data.get('video_info'):
            video_info = cached_data['video_info']
            chapters = video_info.get('chapters')
        
        # Generate new summary using the default prompt from database
        print(f"Generating new summary for video {video_id}")
        summary = self.summarizer.summarize_with_preferred_provider(
            formatted_transcript, 
            chapters=chapters, 
            video_id=video_id, 
            video_info=video_info,
            custom_prompt=custom_prompt
        )
        
        # Save the summary to database with default prompt information
        try:
            prompt_id = default_prompt_data['id'] if default_prompt_data else None
            prompt_name = default_prompt_data['name'] if default_prompt_data else None
            database_storage.save_summary(video_id, summary, self.summarizer.model, prompt_id, prompt_name)
            print(f"Summary saved to database for video {video_id}")
        except Exception as e:
            print(f"Warning: Failed to save summary to database: {e}")
        
        return summary, False


# Global video processor instance
video_processor = VideoProcessor()