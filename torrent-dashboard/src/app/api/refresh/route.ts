import { NextResponse } from 'next/server';

export async function POST() {
  try {
    const triggerUrl = process.env.SCRAPER_TRIGGER_URL; 
    const token = process.env.SCRAPER_TRIGGER_TOKEN;

    if (!triggerUrl || !token) {
      console.error("Configuration manquante : SCRAPER_TRIGGER_URL ou TOKEN");
      return NextResponse.json({ error: 'Erreur de configuration serveur' }, { status: 500 });
    }

    // Appel au serveur Python
    const res = await fetch(triggerUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-token': token,
      },
    });

    const data = await res.json();

    // Si le serveur Python rejette la requête (Token invalide, ou autre erreur 500)
    if (!res.ok) {
      return NextResponse.json({ 
        error: 'Erreur du serveur distant', 
        details: data.message || data.detail || 'Erreur inconnue' 
      }, { status: res.status });
    }

    // Si le scraper est "busy", on renvoie quand même un succès HTTP 200 au frontend,
    // mais avec le message "Occupé" pour l'afficher à l'utilisateur.
    return NextResponse.json(data);

  } catch (error) {
    console.error('Refresh API error:', error);
    return NextResponse.json({ 
      error: 'Le serveur de script est inaccessible.', 
      details: 'Vérifiez que votre PC est allumé et que le tunnel (Ngrok/Cloudflare) est actif.' 
    }, { status: 502 });
  }
}