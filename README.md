# Torrent Dashboard

Un seul README pour tout: scraper sur une machine distante, upload FTP des JSON, et dashboard Next.js qui les consomme.

## Vue rapide
- Scraper (Playwright) tourne sur une autre machine, génère `stats.json` et `history.json`, puis les envoie en FTP vers `dash.example.com`.
- Les routes Next.js `/api/stats` et `/api/history` proxient `${JSON_BASE_URL}/stats.json` et `${JSON_BASE_URL}/history.json`.
- Le frontend lit ces API et affiche les stats/graphes.

## Démarrage (scraper)
1) Prérequis: Python 3.8+, `pip install -r requirements.txt`, puis `python -m playwright install chromium`.
2) Copier `.env.example` en `.env` et le remplir:
   - FTP_HOST, FTP_USER, FTP_PASS, FTP_DIR
   - GF_USER / GF_PASS (Generation-Free)
   - TOS_USER / TOS_PASS (TheOldSchool)
   - SW_USER / SW_PASS (Sharewood)
3) Lancer: `python scraper.py` (génère `stats.json` + `history.json` et les envoie en FTP).
4) Planifier (optionnel):
   - Linux: `0 */6 * * * cd /path && python3 scraper.py >> scraper.log 2>&1`
   - Windows: Planificateur de tâches -> `python scraper.py` toutes les 6h.

## Frontend (torrent-dashboard)
- Dev: `cd torrent-dashboard && npm install && npm run dev` (http://localhost:3000).
- Variables locales: créer `torrent-dashboard/.env.local` avec `ADMIN_PASSWORD=...` et `JSON_BASE_URL=https://example.com/dash`.
- Déploiement (Vercel): ajouter `ADMIN_PASSWORD` et `JSON_BASE_URL` dans Settings > Environment Variables. Root = `torrent-dashboard`. Build: `npm run build && npm run start` ou via Vercel.

## Fichiers produits
- `stats.json`: snapshot actuel.
- `history.json`: historique avec réduction après 30 jours (1 entrée/jour).
- Servis via FTP dans `/public_html/dash/` et accessibles via `${JSON_BASE_URL}` (ex: `https://example.com/dash`).

## Tests (optionnel)
- `python test_architecture.py` (nécessite `requests` et `python-dotenv`). Vérifie fichiers locaux, .env, FTP, accès web; échouera pour les routes Next tant que le site n’est pas déployé.

## Structure
```
dashboard-ratio/
├─ scraper.py
├─ requirements.txt
├─ .env.example
├─ stats.json / history.json (générés)
├─ test_architecture.py
├─ install_scraper.sh / install_scraper.bat
└─ torrent-dashboard/ (app Next.js)
   ├─ src/app/api/stats|history/route.ts (proxy)
   ├─ src/app/page.tsx, traffic, warnings, login
   └─ autres composants/lib/types
```

## Sécurité rapide
- Ne pas committer `.env`.
- Les JSON sont publics par design; si besoin, protéger via `.htaccess` côté FTP.
- HTTPS obligatoire pour le site.

## Déploiement minimal (rappel)
- Scraper: tourner sur une machine distante + FTP OK.
- Frontend: déployer le dossier `torrent-dashboard` (Vercel conseillé).

C’est tout: un README unique, léger, et suffisant pour GitHub.