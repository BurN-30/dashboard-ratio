import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Use env var if provided, otherwise fall back to the public O2Switch path
    const base = process.env.JSON_BASE_URL || 'https://example.com/dash';
    console.log('[/api/stats] Base URL:', base);

    const url = `${base.replace(/\/$/, '')}/stats.json`;
    console.log('[/api/stats] Fetching from:', url);

    // Optional headers for protected endpoints (Basic Auth via .htaccess) and origin hint
    const origin = process.env.JSON_ORIGIN || 'https://dash.example.com';
    const basic = process.env.JSON_AUTH_BASIC; // format: user:password
    const headers: Record<string, string> = {
      Origin: origin,
      'User-Agent': 'DashboardFetcher/1.0',
    };
    if (basic) {
      try {
        const token = Buffer.from(basic).toString('base64');
        headers['Authorization'] = `Basic ${token}`;
        console.log('[/api/stats] Using Basic auth');
      } catch (e) {
        console.warn('[/api/stats] Failed to construct Basic auth header');
      }
    }

    const res = await fetch(url, { cache: 'no-store', headers });
    console.log('[/api/stats] Response status:', res.status);

    if (!res.ok) {
      const text = await res.text();
      console.error('[/api/stats] Failed response:', res.status, text.slice(0, 200));
      return NextResponse.json({ error: 'Failed to fetch data from source', url, status: res.status }, { status: res.status });
    }

    const data = await res.json();
    console.log('[/api/stats] Success, got data');
    return NextResponse.json(data);
  } catch (error) {
    console.error('[/api/stats] Proxy fetch error:', error);
    return NextResponse.json({ error: 'Internal Server Error', details: String(error) }, { status: 500 });
  }
}
