# YouTube Transcript Web Viewer

A Flask web application that displays YouTube video transcripts with proxy support.

## Features

- **Web Interface**: Clean, responsive UI for viewing transcripts
- **Multiple Input Formats**: Accepts video IDs, full URLs, or short URLs
- **Proxy Support**: Uses environment variable for proxy configuration
- **API Endpoint**: JSON API for programmatic access
- **Error Handling**: Graceful error handling with helpful messages

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set proxy environment variable:
```bash
export YOUTUBE_PROXY=200.174.198.86:8888
```

3. Start the server:
```bash
python3 app.py
# OR
./start_server.sh
```

## Usage

### Web Interface

- **Home**: `http://localhost:5000/`
- **Transcript**: `http://localhost:5000/watch?v=VIDEO_ID`

### API Endpoint

- **JSON Response**: `http://localhost:5000/api/transcript/VIDEO_ID`

### Examples

```bash
# Web interface
http://localhost:5000/watch?v=FjHtZnjNEBU

# API endpoint
curl http://localhost:5000/api/transcript/FjHtZnjNEBU
```

### Supported Input Formats

- Video ID: `FjHtZnjNEBU`
- Full URL: `https://www.youtube.com/watch?v=FjHtZnjNEBU`
- Short URL: `https://youtu.be/FjHtZnjNEBU`

## Environment Variables

- `YOUTUBE_PROXY`: Proxy server in format `ip:port` (e.g., `200.174.198.86:8888`)

## Files

- `app.py`: Main Flask application
- `templates/`: HTML templates
- `start_server.sh`: Server startup script
- `requirements.txt`: Python dependencies