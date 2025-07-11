import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Proxy to Python backend
    const backendUrl = process.env.PYTHON_BACKEND_URL || 'http://localhost:5000';
    const response = await fetch(`${backendUrl}/channels`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`);
    }
    
    const html = await response.text();
    
    // For simplicity, we'll return a structured response
    // In a real implementation, you might want to parse the HTML or create a dedicated API endpoint
    return NextResponse.json({
      success: true,
      channels: [],
    });
  } catch (error) {
    console.error('Error fetching channels:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: error instanceof Error ? error.message : 'Failed to fetch channels' 
      },
      { status: 500 }
    );
  }
}