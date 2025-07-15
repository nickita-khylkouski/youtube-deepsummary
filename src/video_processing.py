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
    
    def process_video_complete(self, video_id, channel_id=None):
        """Process a video completely: get transcript, video info, and AI summary"""
        try:
            # Check if video already exists in database
            cached_data = database_storage.get(video_id)
            if cached_data:
                print(f"Video {video_id} already processed, skipping")
                return {'status': 'exists', 'video_id': video_id}
            
            # Get transcript
            print(f"Getting transcript for {video_id}")
            transcript = self.get_transcript(video_id)
            
            # Get video info and chapters
            print(f"Getting video info for {video_id}")
            video_info = self.chapter_extractor.extract_video_info(video_id)
            
            # Format transcript
            formatted_transcript = self.transcript_formatter.format_for_readability(transcript, video_info.get('chapters'))
            
            # Store in database
            # Get channel information if channel_id is available
            channel_info = None
            if channel_id:
                channel_info = youtube_api.get_channel_info(channel_id)
            database_storage.set(video_id, transcript, video_info, formatted_transcript, channel_id, channel_info)
            
            # Generate AI summary if summarizer is configured
            summary_generated = False
            if self.summarizer and self.summarizer.is_configured():
                try:
                    print(f"Generating AI summary for {video_id}")
                    summary = self.summarizer.summarize_with_openai(formatted_transcript, 
                                                                 chapters=video_info.get('chapters'), 
                                                                 video_id=video_id, 
                                                                 video_info=video_info)
                    database_storage.save_summary(video_id, summary)
                    summary_generated = True
                    print(f"AI summary generated and saved for {video_id}")
                except Exception as e:
                    print(f"Failed to generate summary for {video_id}: {e}")
            
            return {
                'status': 'processed',
                'video_id': video_id,
                'title': video_info.get('title', ''),
                'summary_generated': summary_generated
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
        
        # Get video info and chapters from database to include in summary
        cached_data = database_storage.get(video_id)
        chapters = None
        video_info = None
        if cached_data and cached_data.get('video_info'):
            video_info = cached_data['video_info']
            chapters = video_info.get('chapters')
        
        # Generate new summary using provided formatted transcript text
        print(f"Generating new summary for video {video_id}")
        summary = self.summarizer.summarize_with_openai(formatted_transcript, chapters=chapters, video_id=video_id, video_info=video_info)
        
        # Save the summary to database
        try:
            database_storage.save_summary(video_id, summary)
            print(f"Summary saved to database for video {video_id}")
        except Exception as e:
            print(f"Warning: Failed to save summary to database: {e}")
        
        return summary, False


# Global video processor instance
video_processor = VideoProcessor()