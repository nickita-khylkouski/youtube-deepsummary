#!/usr/bin/env python3
"""
Script to fetch and update YouTube channel handles using the YouTube Data API v3
"""

import os
import requests
import time
from dotenv import load_dotenv
from database_storage import DatabaseStorage

# Load environment variables
load_dotenv()

def get_channel_handles(channel_ids, api_key):
    """
    Fetch channel handles from YouTube API for multiple channel IDs
    
    Args:
        channel_ids: List of YouTube channel IDs
        api_key: YouTube Data API v3 key
        
    Returns:
        Dict mapping channel_id to handle
    """
    if not channel_ids:
        return {}
    
    # YouTube API endpoint for channels
    url = "https://www.googleapis.com/youtube/v3/channels"
    
    handles = {}
    
    # Process channels in batches of 50 (API limit)
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i+50]
        
        params = {
            'part': 'snippet,brandingSettings',
            'id': ','.join(batch),
            'key': api_key
        }
        
        try:
            print(f"Fetching handles for batch {i//50 + 1} ({len(batch)} channels)")
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if 'items' in data:
                for item in data['items']:
                    channel_id = item['id']
                    
                    # Try to get handle from different locations
                    handle = None
                    
                    # Check snippet.customUrl (most common location)
                    if 'snippet' in item and 'customUrl' in item['snippet']:
                        custom_url = item['snippet']['customUrl']
                        if custom_url and custom_url.startswith('@'):
                            handle = custom_url
                    
                    # Check brandingSettings if no handle found
                    if not handle and 'brandingSettings' in item:
                        if 'channel' in item['brandingSettings']:
                            branding_channel = item['brandingSettings']['channel']
                            if 'customUrl' in branding_channel:
                                custom_url = branding_channel['customUrl']
                                if custom_url and custom_url.startswith('@'):
                                    handle = custom_url
                    
                    # Store the handle if found
                    if handle:
                        handles[channel_id] = handle
                        print(f"  Found handle for {channel_id}: {handle}")
                    else:
                        print(f"  No handle found for {channel_id}")
            
            # Rate limiting - be respectful to the API
            time.sleep(0.1)
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching batch {i//50 + 1}: {e}")
            continue
        except Exception as e:
            print(f"Unexpected error for batch {i//50 + 1}: {e}")
            continue
    
    return handles

def update_channel_handles_in_db(db_storage, handles):
    """
    Update channel handles in the database
    
    Args:
        db_storage: DatabaseStorage instance
        handles: Dict mapping channel_id to handle
    """
    updated_count = 0
    
    for channel_id, handle in handles.items():
        try:
            success = db_storage.update_channel_info(channel_id, handle=handle)
            if success:
                updated_count += 1
                print(f"Updated handle for {channel_id}: {handle}")
            else:
                print(f"Failed to update handle for {channel_id}")
        except Exception as e:
            print(f"Error updating handle for {channel_id}: {e}")
    
    return updated_count

def main():
    """Main function to update all channel handles"""
    # Check for API key
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("Error: YOUTUBE_API_KEY environment variable not set")
        print("Please set your YouTube Data API v3 key in .env file")
        return
    
    # Initialize database storage
    try:
        db_storage = DatabaseStorage()
    except Exception as e:
        print(f"Error initializing database: {e}")
        return
    
    # Get all channels from database
    try:
        channels = db_storage.get_all_channels()
        print(f"Found {len(channels)} channels in database")
        
        if not channels:
            print("No channels found in database")
            return
        
        # Extract channel IDs
        channel_ids = [channel['channel_id'] for channel in channels if channel.get('channel_id')]
        print(f"Processing {len(channel_ids)} channel IDs")
        
        # Fetch handles from YouTube API
        handles = get_channel_handles(channel_ids, api_key)
        print(f"Successfully fetched {len(handles)} handles")
        
        # Update database with handles
        if handles:
            updated_count = update_channel_handles_in_db(db_storage, handles)
            print(f"Successfully updated {updated_count} channel handles")
        else:
            print("No handles to update")
            
    except Exception as e:
        print(f"Error processing channels: {e}")

if __name__ == "__main__":
    main()