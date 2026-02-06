# Guide de Migration Frontend - Dashboard V2

## Étapes de Migration

### 1. Copier le code existant

```bash
# Depuis le répertoire dashboard-v2
cp -r ../torrent-dashboard/* frontend/
```

### 2. Remplacer les fichiers modifiés

Les fichiers suivants doivent être remplacés par les versions V2 :

- `src/lib/api.ts` - Nouveau client API avec JWT
- `src/hooks/useHardwareStats.ts` - Hook WebSocket
- `src/context/AuthContext.tsx` - Contexte d'auth JWT
- `src/components/RefreshButton.tsx` - Nouveau bouton refresh
- `src/types/tracker.ts` - Types (compatible)

### 3. Modifier le layout principal

Editer `src/app/layout.tsx` pour ajouter le AuthProvider :

```tsx
import { AuthProvider } from '@/context/AuthContext';

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <AuthProvider>
          {/* ... reste du code ... */}
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
```

### 4. Modifier la page de login

Editer `src/app/login/page.tsx` pour utiliser le nouveau contexte :

```tsx
"use client";
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e) => {
    e.preventDefault();
    const success = await login(password, rememberMe);
    if (success) {
      router.push('/');
    }
  };
  // ...
}
```

### 5. Supprimer les routes API proxy

Les fichiers suivants ne sont plus nécessaires (le frontend appelle directement le backend) :

- `src/app/api/stats/route.ts`
- `src/app/api/history/route.ts`
- `src/app/api/refresh/route.ts`
- `src/app/api/hardware/stats/route.ts`
- `src/middleware.ts` (l'auth est gérée par JWT côté client)

### 6. Configurer les variables d'environnement

Créer `.env.local` :

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Pour la production :

```
NEXT_PUBLIC_API_URL=https://api.votre-domaine.com
```

### 7. Modifier next.config.ts

Ajouter la configuration pour le build standalone :

```ts
const nextConfig = {
  output: 'standalone',
  // ... autres options
};
```

## Fichiers Modifiés - Résumé

| Fichier | Action | Description |
|---------|--------|-------------|
| `src/lib/api.ts` | REMPLACER | Client API avec JWT |
| `src/hooks/useHardwareStats.ts` | REMPLACER | WebSocket au lieu de polling |
| `src/context/AuthContext.tsx` | AJOUTER | Gestion auth JWT |
| `src/components/RefreshButton.tsx` | REMPLACER | Appel API direct |
| `src/app/layout.tsx` | MODIFIER | Ajouter AuthProvider |
| `src/app/login/page.tsx` | MODIFIER | Utiliser useAuth |
| `src/middleware.ts` | SUPPRIMER | Plus nécessaire |
| `src/app/api/*` | SUPPRIMER | Plus de proxy |

## Test de la Migration

1. Lancer le backend :
```bash
cd ../backend
python -m uvicorn app.main:app --reload
```

2. Lancer le frontend :
```bash
npm run dev
```

3. Vérifier :
- [ ] Page de login fonctionne
- [ ] Redirection après login
- [ ] Stats des trackers affichées
- [ ] Graphiques d'historique
- [ ] Hardware monitor (WebSocket)
- [ ] Bouton refresh fonctionne
