#!/usr/bin/env python3
"""
YouTube Transcript Web Viewer

A Flask web application that accepts YouTube video IDs and displays transcripts.
Refactored version with modular architecture.
"""

from flask import Flask
from src.database_storage import database_storage
from src.config import Config

# Import route blueprints
from src.routes.main import main_bp
from src.routes.api import api_bp
from src.routes.channels import channels_bp
from src.routes.videos import videos_bp
from src.routes.snippets import snippets_bp
from src.routes.settings import settings_bp
from src.routes.chat import chat_bp

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(channels_bp)
    app.register_blueprint(videos_bp)
    app.register_blueprint(snippets_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(chat_bp)
    
    return app

def main():
    """Main entry point"""
    app = create_app()
    
    # Initialize database storage on startup
    database_storage.clear_expired()
    
    # Get configuration
    proxy = Config.YOUTUBE_PROXY
    host = Config.FLASK_HOST
    port = Config.FLASK_PORT
    debug = Config.FLASK_DEBUG
    
    if proxy:
        print(f"Using proxy: {proxy}")
    else:
        print("No proxy configured")
    
    print(f"OpenAI API configured: {Config.is_openai_configured()}")
    
    # Show database info
    cache_info = database_storage.get_cache_info()
    print(f"Database: {cache_info['videos_count']} videos, {cache_info['transcripts_count']} transcripts, {cache_info['summaries_count']} summaries")
    
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    main()