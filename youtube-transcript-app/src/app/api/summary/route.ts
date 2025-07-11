import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { video_id, formatted_transcript } = body;
    
    if (!video_id || !formatted_transcript) {
      return NextResponse.json(
        { 
          success: false, 
          error: 'video_id and formatted_transcript are required' 
        },
        { status: 400 }
      );
    }
    
    // Proxy to Python backend
    const backendUrl = process.env.PYTHON_BACKEND_URL || 'http://localhost:5000';
    const response = await fetch(`${backendUrl}/api/summary`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        video_id,
        formatted_transcript,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`);
    }
    
    const data = await response.json();
    
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error generating summary:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: error instanceof Error ? error.message : 'Failed to generate summary' 
      },
      { status: 500 }
    );
  }
}