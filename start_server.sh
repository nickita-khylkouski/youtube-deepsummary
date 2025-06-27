#!/bin/bash
# YouTube Transcript Web Server Startup Script

export YOUTUBE_PROXY=200.174.198.86:8888
echo "Starting YouTube Transcript Web Server..."
echo "Server will be available at: http://localhost:5000"
echo "Using proxy: $YOUTUBE_PROXY"
echo ""
echo "Example URLs:"
echo "  http://localhost:5000/"
echo "  http://localhost:5000/watch?v=FjHtZnjNEBU"
echo "  http://localhost:5000/api/transcript/FjHtZnjNEBU"
echo ""
python3 app.py