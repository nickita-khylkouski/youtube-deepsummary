#!/usr/bin/env python3
"""
Test script for notes API functionality
"""

from flask import Flask
from app import app, database_storage
import json

def test_notes_api():
    """Test the notes API endpoints"""
    
    print("=== Testing Notes API ===")
    
    with app.test_client() as client:
        
        # Test GET notes (initially empty)
        print("\n1. Testing GET /api/notes")
        response = client.get('/api/notes')
        print(f"Status: {response.status_code}")
        data = response.get_json()
        print(f"Response: {data}")
        
        # Test POST save notes
        print("\n2. Testing POST /api/notes")
        test_notes = "This is a test note\nWith multiple lines"
        response = client.post('/api/notes', 
                              data=json.dumps({'notes': test_notes}),
                              content_type='application/json')
        print(f"Status: {response.status_code}")
        data = response.get_json()
        print(f"Response: {data}")
        
        # Test GET notes again (should have content)
        print("\n3. Testing GET /api/notes (with content)")
        response = client.get('/api/notes')
        print(f"Status: {response.status_code}")
        data = response.get_json()
        print(f"Response: {data}")
        
        # Test POST append notes
        print("\n4. Testing POST /api/notes/append")
        append_text = "\n\n--- Appended from test ---\nThis is appended content"
        response = client.post('/api/notes/append',
                              data=json.dumps({'text': append_text}),
                              content_type='application/json')
        print(f"Status: {response.status_code}")
        data = response.get_json()
        print(f"Response: {data}")
        
        # Test GET notes final
        print("\n5. Testing GET /api/notes (final)")
        response = client.get('/api/notes')
        print(f"Status: {response.status_code}")
        data = response.get_json()
        print(f"Response: {data}")
        if data.get('success'):
            print(f"Final notes length: {len(data.get('notes', ''))}")

if __name__ == "__main__":
    test_notes_api()