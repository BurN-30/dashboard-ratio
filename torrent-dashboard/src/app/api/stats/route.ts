import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const base = process.env.JSON_BASE_URL;
    if (!base) {
      return NextResponse.json({ error: 'Missing JSON_BASE_URL' }, { status: 500 });
    }

    const url = `${base.replace(/\/$/, '')}/stats.json`;
    const res = await fetch(url, { cache: 'no-store' });

    if (!res.ok) {
      return NextResponse.json({ error: 'Failed to fetch data from source', url }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Proxy fetch error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
