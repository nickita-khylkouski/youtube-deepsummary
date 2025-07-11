'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Clock, User, Calendar, MessageSquare, Sparkles, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface TranscriptEntry {
  time: number;
  text: string;
  formatted_time: string;
}

interface Chapter {
  time: number;
  title: string;
  formatted_time: string;
}

interface VideoInfo {
  title: string;
  uploader: string;
  duration: string;
  chapters: Chapter[];
}

interface TranscriptData {
  video_id: string;
  video_title: string;
  video_uploader: string;
  video_duration: string;
  transcript: TranscriptEntry[];
  formatted_transcript: string;
  chapters: Chapter[];
  thumbnail_url: string;
  proxy_used: string;
}

export default function Watch() {
  const searchParams = useSearchParams();
  const videoId = searchParams.get('v');
  
  const [transcriptData, setTranscriptData] = useState<TranscriptData | null>(null);
  const [summary, setSummary] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [summaryError, setSummaryError] = useState<string>('');

  useEffect(() => {
    if (!videoId) {
      setError('No video ID provided');
      setLoading(false);
      return;
    }

    fetchTranscript();
  }, [videoId]);

  const fetchTranscript = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await fetch(`/api/transcript/${videoId}`);
      const data = await response.json();
      
      if (data.success) {
        setTranscriptData(data);
        // Check if summary exists
        checkExistingSummary();
      } else {
        setError(data.error || 'Failed to fetch transcript');
      }
    } catch (err) {
      setError('Failed to fetch transcript: ' + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const checkExistingSummary = async () => {
    try {
      const response = await fetch(`/api/summary/${videoId}`);
      const data = await response.json();
      
      if (data.success) {
        setSummary(data.summary);
      }
    } catch (err) {
      // Summary doesn't exist yet, which is fine
    }
  };

  const generateSummary = async () => {
    if (!transcriptData) return;
    
    try {
      setSummaryLoading(true);
      setSummaryError('');
      
      const response = await fetch('/api/summary', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_id: videoId,
          formatted_transcript: transcriptData.formatted_transcript,
        }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSummary(data.summary);
      } else {
        setSummaryError(data.error || 'Failed to generate summary');
      }
    } catch (err) {
      setSummaryError('Failed to generate summary: ' + (err as Error).message);
    } finally {
      setSummaryLoading(false);
    }
  };

  const jumpToTime = (time: number) => {
    const iframe = document.querySelector('iframe');
    if (iframe) {
      iframe.src = `https://www.youtube.com/embed/${videoId}?start=${Math.floor(time)}`;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading transcript...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-8">
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg">
            <strong className="font-bold">Error: </strong>
            <span className="block sm:inline">{error}</span>
          </div>
        </div>
      </div>
    );
  }

  if (!transcriptData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">No transcript data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Video Header */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
          <div className="flex flex-col lg:flex-row gap-8">
            {/* Video Thumbnail */}
            <div className="flex-shrink-0">
              <img 
                src={transcriptData.thumbnail_url} 
                alt={transcriptData.video_title}
                className="w-full lg:w-96 h-auto rounded-xl shadow-lg"
              />
            </div>
            
            {/* Video Info */}
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-gray-900 mb-4">
                {transcriptData.video_title}
              </h1>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div className="flex items-center gap-2 text-gray-600">
                  <User className="h-5 w-5" />
                  <span>{transcriptData.video_uploader}</span>
                </div>
                
                <div className="flex items-center gap-2 text-gray-600">
                  <Clock className="h-5 w-5" />
                  <span>{transcriptData.video_duration}</span>
                </div>
                
                <div className="flex items-center gap-2 text-gray-600">
                  <MessageSquare className="h-5 w-5" />
                  <span>{transcriptData.transcript.length} transcript entries</span>
                </div>
                
                <div className="flex items-center gap-2 text-gray-600">
                  <Calendar className="h-5 w-5" />
                  <span>Video ID: {transcriptData.video_id}</span>
                </div>
              </div>
              
              {/* Summary Section */}
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-6 border border-blue-200">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-purple-600" />
                    AI Summary
                  </h2>
                  
                  {!summary && (
                    <button
                      onClick={generateSummary}
                      disabled={summaryLoading}
                      className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                      {summaryLoading ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-4 w-4" />
                          Generate Summary
                        </>
                      )}
                    </button>
                  )}
                </div>
                
                {summary && (
                  <div className="prose prose-sm max-w-none bg-white rounded-lg p-4 border border-gray-200">
                    <ReactMarkdown>{summary}</ReactMarkdown>
                  </div>
                )}
                
                {summaryError && (
                  <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                    {summaryError}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Chapters Section */}
        {transcriptData.chapters && transcriptData.chapters.length > 0 && (
          <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">📚 Chapters</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {transcriptData.chapters.map((chapter, index) => (
                <div
                  key={index}
                  className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4 border border-blue-200 hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => jumpToTime(chapter.time)}
                >
                  <div className="flex items-center gap-3">
                    <div className="bg-blue-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold">
                      {index + 1}
                    </div>
                    <div>
                      <div className="font-semibold text-gray-900">{chapter.title}</div>
                      <div className="text-sm text-gray-600">{chapter.formatted_time}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Transcript Section */}
        <div className="bg-white rounded-2xl shadow-lg p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">📝 Transcript</h2>
          
          <div className="space-y-4 max-h-96 overflow-y-auto">
            {transcriptData.transcript.map((entry, index) => (
              <div
                key={index}
                className="flex gap-4 p-4 hover:bg-gray-50 rounded-lg transition-colors cursor-pointer"
                onClick={() => jumpToTime(entry.time)}
              >
                <div className="flex-shrink-0">
                  <span className="text-sm font-mono text-blue-600 bg-blue-50 px-2 py-1 rounded">
                    {entry.formatted_time}
                  </span>
                </div>
                <div className="flex-1">
                  <p className="text-gray-700 leading-relaxed">{entry.text}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Embedded Video */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mt-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">🎥 Watch Video</h2>
          <div className="aspect-video">
            <iframe
              src={`https://www.youtube.com/embed/${transcriptData.video_id}`}
              title={transcriptData.video_title}
              className="w-full h-full rounded-lg"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
        </div>
      </div>
    </div>
  );
}