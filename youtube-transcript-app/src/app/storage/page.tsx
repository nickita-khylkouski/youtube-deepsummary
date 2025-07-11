'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Database, Clock, User, Calendar, Trash2, Eye, Sparkles } from 'lucide-react';

interface CachedVideo {
  video_id: string;
  title: string;
  uploader: string;
  duration: string;
  created_at: string;
  has_summary: boolean;
  thumbnail_url: string;
}

interface CacheStats {
  total_videos: number;
  total_size: string;
  videos_with_summaries: number;
}

export default function Storage() {
  const [cachedVideos, setCachedVideos] = useState<CachedVideo[]>([]);
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    fetchStorageData();
  }, []);

  const fetchStorageData = async () => {
    try {
      setLoading(true);
      setError('');
      
      // Fetch cached videos and stats from backend
      const response = await fetch('/api/storage');
      const data = await response.json();
      
      if (data.success) {
        setCachedVideos(data.cached_videos || []);
        setCacheStats(data.cache_stats || null);
      } else {
        setError(data.error || 'Failed to fetch storage data');
      }
    } catch (err) {
      setError('Failed to fetch storage data: ' + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const deleteVideo = async (videoId: string) => {
    try {
      const response = await fetch(`/api/delete/${videoId}`, {
        method: 'DELETE',
      });
      
      const data = await response.json();
      
      if (data.success) {
        // Remove video from list
        setCachedVideos(prev => prev.filter(v => v.video_id !== videoId));
        // Update cache stats
        if (cacheStats) {
          setCacheStats(prev => prev ? {
            ...prev,
            total_videos: prev.total_videos - 1
          } : null);
        }
      } else {
        alert('Failed to delete video: ' + data.message);
      }
    } catch (err) {
      alert('Failed to delete video: ' + (err as Error).message);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateString;
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center min-h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading storage data...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg">
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-3">
          <Database className="h-8 w-8 text-blue-600" />
          Storage
        </h1>
        <p className="text-gray-600">
          Manage your cached videos and storage statistics
        </p>
      </div>

      {/* Cache Statistics */}
      {cacheStats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Videos</p>
                <p className="text-2xl font-bold text-blue-600">{cacheStats.total_videos}</p>
              </div>
              <Database className="h-8 w-8 text-blue-600" />
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">With Summaries</p>
                <p className="text-2xl font-bold text-green-600">{cacheStats.videos_with_summaries}</p>
              </div>
              <Sparkles className="h-8 w-8 text-green-600" />
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Storage Used</p>
                <p className="text-2xl font-bold text-purple-600">{cacheStats.total_size}</p>
              </div>
              <Database className="h-8 w-8 text-purple-600" />
            </div>
          </div>
        </div>
      )}

      {/* Cached Videos */}
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Cached Videos</h2>
        </div>
        
        {cachedVideos.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <Database className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <p>No cached videos found.</p>
            <p className="text-sm">Process some videos to see them here!</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {cachedVideos.map((video) => (
              <div key={video.video_id} className="p-6 hover:bg-gray-50 transition-colors">
                <div className="flex items-start gap-4">
                  <img
                    src={video.thumbnail_url}
                    alt={video.title}
                    className="w-32 h-18 object-cover rounded-lg shadow-md flex-shrink-0"
                  />
                  
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">
                      {video.title}
                    </h3>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm text-gray-600 mb-4">
                      <div className="flex items-center gap-2">
                        <User className="h-4 w-4" />
                        <span>{video.uploader}</span>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4" />
                        <span>{video.duration}</span>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4" />
                        <span>{formatDate(video.created_at)}</span>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <Sparkles className="h-4 w-4" />
                        <span>{video.has_summary ? 'Has Summary' : 'No Summary'}</span>
                      </div>
                    </div>
                    
                    <div className="flex gap-2">
                      <Link
                        href={`/watch?v=${video.video_id}`}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        <Eye className="h-4 w-4" />
                        View
                      </Link>
                      
                      <button
                        onClick={() => deleteVideo(video.video_id)}
                        className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                      >
                        <Trash2 className="h-4 w-4" />
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}