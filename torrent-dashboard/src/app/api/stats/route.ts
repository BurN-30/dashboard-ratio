import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const res = await fetch('https://dash.example.com/stats.json', {
      cache: 'no-store',
    });
    
    if (!res.ok) {
      return NextResponse.json({ error: 'Failed to fetch data from source' }, { status: res.status });
    }
    
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Proxy fetch error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
