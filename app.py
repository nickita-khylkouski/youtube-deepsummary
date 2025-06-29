#!/usr/bin/env python3
"""
YouTube Transcript Web Viewer

A Flask web application that accepts YouTube video IDs and displays transcripts.
"""

import os
from flask import Flask, request, render_template, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
import re
from transcript_summarizer import TranscriptSummarizer, format_transcript_for_readability, extract_video_chapters, extract_video_info
from transcript_cache import transcript_cache
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
        # Check cache first
        cached_data = transcript_cache.get(video_id)
        
        if cached_data:
            print(f"Using cached data for video: {video_id}")
            transcript = cached_data['transcript']
            video_info = cached_data['video_info']
            formatted_transcript_text = cached_data['formatted_transcript']
            
            video_title = video_info.get('title')
            chapters = video_info.get('chapters')
            video_duration = video_info.get('duration')
            video_uploader = video_info.get('uploader')
        else:
            print(f"Cache MISS for video: {video_id}, downloading fresh data")
            transcript = get_transcript(video_id)
            
            # Extract video info (title, chapters, etc.)
            print(f"Extracting video info for: {video_id}")
            try:
                video_info = extract_video_info(video_id)
                video_title = video_info.get('title')
                chapters = video_info.get('chapters')
                video_duration = video_info.get('duration')
                video_uploader = video_info.get('uploader')
                
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
                    'uploader': None
                }
                video_title = None
                chapters = None
                video_duration = None
                video_uploader = None
            
            # Format transcript for improved readability
            formatted_transcript_text = format_transcript_for_readability(transcript, chapters)
            
            # Cache the data for future use
            transcript_cache.set(video_id, transcript, video_info, formatted_transcript_text)
        
        proxy_used = os.getenv('YOUTUBE_PROXY', 'None')
        
        # Remove automatic summary generation - now handled via AJAX
        summary = None
        summary_error = None
        
        # Generate thumbnail URL
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        
        return render_template('transcript.html', 
                             video_id=video_id,
                             video_title=video_title,
                             video_duration=video_duration,
                             video_uploader=video_uploader,
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
        # Check cache first for API endpoint too
        cached_data = transcript_cache.get(video_id)
        
        if cached_data:
            print(f"API: Using cached data for video: {video_id}")
            transcript = cached_data['transcript']
            video_info = cached_data['video_info']
            formatted_transcript = cached_data['formatted_transcript']
            chapters = video_info.get('chapters')
        else:
            print(f"API: Cache MISS for video: {video_id}, downloading fresh data")
            transcript = get_transcript(video_id)
            video_info = extract_video_info(video_id)
            chapters = video_info.get('chapters')
            formatted_transcript = format_transcript_for_readability(transcript, chapters)
            
            # Cache the data
            transcript_cache.set(video_id, transcript, video_info, formatted_transcript)
        
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'video_title': video_info.get('title'),
            'video_duration': video_info.get('duration'),
            'video_uploader': video_info.get('uploader'),
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
        
        if not video_id or not formatted_transcript:
            return jsonify({
                'success': False,
                'error': 'video_id and formatted_transcript are required'
            }), 400
        
        # Generate summary using provided formatted transcript text
        summary = summarizer.summarize_with_openai(formatted_transcript)
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'summary': summary
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cache/info')
def api_cache_info():
    """API endpoint to get cache statistics"""
    try:
        cache_info = transcript_cache.get_cache_info()
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
    """API endpoint to clean up expired cache files"""
    try:
        transcript_cache.clear_expired()
        cache_info = transcript_cache.get_cache_info()
        return jsonify({
            'success': True,
            'message': 'Expired cache files removed',
            'cache_info': cache_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Clean up expired cache files on startup
    transcript_cache.clear_expired()
    
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
    
    # Show cache info
    cache_info = transcript_cache.get_cache_info()
    print(f"Cache: {cache_info['valid_files']} valid files, {cache_info['expired_files']} expired files")
    
    app.run(host=host, port=port, debug=debug)