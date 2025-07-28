#!/usr/bin/env python3
"""
Test script for channel deletion functionality
Usage: python3 test_channel_deletion.py
"""

from src.database_storage import database_storage

def test_channel_deletion():
    """Test channel deletion with comprehensive verification"""
    
    print("🧪 CHANNEL DELETION TEST SCRIPT")
    print("=" * 50)
    
    # Get available channels for testing
    channels_result = database_storage.supabase.table('youtube_channels')\
        .select('channel_id, channel_name, handle')\
        .limit(10)\
        .execute()
    
    if not channels_result.data:
        print("❌ No channels found in database")
        return
    
    print("\n📋 Available channels for testing:")
    for i, channel in enumerate(channels_result.data):
        # Count associated data
        videos_count = len(database_storage.supabase.table('youtube_videos')\
            .select('video_id')\
            .eq('channel_id', channel['channel_id'])\
            .execute().data)
        
        chats_count = len(database_storage.supabase.table('chat_conversations')\
            .select('id')\
            .filter('channel_id', 'eq', channel['channel_id'])\
            .execute().data)
        
        print(f"{i+1}. {channel.get('channel_name', 'Unknown')} (@{channel.get('handle', 'Unknown')})")
        print(f"   ID: {channel['channel_id']}")
        print(f"   Videos: {videos_count}, Chats: {chats_count}")
        print()
    
    # Ask user to choose a channel
    try:
        choice = input("🎯 Enter channel number to delete (or 'q' to quit): ").strip()
        if choice.lower() == 'q':
            print("👋 Test cancelled")
            return
        
        channel_idx = int(choice) - 1
        if channel_idx < 0 or channel_idx >= len(channels_result.data):
            print("❌ Invalid channel number")
            return
        
        selected_channel = channels_result.data[channel_idx]
        channel_id = selected_channel['channel_id']
        channel_name = selected_channel.get('channel_name', 'Unknown')
        handle = selected_channel.get('handle', 'Unknown')
        
        print(f"\n🎯 Selected: {channel_name} (@{handle})")
        print(f"Channel ID: {channel_id}")
        
        # Confirm deletion
        confirm = input(f"\n⚠️  Are you sure you want to DELETE '{channel_name}' and ALL its data? (type 'DELETE' to confirm): ")
        if confirm != 'DELETE':
            print("👋 Deletion cancelled")
            return
        
        # Perform audit before deletion
        print("\n🔍 PRE-DELETION AUDIT:")
        audit_channel_data(channel_id)
        
        # Perform deletion
        print(f"\n🗑️  DELETING CHANNEL: {channel_name}")
        print("=" * 50)
        success = database_storage.delete_channel(channel_id)
        
        if success:
            print(f"\n✅ Channel '{channel_name}' deletion completed!")
        else:
            print(f"\n❌ Channel '{channel_name}' deletion failed!")
            return
        
        # Perform audit after deletion
        print("\n🔍 POST-DELETION VERIFICATION:")
        verify_deletion(channel_id, handle)
        
        print(f"\n📋 SQL VERIFICATION OPTIONS:")
        print(f"")
        print(f"🎯 OPTION 1 - Quick One-Liner (copy-paste to Supabase):")
        print(f"WITH ch AS (SELECT channel_id FROM youtube_channels WHERE handle = '{handle}')")
        print(f"SELECT 'Channel' as type, COUNT(*) as count FROM ch")
        print(f"UNION ALL SELECT 'Videos', COUNT(*) FROM youtube_videos WHERE channel_id IN (SELECT channel_id FROM ch)")
        print(f"UNION ALL SELECT 'Chats', COUNT(*) FROM chat_conversations WHERE channel_id IN (SELECT channel_id FROM ch) OR original_channel_id IN (SELECT channel_id FROM ch);")
        print(f"")
        print(f"🔍 OPTION 2 - Comprehensive Data Audit:")
        print(f"-- Edit sql/channel_data_audit.sql and replace ALL '@metalsole' with '{handle}'")
        print(f"-- Shows EVERYTHING: videos, summaries, transcripts, chats, snippets, etc.")
        print(f"")
        print(f"📊 OPTION 3 - Quick Overview:")
        print(f"-- Edit sql/channel_overview.sql and replace ALL '@metalsole' with '{handle}'")
        print(f"-- Shows counts and recent items with status icons")
        
    except ValueError:
        print("❌ Please enter a valid number")
    except KeyboardInterrupt:
        print("\n👋 Test cancelled")
    except Exception as e:
        print(f"❌ Error during test: {e}")

def audit_channel_data(channel_id: str):
    """Audit all data associated with a channel"""
    
    # Videos
    videos = database_storage.supabase.table('youtube_videos')\
        .select('video_id, title')\
        .eq('channel_id', channel_id)\
        .execute().data
    
    print(f"📹 Videos: {len(videos)}")
    
    total_transcripts = 0
    total_summaries = 0
    total_chapters = 0
    total_snippets = 0
    total_chapter_summaries = 0
    
    for video in videos:
        video_id = video['video_id']
        
        # Count associated data for each video
        transcripts = len(database_storage.supabase.table('transcripts')\
            .select('id')\
            .eq('video_id', video_id)\
            .execute().data)
        total_transcripts += transcripts
        
        summaries = len(database_storage.supabase.table('summaries')\
            .select('id')\
            .eq('video_id', video_id)\
            .execute().data)
        total_summaries += summaries
        
        chapters = len(database_storage.supabase.table('video_chapters')\
            .select('id')\
            .eq('video_id', video_id)\
            .execute().data)
        total_chapters += chapters
        
        snippets = len(database_storage.supabase.table('memory_snippets')\
            .select('id')\
            .eq('video_id', video_id)\
            .execute().data)
        total_snippets += snippets
        
        # Chapter summaries (if table exists)
        try:
            chapter_summaries = len(database_storage.supabase.table('chapter_summaries')\
                .select('id')\
                .eq('video_id', video_id)\
                .execute().data)
            total_chapter_summaries += chapter_summaries
        except:
            pass  # Table might not exist
    
    print(f"📝 Transcripts: {total_transcripts}")
    print(f"📋 Summaries: {total_summaries}")
    print(f"📚 Chapters: {total_chapters}")
    print(f"🧠 Memory Snippets: {total_snippets}")
    if total_chapter_summaries > 0:
        print(f"📑 Chapter Summaries: {total_chapter_summaries}")
    
    # Chat conversations
    chats = database_storage.supabase.table('chat_conversations')\
        .select('id')\
        .eq('channel_id', channel_id)\
        .execute().data
    
    global_chats = database_storage.supabase.table('chat_conversations')\
        .select('id')\
        .eq('original_channel_id', channel_id)\
        .execute().data
    
    total_messages = 0
    for chat in chats + global_chats:
        messages = len(database_storage.supabase.table('chat_messages')\
            .select('id')\
            .eq('conversation_id', chat['id'])\
            .execute().data)
        total_messages += messages
    
    print(f"💬 Chat Conversations: {len(chats)} (channel) + {len(global_chats)} (global)")
    print(f"💭 Chat Messages: {total_messages}")

def verify_deletion(channel_id: str, handle: str):
    """Verify that all data has been deleted"""
    
    issues = []
    
    # Check channel record
    channel_count = len(database_storage.supabase.table('youtube_channels')\
        .select('channel_id')\
        .eq('channel_id', channel_id)\
        .execute().data)
    
    if channel_count > 0:
        issues.append(f"❌ Channel record still exists ({channel_count})")
    else:
        print("✅ Channel record deleted")
    
    # Check videos
    video_count = len(database_storage.supabase.table('youtube_videos')\
        .select('video_id')\
        .eq('channel_id', channel_id)\
        .execute().data)
    
    if video_count > 0:
        issues.append(f"❌ Videos still exist ({video_count})")
    else:
        print("✅ Videos deleted")
    
    # Check chat conversations
    chat_count = len(database_storage.supabase.table('chat_conversations')\
        .select('id')\
        .filter('channel_id', 'eq', channel_id)\
        .execute().data)
    
    global_chat_count = len(database_storage.supabase.table('chat_conversations')\
        .select('id')\
        .eq('original_channel_id', channel_id)\
        .execute().data)
    
    total_chat_count = chat_count + global_chat_count
    if total_chat_count > 0:
        issues.append(f"❌ Chat conversations still exist ({chat_count} regular + {global_chat_count} global)")
    else:
        print("✅ Chat conversations deleted")
    
    # Summary
    if issues:
        print("\n⚠️  ISSUES FOUND:")
        for issue in issues:
            print(f"   {issue}")
        print(f"\n🔍 Run verification SQL queries to investigate further")
    else:
        print("\n🎉 ALL DATA SUCCESSFULLY DELETED!")

if __name__ == "__main__":
    test_channel_deletion()