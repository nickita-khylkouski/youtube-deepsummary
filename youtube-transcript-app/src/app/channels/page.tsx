'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Users, Video, Eye, Sparkles } from 'lucide-react';

interface Channel {
  channel_name: string;
  video_count: number;
  latest_video_date: string;
  videos_with_summaries: number;
}

export default function Channels() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    fetchChannels();
  }, []);

  const fetchChannels = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await fetch('/api/channels');
      const data = await response.json();
      
      if (data.success) {
        setChannels(data.channels || []);
      } else {
        setError(data.error || 'Failed to fetch channels');
      }
    } catch (err) {
      setError('Failed to fetch channels: ' + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
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
            <p className="text-gray-600">Loading channels...</p>
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
          <Users className="h-8 w-8 text-blue-600" />
          Channels
        </h1>
        <p className="text-gray-600">
          Browse YouTube channels with processed videos
        </p>
      </div>

      {/* Channel Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Channels</p>
              <p className="text-2xl font-bold text-blue-600">{channels.length}</p>
            </div>
            <Users className="h-8 w-8 text-blue-600" />
          </div>
        </div>
        
        <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Videos</p>
              <p className="text-2xl font-bold text-green-600">
                {channels.reduce((sum, channel) => sum + channel.video_count, 0)}
              </p>
            </div>
            <Video className="h-8 w-8 text-green-600" />
          </div>
        </div>
        
        <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">With Summaries</p>
              <p className="text-2xl font-bold text-purple-600">
                {channels.reduce((sum, channel) => sum + channel.videos_with_summaries, 0)}
              </p>
            </div>
            <Sparkles className="h-8 w-8 text-purple-600" />
          </div>
        </div>
      </div>

      {/* Channels List */}
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">All Channels</h2>
        </div>
        
        {channels.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <Users className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <p>No channels found.</p>
            <p className="text-sm">Process some videos to see channels here!</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {channels.map((channel) => (
              <div key={channel.channel_name} className="p-6 hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      {channel.channel_name}
                    </h3>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-600 mb-4">
                      <div className="flex items-center gap-2">
                        <Video className="h-4 w-4" />
                        <span>{channel.video_count} videos</span>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <Sparkles className="h-4 w-4" />
                        <span>{channel.videos_with_summaries} with summaries</span>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <span className="text-gray-500">Latest:</span>
                        <span>{formatDate(channel.latest_video_date)}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex gap-2 ml-4">
                    <Link
                      href={`/channels/${encodeURIComponent(channel.channel_name)}/videos`}
                      className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      <Eye className="h-4 w-4" />
                      View Videos
                    </Link>
                    
                    <Link
                      href={`/channels/${encodeURIComponent(channel.channel_name)}/summaries`}
                      className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                    >
                      <Sparkles className="h-4 w-4" />
                      View Summaries
                    </Link>
                  </div>
                </div>
                
                {/* Progress Bar */}
                <div className="mt-4">
                  <div className="flex justify-between text-sm text-gray-600 mb-1">
                    <span>Summary Progress</span>
                    <span>{Math.round((channel.videos_with_summaries / channel.video_count) * 100)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                      style={{ 
                        width: `${(channel.videos_with_summaries / channel.video_count) * 100}%` 
                      }}
                    />
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