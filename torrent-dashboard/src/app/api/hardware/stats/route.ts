import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // 1. ON FORCE L'URL NGROK (On ignore la variable d'env Vercel pour l'instant)
    // Remplace l'URL ci-dessous par ton URL Ngrok actuelle si elle a changé
    const url = 'https://submedial-bloodlike-sarah.ngrok-free.dev/hardware-proxy';

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
