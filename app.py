#!/usr/bin/env python3
"""
YouTube Transcript Web Viewer

A Flask web application that accepts YouTube video IDs and displays transcripts.
"""

import os
from flask import Flask, request, render_template, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json
from datetime import datetime, timedelta
from urllib.parse import unquote
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    print("Warning: markdown library not available. Install with: pip install markdown")

def get_channel_url_identifier(channel_info=None, channel_name=None):
    """Get the best identifier for channel URLs - prefer channel_id over name"""
    if channel_info and channel_info.get('channel_id'):
        return channel_info['channel_id']
    elif channel_name:
        return channel_name
    else:
        return 'Unknown'
try:
    from googleapiclient.discovery import build
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False
    print("Warning: google-api-python-client not available. Install with: pip install google-api-python-client")
from transcript_summarizer import TranscriptSummarizer, format_transcript_for_readability, extract_video_chapters, extract_video_info
from database_storage import database_storage
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Initialize summarizer with error handling
try:
    summarizer = TranscriptSummarizer()
    print(f"Summarizer initialized. OpenAI configured: {summarizer.is_configured()}")
except Exception as e:
    print(f"Warning: Failed to initialize summarizer: {e}")
    summarizer = None

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

def get_youtube_service():
    """Initialize YouTube Data API service"""
    if not YOUTUBE_API_AVAILABLE:
        return None
    
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        return None
    
    try:
        return build('youtube', 'v3', developerKey=api_key)
    except Exception as e:
        print(f"Failed to initialize YouTube API service: {e}")
        return None

def get_channel_info(channel_id):
    """Get channel information from YouTube API (handle, title, description)"""
    youtube_service = get_youtube_service()
    if not youtube_service:
        return None
    
    try:
        # Fetch channel information including handle, title, and description
        channel_request = youtube_service.channels().list(
            part='snippet,brandingSettings',
            id=channel_id
        )
        channel_response = channel_request.execute()
        
        if channel_response.get('items'):
            item = channel_response['items'][0]
            
            # Initialize result dictionary
            channel_info = {
                'handle': None,
                'title': None,
                'description': None,
                'thumbnail_url': None
            }
            
            # Get basic info from snippet
            if 'snippet' in item:
                snippet = item['snippet']
                channel_info['title'] = snippet.get('title')
                channel_info['description'] = snippet.get('description')
                
                # Get thumbnail URL (prefer high quality, fallback to medium, then default)
                thumbnails = snippet.get('thumbnails', {})
                if 'high' in thumbnails:
                    channel_info['thumbnail_url'] = thumbnails['high']['url']
                elif 'medium' in thumbnails:
                    channel_info['thumbnail_url'] = thumbnails['medium']['url']
                elif 'default' in thumbnails:
                    channel_info['thumbnail_url'] = thumbnails['default']['url']
                
                # Try to get handle from snippet.customUrl (most common location)
                if 'customUrl' in snippet:
                    custom_url = snippet['customUrl']
                    if custom_url and custom_url.startswith('@'):
                        channel_info['handle'] = custom_url
            
            # Check brandingSettings if no handle found
            if not channel_info['handle'] and 'brandingSettings' in item:
                if 'channel' in item['brandingSettings']:
                    branding_channel = item['brandingSettings']['channel']
                    if 'customUrl' in branding_channel:
                        custom_url = branding_channel['customUrl']
                        if custom_url and custom_url.startswith('@'):
                            channel_info['handle'] = custom_url
            
            return channel_info
        
        return None
        
    except Exception as e:
        print(f"Error fetching channel info for {channel_id}: {e}")
        return None

def get_channel_handle(channel_id):
    """Get channel handle from YouTube API (backward compatibility)"""
    channel_info = get_channel_info(channel_id)
    return channel_info['handle'] if channel_info else None

def get_channel_videos(channel_name, max_results=5):
    """Get latest videos from a channel using YouTube Data API"""
    youtube_service = get_youtube_service()
    if not youtube_service:
        raise Exception("YouTube Data API not available or not configured")
    
    try:
        # First, try to get the channel ID from the database
        actual_channel_id = None
        
        # Check if we have a channel record with this name
        channel_info = database_storage.get_channel_by_name(channel_name)
        if channel_info:
            actual_channel_id = channel_info['channel_id']
            print(f"Found channel ID {actual_channel_id} from database for channel {channel_name}")
        else:
            # Try to find an existing video from this channel to get the channel ID
            existing_videos = database_storage.get_videos_by_channel(channel_name=channel_name)
            if existing_videos:
                # Use yt-dlp or video info to try to get channel ID from an existing video
                sample_video_id = existing_videos[0]['video_id']
                try:
                    # Try to extract channel info from existing video
                    video_request = youtube_service.videos().list(
                        part='snippet',
                        id=sample_video_id
                    )
                    video_response = video_request.execute()
                    if video_response.get('items'):
                        actual_channel_id = video_response['items'][0]['snippet']['channelId']
                        print(f"Found channel ID {actual_channel_id} from existing video {sample_video_id}")
                        
                        # Get channel information if available
                        channel_info = get_channel_info(actual_channel_id)
                        
                        # Create/update channel record
                        database_storage._ensure_channel_exists(actual_channel_id, channel_name, channel_info)
                except Exception as e:
                    print(f"Could not get channel ID from existing video: {e}")
        
        # If we still don't have channel ID, try different search approaches
        if not actual_channel_id:
            channel_id, name_type = extract_channel_id_or_name(channel_name)
            
            if name_type == 'id':
                actual_channel_id = channel_id
            else:
                # Try exact channel name search first
                search_request = youtube_service.search().list(
                    part='snippet',
                    q=f'"{channel_name}"',  # Use quotes for exact match
                    type='channel',
                    maxResults=5  # Get more results to find exact match
                )
                search_response = search_request.execute()
                
                print(f"Search returned {len(search_response.get('items', []))} results for '{channel_name}'")
                for i, item in enumerate(search_response.get('items', [])):
                    print(f"  {i+1}. {item['snippet']['title']} (ID: {item['id']['channelId']})")
                
                # Look for exact match in channel titles
                best_match = None
                exact_match = None
                
                for item in search_response.get('items', []):
                    item_title = item['snippet']['title']
                    
                    # Check for exact match (case-insensitive)
                    if item_title.lower() == channel_name.lower():
                        exact_match = item
                        print(f"Found exact channel match: {item_title} -> {item['id']['channelId']}")
                        break
                    
                    # Check for close match (contains the search term)
                    elif channel_name.lower() in item_title.lower() or item_title.lower() in channel_name.lower():
                        if not best_match:
                            best_match = item
                            print(f"Found potential match: {item_title} -> {item['id']['channelId']}")
                
                if exact_match:
                    actual_channel_id = exact_match['id']['channelId']
                elif best_match:
                    actual_channel_id = best_match['id']['channelId']
                    print(f"Using best match: {best_match['snippet']['title']} -> {actual_channel_id}")
                elif search_response.get('items'):
                    # Fallback to first result
                    actual_channel_id = search_response['items'][0]['id']['channelId']
                    found_name = search_response['items'][0]['snippet']['title']
                    print(f"Using first search result: {found_name} -> {actual_channel_id}")
                
                if not actual_channel_id:
                    raise Exception(f"Channel '{channel_name}' not found")
        
        # Now get the latest videos from the specific channel using the channel ID
        print(f"Fetching videos for channel ID: {actual_channel_id}")
        
        # Method 1: Try to get the uploads playlist for this channel
        try:
            channel_request = youtube_service.channels().list(
                part='contentDetails',
                id=actual_channel_id
            )
            channel_response = channel_request.execute()
            
            if channel_response.get('items'):
                uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                print(f"Found uploads playlist: {uploads_playlist_id}")
                
                # Get videos from the uploads playlist
                playlist_request = youtube_service.playlistItems().list(
                    part='snippet',
                    playlistId=uploads_playlist_id,
                    maxResults=max_results,
                    order='date'
                )
                playlist_response = playlist_request.execute()
                
                videos = []
                for item in playlist_response.get('items', []):
                    video_id = item['snippet']['resourceId']['videoId']
                    snippet = item['snippet']
                    
                    videos.append({
                        'video_id': video_id,
                        'title': snippet.get('title', ''),
                        'description': snippet.get('description', ''),
                        'published_at': snippet.get('publishedAt', ''),
                        'thumbnail_url': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                        'channel_name': snippet.get('channelTitle', channel_name),
                        'channel_id': actual_channel_id
                    })
                
                if videos:
                    print(f"Found {len(videos)} videos from uploads playlist")
                    return videos
                    
        except Exception as e:
            print(f"Uploads playlist method failed: {e}, trying activities API")
        
        # Method 2: Use the activities endpoint to get the most recent uploads
        try:
            activities_request = youtube_service.activities().list(
                part='snippet,contentDetails',
                channelId=actual_channel_id,
                maxResults=max_results,
                publishedAfter=(datetime.utcnow() - timedelta(days=60)).isoformat() + 'Z'  # Last 60 days
            )
            activities_response = activities_request.execute()
            
            videos = []
            for item in activities_response.get('items', []):
                if (item['snippet']['type'] == 'upload' and 
                    'contentDetails' in item and 
                    'upload' in item['contentDetails']):
                    
                    video_id = item['contentDetails']['upload']['videoId']
                    snippet = item['snippet']
                    
                    videos.append({
                        'video_id': video_id,
                        'title': snippet.get('title', ''),
                        'description': snippet.get('description', ''),
                        'published_at': snippet.get('publishedAt', ''),
                        'thumbnail_url': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                        'channel_name': snippet.get('channelTitle', channel_name),
                        'channel_id': actual_channel_id
                    })
            
            if videos:
                print(f"Found {len(videos)} recent uploads using activities API")
                return videos
                
        except Exception as e:
            print(f"Activities API failed: {e}, falling back to search")
        
        # Fallback: use search API with the specific channel ID
        search_request = youtube_service.search().list(
            part='snippet',
            channelId=actual_channel_id,
            type='video',
            order='date',
            maxResults=max_results
        )
        search_response = search_request.execute()
        
        videos = []
        for item in search_response.get('items', []):
            video_id = item['id']['videoId']
            snippet = item['snippet']
            
            # Double-check that this video is actually from the right channel
            if snippet.get('channelTitle', '').lower() == channel_name.lower():
                videos.append({
                    'video_id': video_id,
                    'title': snippet.get('title', ''),
                    'description': snippet.get('description', ''),
                    'published_at': snippet.get('publishedAt', ''),
                    'thumbnail_url': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                    'channel_name': snippet.get('channelTitle', channel_name),
                    'channel_id': actual_channel_id
                })
        
        print(f"Found {len(videos)} videos using search API")
        return videos
        
    except Exception as e:
        print(f"Error fetching channel videos: {e}")
        raise Exception(f"Failed to fetch videos from channel: {str(e)}")

def process_video_complete(video_id, channel_id=None):
    """Process a video completely: get transcript, video info, and AI summary"""
    try:
        # Check if video already exists in database
        cached_data = database_storage.get(video_id)
        if cached_data:
            print(f"Video {video_id} already processed, skipping")
            return {'status': 'exists', 'video_id': video_id}
        
        # Get transcript
        print(f"Getting transcript for {video_id}")
        transcript = get_transcript(video_id)
        
        # Get video info
        print(f"Getting video info for {video_id}")
        video_info = extract_video_info(video_id)
        
        # Format transcript
        formatted_transcript = format_transcript_for_readability(transcript, video_info.get('chapters'))
        
        # Store in database
        # Get channel information if channel_id is available
        channel_info = None
        if channel_id:
            channel_info = get_channel_info(channel_id)
        database_storage.set(video_id, transcript, video_info, formatted_transcript, channel_id, channel_info)
        
        # Generate AI summary if summarizer is configured
        summary_generated = False
        if summarizer and summarizer.is_configured():
            try:
                print(f"Generating AI summary for {video_id}")
                summary = summarizer.summarize_with_openai(formatted_transcript, 
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

def get_transcript(video_id):
    """Download transcript for given video ID using proxy from environment with language fallback"""
    try:
        proxies = None
        proxy = os.getenv('YOUTUBE_PROXY')
        
        if proxy:
            proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            print(f"Using proxy: {proxy}")
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

@app.route('/')
def index():
    """Home page with instructions"""
    return render_template('index.html')

@app.route('/watch')
def watch():
    """Display transcript for YouTube video"""
    video_id_param = request.args.get('v')
    # Remove summarize parameter since we're using AJAX now
    # summarize = request.args.get('summarize', 'false').lower() == 'true'
    
    if not video_id_param:
        return render_template('error.html', 
                             error_message="No video ID provided. Please use /watch?v=VIDEO_ID"), 400
    
    video_id = extract_video_id(video_id_param)
    
    if not video_id:
        return render_template('error.html', 
                             error_message="Invalid video ID format"), 400
    
    try:
        # Check database first
        cached_data = database_storage.get(video_id)
        
        if cached_data:
            print(f"Using cached data for video: {video_id}")
            transcript = cached_data['transcript']
            video_info = cached_data['video_info']
            formatted_transcript_text = cached_data['formatted_transcript']
            
            video_title = video_info.get('title')
            chapters = video_info.get('chapters')
            video_duration = video_info.get('duration')
            channel_name = 'Unknown Channel'
            
            # Get enhanced channel information from cached data
            channel_info = None
            if 'youtube_channels' in cached_data.get('video_info', {}):
                channel_info = cached_data['video_info']['youtube_channels']
        else:
            print(f"Database MISS for video: {video_id}, downloading fresh data")
            transcript = get_transcript(video_id)
            
            # Extract video info (title, chapters, etc.)
            print(f"Extracting video info for: {video_id}")
            try:
                video_info = extract_video_info(video_id)
                video_title = video_info.get('title')
                chapters = video_info.get('chapters')
                video_duration = video_info.get('duration')
                channel_name = 'Unknown Channel'
                
                # Channel info will be determined when storing in database
                channel_info = None
                
                print(f"Video title: {video_title}")
                print(f"Chapters extracted: {chapters}")
                if chapters:
                    print(f"Found {len(chapters)} chapters")
                else:
                    print("No chapters found or chapter extraction failed")
            except Exception as e:
                print(f"Video info extraction error: {e}")
                video_info = {
                    'title': None,
                    'chapters': None,
                    'duration': None,
                }
                video_title = None
                chapters = None
                video_duration = None
                channel_name = 'Unknown Channel'
                channel_info = None
            
            # Format transcript for improved readability
            formatted_transcript_text = format_transcript_for_readability(transcript, chapters)
            
            # Try to get channel_id from video_info (extracted by yt-dlp)
            channel_id = video_info.get('channel_id') if video_info else None
            if channel_id:
                print(f"Found channel_id {channel_id} from video info for video {video_id}")
            
            # Store the data in database for future use
            # Get channel information if channel_id is available
            channel_info = None
            if channel_id:
                channel_info = get_channel_info(channel_id)
            database_storage.set(video_id, transcript, video_info, formatted_transcript_text, channel_id, channel_info)
        
        proxy_used = os.getenv('YOUTUBE_PROXY', 'None')
        
        # Check for existing summary
        existing_summary = database_storage.get_summary(video_id)
        if existing_summary:
            # Convert markdown to HTML if markdown library is available
            if MARKDOWN_AVAILABLE:
                # Pre-process bullet points to proper markdown lists
                processed_summary = existing_summary.replace('• ', '* ')
                summary = markdown.markdown(processed_summary, extensions=['nl2br', 'tables'])
                print(f"Converted existing summary for {video_id}: markdown -> HTML conversion applied")
            else:
                summary = existing_summary.replace('\n', '<br>').replace('• ', '• ')
                print(f"Fallback for {video_id}: markdown library not available")
        else:
            summary = None
        summary_error = None
        
        # Generate thumbnail URL
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        
        return render_template('transcript.html', 
                             video_id=video_id,
                             video_title=video_title,
                             video_duration=video_duration,
                             channel_info=channel_info,
                             transcript=transcript,
                             formatted_transcript=formatted_transcript_text,
                             chapters=chapters,
                             thumbnail_url=thumbnail_url,
                             proxy_used=proxy_used,
                             summary=summary,
                             summary_error=summary_error,
                             summarize_enabled=summarizer and summarizer.is_configured())
        
    except Exception as e:
        return render_template('error.html', 
                             error_message=str(e)), 500

@app.route('/api/transcript/<video_id>')
def api_transcript(video_id):
    """API endpoint to get transcript as JSON"""
    try:
        # Check database first for API endpoint too
        cached_data = database_storage.get(video_id)
        
        if cached_data:
            print(f"API: Using cached data for video: {video_id}")
            transcript = cached_data['transcript']
            video_info = cached_data['video_info']
            formatted_transcript = cached_data['formatted_transcript']
            chapters = video_info.get('chapters')
        else:
            print(f"API: Database MISS for video: {video_id}, downloading fresh data")
            transcript = get_transcript(video_id)
            video_info = extract_video_info(video_id)
            chapters = video_info.get('chapters')
            formatted_transcript = format_transcript_for_readability(transcript, chapters)
            
            # Try to get channel_id from video_info (extracted by yt-dlp)  
            channel_id = video_info.get('channel_id') if video_info else None
            if channel_id:
                print(f"API: Found channel_id {channel_id} from video info for video {video_id}")
            
            # Store the data in database
            # Get channel information if channel_id is available
            channel_info = None
            if channel_id:
                channel_info = get_channel_info(channel_id)
            database_storage.set(video_id, transcript, video_info, formatted_transcript, channel_id, channel_info)
        
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        
        # Get enhanced video data with channel information
        enhanced_video_data = database_storage.get(video_id)
        channel_info = None
        if enhanced_video_data and 'video_info' in enhanced_video_data:
            if 'youtube_channels' in enhanced_video_data['video_info']:
                channel_info = enhanced_video_data['video_info']['youtube_channels']
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'video_title': video_info.get('title'),
            'video_duration': video_info.get('duration'),
            'channel_info': channel_info,
            'transcript': transcript,
            'formatted_transcript': formatted_transcript,
            'chapters': chapters,
            'thumbnail_url': thumbnail_url,
            'proxy_used': os.getenv('YOUTUBE_PROXY', None)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/summary/<video_id>')
def api_summary(video_id):
    """API endpoint to get transcript summary as JSON (legacy - downloads transcript)"""
    try:
        if not summarizer or not summarizer.is_configured():
            return jsonify({
                'success': False,
                'error': 'OpenAI API key not configured'
            }), 400
        
        transcript = get_transcript(video_id)
        summary = summarizer.summarize_transcript(transcript)
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'summary': summary,
            'proxy_used': os.getenv('YOUTUBE_PROXY', None)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/summary', methods=['POST'])
def api_summary_with_data():
    """API endpoint to generate summary from provided transcript data"""
    try:
        if not summarizer or not summarizer.is_configured():
            return jsonify({
                'success': False,
                'error': 'OpenAI API key not configured'
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        video_id = data.get('video_id')
        formatted_transcript = data.get('formatted_transcript')
        force_regenerate = data.get('force_regenerate', False)
        
        if not video_id or not formatted_transcript:
            return jsonify({
                'success': False,
                'error': 'video_id and formatted_transcript are required'
            }), 400
        
        # First check if summary already exists in database (unless force regeneration)
        if not force_regenerate:
            existing_summary = database_storage.get_summary(video_id)
            if existing_summary:
                print(f"Using existing summary for video {video_id}")
                return jsonify({
                    'success': True,
                    'video_id': video_id,
                    'summary': existing_summary,
                    'from_cache': True
                })
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
        summary = summarizer.summarize_with_openai(formatted_transcript, chapters=chapters, video_id=video_id, video_info=video_info)
        
        # Save the summary to database
        try:
            database_storage.save_summary(video_id, summary)
            print(f"Summary saved to database for video {video_id}")
        except Exception as e:
            print(f"Warning: Failed to save summary to database: {e}")
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'summary': summary,
            'from_cache': False
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cache/info')
def api_cache_info():
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

@app.route('/api/cache/cleanup', methods=['POST'])
def api_cache_cleanup():
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

@app.route('/storage')
def storage_page():
    """Display all saved videos"""
    try:
        cached_videos = database_storage.get_all_cached_videos()
        cache_stats = database_storage.get_cache_info()
        
        return render_template('storage.html', 
                             cached_videos=cached_videos,
                             cache_stats=cache_stats)
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading storage page: {str(e)}"), 500

@app.route('/api/delete/<video_id>', methods=['DELETE'])
def api_delete_video(video_id):
    """API endpoint to delete a video from storage"""
    try:
        success = database_storage.delete(video_id)
        if success:
            return jsonify({'success': True, 'message': f'Video {video_id} deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete video'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Snippets API endpoints
@app.route('/api/snippets', methods=['POST'])
def api_save_snippet():
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

        success = database_storage.save_memory_snippet(
            video_id=video_id,
            snippet_text=snippet_text,
            context_before=context_before,
            context_after=context_after,
            tags=tags
        )

        if success:
            return jsonify({'success': True, 'message': 'Snippet saved successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to save snippet'}), 500

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/snippets')
def api_get_snippets():
    """API endpoint to get snippets"""
    try:
        video_id = request.args.get('video_id')
        limit = int(request.args.get('limit', 100))

        snippets = database_storage.get_memory_snippets(video_id=video_id, limit=limit)
        return jsonify({'success': True, 'snippets': snippets})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/snippets/<snippet_id>', methods=['DELETE'])
def api_delete_snippet(snippet_id):
    """API endpoint to delete a snippet"""
    try:
        success = database_storage.delete_memory_snippet(snippet_id)
        if success:
            return jsonify({'success': True, 'message': 'Snippet deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete snippet'}), 404

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/snippets/<snippet_id>/tags', methods=['PUT'])
def api_update_snippet_tags(snippet_id):
    """API endpoint to update snippet tags"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        tags = data.get('tags', [])

        success = database_storage.update_memory_snippet_tags(snippet_id, tags)
        if success:
            return jsonify({'success': True, 'message': 'Snippet tags updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to update snippet tags'}), 404

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/channels')
def channels_page():
    """Display all channels with video counts"""
    try:
        channels = database_storage.get_all_channels()
        return render_template('channels.html', channels=channels)
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading channels: {str(e)}"), 500

@app.route('/channel/<channel_identifier>/videos')
def channel_videos(channel_identifier):
    """Display all videos from a specific channel (by name or ID)"""
    try:
        # Try to get videos by channel_id first, then by name for backward compatibility
        channel_videos_list = None
        channel_info = None
        
        # Check if identifier looks like a channel ID (starts with UC)
        if channel_identifier.startswith('UC'):
            channel_info = database_storage.get_channel_by_id(channel_identifier)
            if channel_info:
                channel_videos_list = database_storage.get_videos_by_channel(channel_id=channel_identifier)
        
        # If not found by ID, try by name (backward compatibility)
        if not channel_videos_list:
            channel_videos_list = database_storage.get_videos_by_channel(channel_name=channel_identifier)
            if not channel_info:
                channel_info = database_storage.get_channel_by_name(channel_identifier)
        
        if not channel_videos_list:
            return render_template('error.html', 
                                 error_message=f"No videos found for channel: {channel_identifier}"), 404
        
        # Check which videos have summaries
        for video in channel_videos_list:
            video['has_summary'] = database_storage.get_summary(video['video_id']) is not None
            video['thumbnail_url'] = f"https://img.youtube.com/vi/{video['video_id']}/maxresdefault.jpg"
        
        # Use channel name from channel_info if available, otherwise use identifier
        display_name = channel_info['channel_name'] if channel_info else channel_identifier
        
        return render_template('channel_videos.html', 
                             channel_name=display_name,
                             channel_info=channel_info,
                             videos=channel_videos_list,
                             total_videos=len(channel_videos_list))
        
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading channel videos: {str(e)}"), 500

@app.route('/channel/<channel_identifier>/summaries')
def channel_summaries(channel_identifier):
    """Display AI summaries for all videos from a specific channel (by name or ID)"""
    try:
        # Try to get videos by channel_id first, then by name for backward compatibility
        channel_videos = None
        channel_info = None
        
        # Check if identifier looks like a channel ID (starts with UC)
        if channel_identifier.startswith('UC'):
            channel_info = database_storage.get_channel_by_id(channel_identifier)
            if channel_info:
                channel_videos = database_storage.get_videos_by_channel(channel_id=channel_identifier)
        
        # If not found by ID, try by name (backward compatibility)
        if not channel_videos:
            channel_videos = database_storage.get_videos_by_channel(channel_name=channel_identifier)
            if not channel_info:
                channel_info = database_storage.get_channel_by_name(channel_identifier)
        
        if not channel_videos:
            return render_template('error.html', 
                                 error_message=f"No videos found for channel: {channel_identifier}"), 404
        
        # Get summaries for each video
        summaries = []
        for video in channel_videos:
            video_id = video['video_id']
            summary = database_storage.get_summary(video_id)
            
            if summary:
                # Convert markdown to HTML if markdown library is available
                if MARKDOWN_AVAILABLE:
                    # Pre-process bullet points to proper markdown lists
                    processed_summary = summary.replace('• ', '* ')
                    summary_html = markdown.markdown(processed_summary, extensions=['nl2br', 'tables'])
                    print(f"Converted summary for {video_id}: markdown -> HTML conversion applied")
                else:
                    summary_html = summary.replace('\n', '<br>').replace('• ', '• ')
                    print(f"Fallback for {video_id}: markdown library not available")
                
                summaries.append({
                    'video_id': video_id,
                    'title': video['title'],
                    'channel_name': video.get('channel_name'),
                    'channel_id': video.get('channel_id'),
                    'duration': video['duration'],
                    'thumbnail_url': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                    'summary': summary_html,
                    'created_at': video['created_at']
                })
        
        # Use channel name from channel_info if available, otherwise use identifier
        display_name = channel_info['channel_name'] if channel_info else channel_identifier
        
        return render_template('channel_summaries.html', 
                             channel_name=display_name,
                             channel_info=channel_info,
                             summaries=summaries,
                             total_videos=len(channel_videos),
                             summarized_videos=len(summaries))
        
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading channel summaries: {str(e)}"), 500

@app.route('/snippets')
def snippets_page():
    """Display channels that have snippets"""
    try:
        snippets = database_storage.get_memory_snippets(limit=1000)
        stats = database_storage.get_memory_snippets_stats()
        
        # Group snippets by channel (use channel information from new schema)
        channel_groups = {}
        for snippet in snippets:
            # Use the enhanced channel information from get_memory_snippets
            channel_name = snippet.get('channel_name', 'Unknown Channel')
            channel_id = snippet.get('channel_id')
            
            # Use channel_id as key if available, otherwise channel_name
            channel_key = channel_id if channel_id else channel_name
            
            if channel_key not in channel_groups:
                channel_groups[channel_key] = {
                    'channel_name': channel_name,
                    'channel_id': channel_id,
                    'thumbnail_url': snippet.get('channel_thumbnail_url'),
                    'videos': {},
                    'total_snippets': 0,
                    'latest_date': ''
                }
            
            video_id = snippet['video_id']
            if video_id not in channel_groups[channel_key]['videos']:
                # Get video information from snippet
                video_info = snippet.get('youtube_videos', {})
                if not video_info:
                    video_info = {
                        'title': f'Video {video_id}',
                        'channel_name': snippet.get('channel_name', 'Unknown Channel'),
                        'thumbnail_url': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                    }
                
                channel_groups[channel_key]['videos'][video_id] = {
                    'video_info': video_info,
                    'video_id': video_id,
                    'snippet_count': 0
                }
            
            channel_groups[channel_key]['videos'][video_id]['snippet_count'] += 1
            channel_groups[channel_key]['total_snippets'] += 1
            
            # Track latest snippet date for channel
            snippet_date = snippet.get('created_at', '')
            if snippet_date > channel_groups[channel_key]['latest_date']:
                channel_groups[channel_key]['latest_date'] = snippet_date
        
        # Convert to list and sort by most recent snippet
        channels = []
        for channel_key, group in channel_groups.items():
            group['video_count'] = len(group['videos'])
            channels.append(group)
        
        # Sort channels by latest snippet date (newest first)
        channels.sort(key=lambda x: x['latest_date'], reverse=True)
        
        return render_template('snippet_channels.html', 
                             channels=channels,
                             stats=stats)
        
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Error loading snippets: {str(e)}"), 500

@app.route('/test/snippets/<channel_name>')
def test_snippets_channel(channel_name):
    """Test route for debugging snippets"""
    try:
        snippets = database_storage.get_memory_snippets(limit=10)
        return f"Channel: {channel_name}, Total snippets: {len(snippets)}, First snippet: {snippets[0] if snippets else 'None'}"
    except Exception as e:
        return f"Error: {e}"

@app.route('/snippets/channel/<channel_name>')
def snippets_channel_page(channel_name):
    """Display snippets for a specific channel"""
    try:
        print(f"Loading snippets for channel: {channel_name}")
        snippets = database_storage.get_memory_snippets(limit=1000)
        print(f"Total snippets retrieved: {len(snippets)}")
        
        # Filter snippets by channel (support both name and ID)
        channel_snippets = []
        for snippet in snippets:
            snippet_channel_name = snippet.get('channel_name', 'Unknown Channel')
            snippet_channel_id = snippet.get('channel_id')
            
            # Match by channel_id if channel_name starts with UC, otherwise by name
            if channel_name.startswith('UC'):
                if snippet_channel_id == channel_name:
                    channel_snippets.append(snippet)
            else:
                if snippet_channel_name == channel_name:
                    channel_snippets.append(snippet)
        
        print(f"Filtered snippets for channel {channel_name}: {len(channel_snippets)}")
        
        # Get channel info for header display
        channel_info = None
        if channel_snippets:
            # Use channel info from the first snippet
            first_snippet = channel_snippets[0]
            if first_snippet.get('channel_thumbnail_url'):
                channel_info = {
                    'thumbnail_url': first_snippet.get('channel_thumbnail_url'),
                    'channel_id': first_snippet.get('channel_id')
                }
        
        # If no snippets found, return empty page
        if not channel_snippets:
            return render_template('snippets.html', 
                                 video_groups=[],
                                 channel_name=channel_name,
                                 channel_info=channel_info,
                                 stats={'total_snippets': 0})
        
        # Group snippets by video_id
        grouped_snippets = {}
        for snippet in channel_snippets:
            video_id = snippet['video_id']
            if video_id not in grouped_snippets:
                # Use the enhanced video information
                video_info = snippet.get('youtube_videos', {})
                if not video_info:
                    video_info = {
                        'title': f'Video {video_id}',
                        'channel_name': snippet.get('channel_name', 'Unknown Channel')
                    }
                
                grouped_snippets[video_id] = {
                    'video_info': video_info,
                    'video_id': video_id,
                    'channel_name': snippet.get('channel_name'),
                    'channel_id': snippet.get('channel_id'),
                    'snippets': []
                }
            grouped_snippets[video_id]['snippets'].append(snippet)
        
        # Convert to list and sort by most recent snippet in each group
        video_groups = []
        for video_id, group in grouped_snippets.items():
            # Sort snippets within group by creation date (newest first)
            group['snippets'].sort(key=lambda x: x.get('created_at', ''), reverse=True)
            # Use the newest snippet's date for group sorting
            group['latest_date'] = group['snippets'][0].get('created_at', '') if group['snippets'] else ''
            video_groups.append(group)
        
        # Sort groups by latest snippet date (newest first)
        video_groups.sort(key=lambda x: x['latest_date'], reverse=True)
        
        return render_template('snippets.html', 
                             video_groups=video_groups,
                             channel_name=channel_name,
                             channel_info=channel_info,
                             stats={'total_snippets': len(channel_snippets)})
        
    except Exception as e:
        print(f"Error in snippets_channel_page for channel {channel_name}: {e}")
        print(f"Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        return render_template('error.html', 
                             error_message=f"Error loading channel snippets: {str(e)}"), 500

@app.route('/api/channels/<channel_name>/import', methods=['POST'])
def api_import_channel_videos(channel_name):
    """API endpoint to import latest videos from a channel"""
    try:
        # Decode URL-encoded channel name
        decoded_channel_name = unquote(channel_name)
        print(f"Original channel name: {channel_name}")
        print(f"Decoded channel name: {decoded_channel_name}")
        
        data = request.get_json() if request.content_type == 'application/json' else {}
        max_results = int(data.get('max_results', 5))
        
        if max_results > 20:  # Reasonable limit
            max_results = 20
        
        # Check if YouTube API is configured
        if not YOUTUBE_API_AVAILABLE or not get_youtube_service():
            return jsonify({
                'success': False,
                'error': 'YouTube Data API not configured. Please set YOUTUBE_API_KEY environment variable.'
            }), 400
        
        # Get latest videos from channel using decoded name
        print(f"Fetching {max_results} videos from channel: {decoded_channel_name}")
        videos = get_channel_videos(decoded_channel_name, max_results)
        
        if not videos:
            return jsonify({
                'success': False,
                'error': f'No videos found for channel: {channel_name}'
            }), 404
        
        # Process each video
        results = []
        processed_count = 0
        skipped_count = 0
        error_count = 0
        
        for video in videos:
            video_id = video['video_id']
            channel_id = video.get('channel_id')
            print(f"Processing video: {video_id} - {video['title']}")
            
            result = process_video_complete(video_id, channel_id)
            results.append(result)
            
            if result['status'] == 'processed':
                processed_count += 1
            elif result['status'] == 'exists':
                skipped_count += 1
            else:
                error_count += 1
        
        return jsonify({
            'success': True,
            'channel_name': decoded_channel_name,
            'total_videos': len(videos),
            'processed': processed_count,
            'skipped': skipped_count,
            'errors': error_count,
            'results': results
        })
        
    except Exception as e:
        print(f"Error importing channel videos: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/favicon.ico')
def favicon():
    """Serve favicon from static directory"""
    return app.send_static_file('favicon.ico')

if __name__ == '__main__':
    # Initialize database storage on startup
    database_storage.clear_expired()
    
    # Get configuration from environment variables
    proxy = os.getenv('YOUTUBE_PROXY')
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 33079))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    if proxy:
        print(f"Using proxy: {proxy}")
    else:
        print("No proxy configured")
    
    print(f"OpenAI API configured: {bool(os.getenv('OPENAI_API_KEY'))}")
    
    # Show database info
    cache_info = database_storage.get_cache_info()
    print(f"Database: {cache_info['videos_count']} videos, {cache_info['transcripts_count']} transcripts, {cache_info['summaries_count']} summaries")
    
    app.run(host=host, port=port, debug=debug)