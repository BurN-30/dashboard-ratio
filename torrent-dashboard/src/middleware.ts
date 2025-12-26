import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;

  // Chemins publics
  const isPublicPath = path === "/login" || path === "/api/login";
  
  // Ignorer les ressources statiques
  if (
    path.startsWith("/_next") ||
    path.startsWith("/images") ||
    path.startsWith("/favicon.ico") ||
    path.match(/\.(png|jpg|jpeg|gif|svg|ico|css|js|json)$/)
  ) {
    return NextResponse.next();
  }

  const token = request.cookies.get("auth_token")?.value;

  // Protection
  if (!isPublicPath && !token) {
    // Si c'est une route API, renvoyer 401 au lieu de rediriger
    if (path.startsWith("/api/")) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    // Sinon rediriger vers login
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Redirection si déjà connecté
  if (path === "/login" && token) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
