'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Play, Clock, Users, TrendingUp } from 'lucide-react';

export default function Home() {
  const [videoInput, setVideoInput] = useState('');
  const router = useRouter();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const videoId = videoInput.trim() || 'FjHtZnjNEBU';
    router.push(`/watch?v=${videoId}`);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <div className="relative overflow-hidden bg-gradient-to-br from-blue-600 via-purple-600 to-purple-700 text-white">
        <div className="absolute inset-0 bg-black/10"></div>
        <div className="relative z-10 px-4 py-16 sm:px-6 sm:py-20 lg:px-8">
          <div className="mx-auto max-w-4xl text-center">
            <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
              Transform Hours of Video<br />
              Into <span className="bg-gradient-to-r from-yellow-400 to-orange-400 bg-clip-text text-transparent">Actionable Insights</span>
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-100 max-w-2xl mx-auto">
              Stop wasting time on lengthy videos. Extract the key information that will actually move your projects forward, enhance your skills, and create real value in your work and life.
            </p>
            
            {/* Search Form */}
            <div className="mt-10 max-w-2xl mx-auto">
              <form onSubmit={handleSubmit} className="bg-white/95 backdrop-blur-sm rounded-2xl p-6 shadow-xl">
                <div className="flex gap-4">
                  <input
                    type="text"
                    value={videoInput}
                    onChange={(e) => setVideoInput(e.target.value)}
                    placeholder="Paste YouTube URL or video ID..."
                    className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-xl text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  />
                  <button
                    type="submit"
                    className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-red-500 to-pink-500 text-white font-semibold rounded-xl hover:from-red-600 hover:to-pink-600 transition-all shadow-lg hover:shadow-xl"
                  >
                    <Play size={20} />
                    Extract Impact
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Section */}
      <div className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
            <div className="text-center rounded-2xl bg-gradient-to-br from-blue-50 to-blue-100 p-6 border border-blue-200">
              <div className="flex items-center justify-center">
                <Users className="h-8 w-8 text-blue-600 mb-2" />
              </div>
              <div className="text-3xl font-bold text-blue-600">10,000+</div>
              <div className="text-gray-600 font-medium">Professionals Empowered</div>
            </div>
            <div className="text-center rounded-2xl bg-gradient-to-br from-green-50 to-green-100 p-6 border border-green-200">
              <div className="flex items-center justify-center">
                <Clock className="h-8 w-8 text-green-600 mb-2" />
              </div>
              <div className="text-3xl font-bold text-green-600">500+</div>
              <div className="text-gray-600 font-medium">Hours Saved Daily</div>
            </div>
            <div className="text-center rounded-2xl bg-gradient-to-br from-orange-50 to-orange-100 p-6 border border-orange-200">
              <div className="flex items-center justify-center">
                <TrendingUp className="h-8 w-8 text-orange-600 mb-2" />
              </div>
              <div className="text-3xl font-bold text-orange-600">95%</div>
              <div className="text-gray-600 font-medium">Time Reduction</div>
            </div>
          </div>
        </div>
      </div>

      {/* Testimonials Section */}
      <div className="py-16 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-gray-50 to-gray-100">
        <div className="mx-auto max-w-7xl">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              💬 Real Impact Stories
            </h2>
          </div>
          
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-2 xl:grid-cols-3">
            {/* Testimonial 1 */}
            <div className="relative bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-200">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-purple-600 rounded-t-2xl"></div>
              <p className="text-gray-700 mb-6 leading-relaxed">
                "This tool helped me finish my thesis 3 months early. Instead of watching 40+ hours of lecture videos, I extracted the exact research insights I needed. The AI summaries identified patterns across different talks that became the foundation of my research."
              </p>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold">
                  SC
                </div>
                <div>
                  <div className="font-semibold text-gray-900">Sarah Chen</div>
                  <div className="text-sm text-gray-500">PhD Student, Stanford</div>
                </div>
              </div>
            </div>

            {/* Testimonial 2 */}
            <div className="relative bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-200">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-pink-500 to-red-500 rounded-t-2xl"></div>
              <p className="text-gray-700 mb-6 leading-relaxed">
                "I launched a $2M product feature after extracting insights from 50+ competitor analysis videos. What used to take weeks of research now takes hours. The structured summaries revealed market gaps that became our competitive advantage."
              </p>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-gradient-to-br from-pink-500 to-red-500 rounded-full flex items-center justify-center text-white font-bold">
                  MR
                </div>
                <div>
                  <div className="font-semibold text-gray-900">Marcus Rodriguez</div>
                  <div className="text-sm text-gray-500">Product Manager</div>
                </div>
              </div>
            </div>

            {/* Testimonial 3 */}
            <div className="relative bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-200">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-t-2xl"></div>
              <p className="text-gray-700 mb-6 leading-relaxed">
                "My YouTube channel grew from 5K to 100K subscribers in 6 months. I analyzed top performers in my niche, extracted their successful frameworks, and adapted them to my content. The insights turned my hobby into a full-time business."
              </p>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-gradient-to-br from-cyan-500 to-blue-500 rounded-full flex items-center justify-center text-white font-bold">
                  AT
                </div>
                <div>
                  <div className="font-semibold text-gray-900">Alex Thompson</div>
                  <div className="text-sm text-gray-500">Content Creator</div>
                </div>
              </div>
            </div>

            {/* Testimonial 4 */}
            <div className="relative bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-200">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-orange-500 to-yellow-500 rounded-t-2xl"></div>
              <p className="text-gray-700 mb-6 leading-relaxed">
                "I got promoted to senior engineer after implementing techniques from 100+ coding tutorials. Instead of watching everything, I extracted the core concepts and built a personal knowledge base."
              </p>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-gradient-to-br from-orange-500 to-yellow-500 rounded-full flex items-center justify-center text-white font-bold">
                  JL
                </div>
                <div>
                  <div className="font-semibold text-gray-900">Jordan Lee</div>
                  <div className="text-sm text-gray-500">Software Engineer</div>
                </div>
              </div>
            </div>

            {/* Testimonial 5 */}
            <div className="relative bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-200">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-green-500 to-teal-500 rounded-t-2xl"></div>
              <p className="text-gray-700 mb-6 leading-relaxed">
                "I broke three major stories by analyzing hours of interview footage in minutes. The transcript search helped me find contradictory statements and smoking gun quotes that others missed."
              </p>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-teal-500 rounded-full flex items-center justify-center text-white font-bold">
                  EP
                </div>
                <div>
                  <div className="font-semibold text-gray-900">Emma Parker</div>
                  <div className="text-sm text-gray-500">Investigative Journalist</div>
                </div>
              </div>
            </div>

            {/* Testimonial 6 */}
            <div className="relative bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-200">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 to-pink-500 rounded-t-2xl"></div>
              <p className="text-gray-700 mb-6 leading-relaxed">
                "Our startup pivoted based on insights from 200+ customer interview videos. The AI summaries revealed pain points we'd completely missed. That pivot led to $5M in funding and product-market fit."
              </p>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center text-white font-bold">
                  RK
                </div>
                <div>
                  <div className="font-semibold text-gray-900">Raj Kumar</div>
                  <div className="text-sm text-gray-500">Market Researcher</div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-12 text-center text-gray-600 text-lg font-medium border-t pt-8">
            ✨ Join 10,000+ professionals who turn video content into career-changing insights
          </div>
        </div>
      </div>

      {/* How to Use Section */}
      <div className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <details className="group bg-white rounded-2xl border-2 border-gray-200 shadow-lg overflow-hidden">
            <summary className="cursor-pointer bg-gradient-to-r from-blue-600 to-purple-600 text-white p-6 font-semibold text-xl hover:from-blue-700 hover:to-purple-700 transition-all">
              🎯 Turn any video into actionable insights in 3 steps
            </summary>
            <div className="p-8 bg-white">
              <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
                <div className="bg-gradient-to-br from-blue-500 to-purple-600 text-white p-8 rounded-2xl shadow-lg">
                  <h3 className="text-xl font-semibold mb-4">🚀 Extract Impact</h3>
                  <ol className="space-y-3 text-gray-100">
                    <li>1. Paste any YouTube URL or video ID above</li>
                    <li>2. Click "Extract Impact" to get structured content</li>
                    <li>3. Generate AI summary to identify key takeaways</li>
                    <li>4. Apply insights to your current projects immediately</li>
                  </ol>
                </div>
                
                <div className="bg-gradient-to-br from-cyan-500 to-blue-500 text-white p-8 rounded-2xl shadow-lg">
                  <h3 className="text-xl font-semibold mb-4">💼 Use Cases</h3>
                  <ul className="space-y-3 text-gray-100">
                    <li>• Research competitive strategies from industry talks</li>
                    <li>• Extract learning frameworks from educational content</li>
                    <li>• Analyze customer feedback from video interviews</li>
                    <li>• Build knowledge base from conference presentations</li>
                  </ul>
                </div>
                
                <div className="bg-gradient-to-br from-pink-500 to-red-500 text-white p-8 rounded-2xl shadow-lg">
                  <h3 className="text-xl font-semibold mb-4">📊 Maximize Impact</h3>
                  <ul className="space-y-3 text-gray-100">
                    <li>• Focus on actionable insights, not just information</li>
                    <li>• Create implementation plans from extracted frameworks</li>
                    <li>• Track which insights drive measurable results</li>
                    <li>• Build a personal knowledge system for future reference</li>
                  </ul>
                </div>
              </div>
            </div>
          </details>
        </div>
      </div>
    </div>
  );
}
