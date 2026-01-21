import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // 1. ON FORCE L'URL NGROK VIA VARIABLE D'ENVIRONNEMENT
    const baseUrl = process.env.NGROK_URL;
    if (!baseUrl) {
      return NextResponse.json(
        { error: 'Configuration Error: NGROK_URL not set' },
        { status: 500 }
      );
    }

    const url = `${baseUrl}/hardware-proxy`;

    // 2. On appelle le Python via le tunnel avec le Sésame
    const res = await fetch(url, {
      cache: 'no-store',
      headers: {
        'ngrok-skip-browser-warning': 'true',
      },
    });

    if (!res.ok) {
      return NextResponse.json(
        { error: `Erreur distante: ${res.status}` },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Hardware Proxy Error:', error);
    return NextResponse.json(
      { error: 'Internal Server Error', details: String(error) },
      { status: 500 }
    );
  }
}
