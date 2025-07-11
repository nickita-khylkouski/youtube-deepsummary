import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import { Play, Database, Users, Home } from "lucide-react";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "YouTube Transcript Viewer",
  description: "Transform hours of video into actionable insights",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <nav className="bg-white shadow-lg border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center">
                <Link href="/" className="flex items-center space-x-2">
                  <Play className="h-8 w-8 text-blue-600" />
                  <span className="text-xl font-bold text-gray-900">
                    YouTube Transcript Viewer
                  </span>
                </Link>
              </div>
              
              <div className="flex items-center space-x-4">
                <Link
                  href="/"
                  className="flex items-center space-x-1 text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium transition-colors"
                >
                  <Home className="h-4 w-4" />
                  <span>Home</span>
                </Link>
                
                <Link
                  href="/storage"
                  className="flex items-center space-x-1 text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium transition-colors"
                >
                  <Database className="h-4 w-4" />
                  <span>Storage</span>
                </Link>
                
                <Link
                  href="/channels"
                  className="flex items-center space-x-1 text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium transition-colors"
                >
                  <Users className="h-4 w-4" />
                  <span>Channels</span>
                </Link>
              </div>
            </div>
          </div>
        </nav>
        
        <main className="min-h-screen bg-gray-50">
          {children}
        </main>
        
        <footer className="bg-gray-800 text-white py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              <p className="text-gray-400">
                © 2024 YouTube Transcript Viewer. Transform video content into actionable insights.
              </p>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
