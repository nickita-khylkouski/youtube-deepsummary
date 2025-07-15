"""
Video processing module for transcript extraction and summarization
"""
from youtube_transcript_api import YouTubeTranscriptApi
from .transcript_summarizer import TranscriptSummarizer, format_transcript_for_readability, extract_video_info
from .database_storage import database_storage
from .youtube_api import youtube_api
from .config import Config


class VideoProcessor:
    """Handles video processing including transcript extraction and AI summarization"""
    
    def __init__(self):
        # Initialize summarizer with error handling
        try:
            self.summarizer = TranscriptSummarizer()
            print(f"Summarizer initialized. OpenAI configured: {self.summarizer.is_configured()}")
        except Exception as e:
            print(f"Warning: Failed to initialize summarizer: {e}")
            self.summarizer = None
    
    def get_transcript(self, video_id):
        """Download transcript for given video ID using proxy from environment with language fallback"""
        try:
            proxies = Config.get_proxy_config()
            
            if proxies:
                print(f"Using proxy: {Config.YOUTUBE_PROXY}")
            else:
                print("No proxy configured")
            
            print(f"Fetching transcript for video ID: {video_id}")
            
            # First try to get English transcript directly
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'], proxies=proxies)
                print(f"Successfully fetched English transcript with {len(transcript_list)} entries")
                language_used = "en (English)"
            except Exception as e:
                print(f"English transcript not available: {str(e)}")
                
                # If English not available, get the first available transcript
                try:
                    print("Attempting to find available transcripts...")
                    transcript_list_data = YouTubeTranscriptApi.list_transcripts(video_id, proxies=proxies)
                    
                    # Get list of available language codes
                    available_languages = []
                    for transcript in transcript_list_data:
                        available_languages.append(transcript.language_code)
                        print(f"Available: {transcript.language} ({transcript.language_code})")
                    
                    if available_languages:
                        # Use the first available language code with the standard get_transcript method
                        first_lang = available_languages[0]
                        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[first_lang], proxies=proxies)
                        
                        # Get language name for logging
                        first_transcript = next(iter(transcript_list_data))
                        language_used = f"{first_transcript.language} ({first_transcript.language_code})"
                        print(f"Successfully fetched {language_used} transcript with {len(transcript_list)} entries")
                    else:
                        raise Exception("No transcripts found")
                        
                except Exception as fallback_error:
                    print(f"Fallback transcript fetch failed: {str(fallback_error)}")
                    raise Exception(f"No transcripts available for this video: {str(fallback_error)}")
            
            # Format the transcript
            formatted_transcript = []
            for entry in transcript_list:
                formatted_transcript.append({
                    'time': entry['start'],
                    'text': entry['text'],
                    'formatted_time': f"{int(entry['start'] // 60):02d}:{int(entry['start'] % 60):02d}"
                })
            
            print(f"Transcript language used: {language_used}")
            return formatted_transcript
            
        except Exception as e:
            print(f"Error in get_transcript: {str(e)}")
            raise Exception(f"Error downloading transcript: {str(e)}")
    
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
            
            # Get video info
            print(f"Getting video info for {video_id}")
            video_info = extract_video_info(video_id)
            
            # Format transcript
            formatted_transcript = format_transcript_for_readability(transcript, video_info.get('chapters'))
            
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