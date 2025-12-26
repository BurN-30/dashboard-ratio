import { NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function POST(request: Request) {
  const body = await request.json();
  const { password, rememberMe } = body;

  // Récupérer le mot de passe depuis les variables d'environnement
  // Si non défini, utiliser "admin" par défaut (à changer !)
  const adminPassword = process.env.ADMIN_PASSWORD || "admin";

  console.log("Login attempt:", { 
    providedPassword: password, 
    envPasswordLength: adminPassword.length,
    match: password === adminPassword 
  });

  if (password === adminPassword) {
    // Créer la réponse
    const response = NextResponse.json({ success: true });

    // Définir le cookie directement sur la réponse pour plus de fiabilité
    response.cookies.set({
      name: "auth_token",
      value: "authenticated",
      httpOnly: true,
      path: "/",
      secure: false, // Toujours false pour le local/HTTP
      sameSite: "lax",
      expires: rememberMe ? Date.now() + 30 * 24 * 60 * 60 * 1000 : undefined,
    });

    return response;
  }

  return NextResponse.json(
    { error: "Invalid password" },
    { status: 401 }
  );
}
