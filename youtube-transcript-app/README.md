# YouTube Transcript Viewer - Next.js App

A modern Next.js application that transforms YouTube videos into actionable insights through AI-powered transcript analysis.

## Features

- **Beautiful Modern UI**: Clean, responsive design with Tailwind CSS
- **YouTube Video Processing**: Extract transcripts from any YouTube video
- **AI-Powered Summaries**: Generate comprehensive summaries using OpenAI
- **Chapter Navigation**: Visual chapter markers for easy video navigation
- **Video Storage**: Cache and manage processed videos
- **Channel Analytics**: Track and analyze content across YouTube channels
- **Mobile Responsive**: Works perfectly on all devices

## Tech Stack

- **Frontend**: Next.js 15, React 19, TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **Backend**: Python Flask (proxy through Next.js API routes)
- **AI**: OpenAI GPT for summaries
- **Database**: SQLite (via Python backend)

## Getting Started

### Prerequisites

1. **Node.js**: Version 18 or higher
2. **Python**: Version 3.8 or higher
3. **OpenAI API Key**: For AI summaries (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd youtube-transcript-app
   ```

2. **Install Node.js dependencies**
   ```bash
   npm install
   ```

3. **Set up Python backend**
   ```bash
   npm run setup
   ```

4. **Configure environment variables**
   Create a `.env.local` file in the root directory:
   ```env
   PYTHON_BACKEND_URL=http://localhost:5000
   NEXT_PUBLIC_APP_URL=http://localhost:3000
   ```

5. **Set up Python backend environment**
   In the parent directory, create a `.env` file:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   YOUTUBE_PROXY=your_proxy_if_needed
   ```

### Running the Application

#### Development Mode (Both Frontend and Backend)
```bash
npm run dev:full
```

This will start:
- Python Flask backend on `http://localhost:5000`
- Next.js frontend on `http://localhost:3000`

#### Frontend Only
```bash
npm run dev
```

#### Backend Only
```bash
npm run backend
```

### Building for Production

```bash
npm run build
npm run start
```

## Project Structure

```
youtube-transcript-app/
├── src/
│   ├── app/
│   │   ├── api/                 # Next.js API routes (proxy to Python)
│   │   │   ├── transcript/      # Video transcript endpoints
│   │   │   ├── summary/         # AI summary endpoints
│   │   │   ├── storage/         # Storage management
│   │   │   └── channels/        # Channel analytics
│   │   ├── watch/              # Video transcript viewer
│   │   ├── storage/            # Storage management page
│   │   ├── channels/           # Channel analytics page
│   │   ├── layout.tsx          # Root layout with navigation
│   │   └── page.tsx            # Home page
│   └── components/             # Reusable React components
├── public/                     # Static assets
├── .env.local                  # Environment variables
├── package.json               # Dependencies and scripts
└── README.md                  # This file
```

## API Endpoints

### Frontend API Routes (Next.js)
- `GET /api/transcript/[videoId]` - Get video transcript
- `GET /api/summary/[videoId]` - Get existing summary
- `POST /api/summary` - Generate new summary
- `GET /api/storage` - Get cached videos
- `GET /api/channels` - Get channel analytics
- `DELETE /api/delete/[videoId]` - Delete cached video

### Backend API Routes (Python Flask)
The Next.js API routes proxy to the Python Flask backend running on port 5000.

## Usage

1. **Process a Video**
   - Enter a YouTube URL or video ID on the home page
   - Click "Extract Impact" to process the video
   - View the transcript, chapters, and generate AI summaries

2. **Manage Storage**
   - Navigate to `/storage` to view cached videos
   - Delete videos or view processing statistics

3. **Analyze Channels**
   - Navigate to `/channels` to see channel analytics
   - View all videos from specific channels
   - Track summary generation progress

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PYTHON_BACKEND_URL` | URL of the Python Flask backend | `http://localhost:5000` |
| `NEXT_PUBLIC_APP_URL` | Public URL of the Next.js app | `http://localhost:3000` |

## Development

### Adding New Features

1. **Frontend Components**: Add to `src/components/`
2. **Pages**: Add to `src/app/` following Next.js App Router structure
3. **API Routes**: Add to `src/app/api/` and ensure they proxy to Python backend
4. **Styling**: Use Tailwind CSS classes

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Troubleshooting

### Common Issues

1. **Python backend not starting**
   - Ensure Python dependencies are installed: `pip install -r requirements.txt`
   - Check if port 5000 is available

2. **Frontend API calls failing**
   - Verify `PYTHON_BACKEND_URL` in `.env.local`
   - Ensure Python backend is running

3. **Build errors**
   - Clear `.next` directory: `rm -rf .next`
   - Reinstall dependencies: `npm install`

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments

- YouTube Transcript API for video transcript extraction
- OpenAI for AI-powered summaries
- Next.js team for the excellent framework
- Tailwind CSS for the utility-first CSS framework
