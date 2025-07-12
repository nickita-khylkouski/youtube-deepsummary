#!/usr/bin/env python3
"""
Script to create the user_notes table in Supabase
Run this script to set up the notes functionality
"""

from database_storage import database_storage

def create_notes_table():
    """Create the user_notes table and test it"""
    
    print("=== Creating user_notes table ===")
    print("NOTE: You need to run this SQL in your Supabase SQL Editor:")
    print()
    print("-- Create user_notes table")
    print("CREATE TABLE IF NOT EXISTS user_notes (")
    print("    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,")
    print("    notes_content TEXT NOT NULL DEFAULT '',")
    print("    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),")
    print("    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()")
    print(");")
    print()
    print("-- Create index")
    print("CREATE INDEX IF NOT EXISTS idx_user_notes_updated_at ON user_notes(updated_at DESC);")
    print()
    print("-- Enable RLS")
    print("ALTER TABLE user_notes ENABLE ROW LEVEL SECURITY;")
    print()
    print("-- Create policy")
    print("CREATE POLICY \"Allow public access to user_notes\" ON user_notes FOR ALL USING (true);")
    print()
    
    # Try to test if table exists
    try:
        print("Testing if table exists...")
        notes = database_storage.get_notes()
        print("✅ Table exists! Current notes length:", len(notes))
        
        # Try to save a test note
        test_result = database_storage.save_notes("Test note - created by setup script")
        if test_result:
            print("✅ Notes functionality working!")
        else:
            print("❌ Notes save failed")
            
    except Exception as e:
        print("❌ Table doesn't exist yet. Error:", e)
        print()
        print("Please copy and paste the SQL above into your Supabase SQL Editor and run it.")
        print("Then run this script again to test.")

if __name__ == "__main__":
    create_notes_table()