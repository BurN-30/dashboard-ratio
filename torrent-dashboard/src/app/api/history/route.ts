import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const res = await fetch('https://dash.example.com/history.json', {
      cache: 'no-store',
    });
    
    if (!res.ok) {
      // If history doesn't exist yet, return empty array
      if (res.status === 404) {
        return NextResponse.json([]);
      }
      return NextResponse.json({ error: 'Failed to fetch history' }, { status: res.status });
    }
    
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Proxy fetch error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
