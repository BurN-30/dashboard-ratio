import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Use env var if provided, otherwise fall back to the public O2Switch path
    const base = process.env.JSON_BASE_URL || 'https://example.com/dash';
    console.log('[/api/history] Base URL:', base);

    const url = `${base.replace(/\/$/, '')}/history.json`;
    console.log('[/api/history] Fetching from:', url);

    const res = await fetch(url, { cache: 'no-store' });
    console.log('[/api/history] Response status:', res.status);

    if (!res.ok) {
      // If history doesn't exist yet, return empty array
      if (res.status === 404) {
        console.log('[/api/history] Not found (404), returning empty array');
        return NextResponse.json([]);
      }
      const text = await res.text();
      console.error('[/api/history] Failed response:', res.status, text.slice(0, 200));
      return NextResponse.json({ error: 'Failed to fetch history', url, status: res.status }, { status: res.status });
    }

    const data = await res.json();
    console.log('[/api/history] Success, got data');
    return NextResponse.json(data);
  } catch (error) {
    console.error('[/api/history] Proxy fetch error:', error);
    return NextResponse.json({ error: 'Internal Server Error', details: String(error) }, { status: 500 });
  }
}
