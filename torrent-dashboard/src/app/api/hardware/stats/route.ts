import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Use env var if provided, otherwise fall back to the public O2Switch path
    const base = process.env.JSON_BASE_URL || 'https://example.com/dash';
    const url = `${base.replace(/\/$/, '')}/hardware.json`;

    const res = await fetch(url, { cache: 'no-store' });

    if (!res.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch hardware data', url, status: res.status }, 
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[/api/hardware/stats] Fetch error:', error);
    return NextResponse.json(
      { error: 'Internal Server Error', details: String(error) }, 
      { status: 500 }
    );
  }
}
