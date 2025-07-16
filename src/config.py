"""
Configuration module for YouTube Deep Summary application
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the application"""
    
    # Flask configuration
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 33079))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # OpenAI configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1')
    OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', 100000))
    OPENAI_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', 0.7))
    
    # Anthropic configuration
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    ANTHROPIC_MODEL = os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
    
    # Supabase configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    # YouTube API configuration
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
    YOUTUBE_PROXY = os.getenv('YOUTUBE_PROXY')
    
    @classmethod
    def is_openai_configured(cls):
        """Check if OpenAI API is configured"""
        return bool(cls.OPENAI_API_KEY)
    
    @classmethod
    def is_anthropic_configured(cls):
        """Check if Anthropic API is configured"""
        return bool(cls.ANTHROPIC_API_KEY)
    
    @classmethod
    def is_youtube_api_configured(cls):
        """Check if YouTube API is configured"""
        return bool(cls.YOUTUBE_API_KEY)
    
    @classmethod
    def get_proxy_config(cls):
        """Get proxy configuration for HTTP requests"""
        if cls.YOUTUBE_PROXY:
            return {
                'http': f'http://{cls.YOUTUBE_PROXY}',
                'https': f'http://{cls.YOUTUBE_PROXY}'
            }
        return None