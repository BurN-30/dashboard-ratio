# TODO TrackBoard

État au 2026-04-08 après la session de refactor majeur (5 commits, ~8000 lignes
de dette technique en moins, hw-agent en auto-start au boot, Cloudflare Tunnel
réparé, tous les services média joignables).

Ce fichier liste les actions qui restent. Coche au fur et à mesure.

---

## Sécurité — à faire en priorité

- [ ] **Changer le mot de passe SSH du VPS OVH**
  L'ancien mdp `***REDACTED***` a été partagé en clair dans la conversation Claude
  Code du 08/04, donc considéré comme compromis.
  Sur le VPS : `passwd` (puis nouveau mdp via `openssl rand -base64 24` ou
  un gestionnaire de mdp).

- [ ] **Auditer et nettoyer `~/.ssh/authorized_keys` côté VPS**
  Le fichier contient actuellement 13 entrées. Vérifier ce qui est encore
  utilisé, virer les clés des machines auxquelles tu n'as plus accès ou
  qui sont obsolètes (anciens postes, anciens devices, démos, etc.).

- [ ] **Déposer une clé SSH propre depuis le poste de travail principal**
  Génerer si pas déjà fait : `ssh-keygen -t ed25519 -C "nom-du-poste"`
  puis `ssh-copy-id ubuntu@***REDACTED_IP***`.

- [ ] **Tester la connexion par clé** depuis tous les postes que tu utilises
  pour SSH au VPS, **avant** de désactiver l'auth password (sinon lockout).

- [ ] **Désactiver l'auth password SSH côté VPS**
  Une fois les clés validées, dans `/etc/ssh/sshd_config` :
  ```
  PasswordAuthentication no
  PubkeyAuthentication yes
  PermitRootLogin no
  ```
  puis `sudo systemctl reload ssh`. Garder une session SSH ouverte en
  parallèle pendant le test pour éviter le lockout.

- [ ] **Retirer la clé `nathan.saccol@stage-hfp26`** du VPS quand tu n'auras
  plus besoin de la maintenance distante. `nano ~/.ssh/authorized_keys`,
  supprimer la ligne ed25519 finissant par `nathan.saccol@stage-hfp26`.

---

## Déploiement du nouveau code sur le VPS

- [ ] **Pull et rebuild le backend** sur le VPS pour récupérer le healthcheck
  honnête, le Torr9 défensif, le scrub IP, etc.
  ```bash
  cd ~/dashboard-ratio
  git pull origin master
  docker compose down
  docker compose up -d --build
  docker compose logs -f backend
  ```
  ⚠️ Avec le flatten, le path interne `dashboard-v2/` n'existe plus après
  le pull. Le compose est maintenant à `~/dashboard-ratio/docker-compose.yml`
  directement. Le symlink `~/dashboard-v2 → ~/dashboard-ratio/dashboard-v2`
  est devenu cassé, à supprimer (`rm ~/dashboard-v2`).

- [ ] **Vérifier `/health/full`** après le rebuild (auth requise) :
  ```bash
  TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"password":"<ADMIN_PASSWORD>"}' | jq -r '.token.access_token')
  curl -s http://localhost:8000/health/full \
    -H "Authorization: Bearer $TOKEN" | jq
  ```
  Doit retourner `status: ok`, scheduler running, agent connected,
  configured scrapers, last scrape par tracker, hardware history count.

- [ ] **Vérifier que le scraper Torr9 défensif fonctionne** au prochain
  scrape automatique (6h, 12h ou 18h Europe/Paris). Logs attendus :
  ```
  [Torr9] Navigation vers https://torr9.net/login
  [Torr9] Login reussi
  [Torr9] /stats en maintenance, skip   (ou stats parsées si /stats revient)
  [Torr9] Scraping termine (stats_ok=False, points_bonus=N)
  ```

---

## Alembic — transition vers de vraies migrations

- [ ] **Générer la migration initiale autogenerate** sur le VPS :
  ```bash
  docker compose exec backend alembic revision --autogenerate -m "initial schema"
  ```
  Ça crée un fichier dans `backend/alembic/versions/` qui décrit le schéma
  actuel à partir des modèles SQLAlchemy.

- [ ] **Inspecter le fichier généré** dans `backend/alembic/versions/` —
  alembic peut rater quelques cas (renames, types custom, etc.). Vérifier
  qu'il correspond bien à la DB existante.

- [ ] **Stamp head** pour marquer la DB existante comme déjà à jour, sans
  toucher aux tables :
  ```bash
  docker compose exec backend alembic stamp head
  ```
  Ça crée la table `alembic_version` et y inscrit la révision courante.
  Aucune autre table n'est modifiée. C'est une opération non destructive.

- [ ] **Commit le fichier de migration** dans le repo :
  ```bash
  git add backend/alembic/versions/*.py
  git commit -m "Initial alembic migration matching the current schema"
  git push
  ```

- [ ] **(Plus tard) Désactiver `Base.metadata.create_all`** dans
  `backend/app/db/database.py:init_db()` une fois alembic en place et
  qu'on est sûr que tout marche. Garder pour plus tard, pas urgent.

---

## Vercel — fix la démo en ligne

- [ ] **Mettre à jour Root Directory** dans les Settings du projet Vercel :
  - Va sur https://vercel.com/dashboard
  - Ouvre le projet
  - Settings → General → Build & Development Settings
  - **Root Directory** : changer de `dashboard-v2/frontend` → `frontend`
  - Save

- [ ] **Renommer le projet Vercel** pour ne plus exposer le vrai nom dans
  l'URL générée :
  - Settings → General → Project Name → quelque chose d'anonyme genre
    `trackboard-demo`
  - L'URL deviendra `https://trackboard-demo.vercel.app` (ou similaire)

- [ ] **Redéployer manuellement** depuis Deployments → ⋯ → Redeploy
  pour valider que le build passe.

---

## Améliorations futures (priorité basse)

Choses qu'on a discutées dans l'audit initial mais qu'on n'a pas faites
faute de temps. À piocher quand l'envie vient.

### Backend
- [ ] **Page status frontend** consommant `/health/full` pour avoir un coup
  d'œil visuel sur tous les composants (DB, scheduler, agent, scrapers,
  derniers scrapes, services média).
- [ ] **Notifications Telegram/Discord** quand : un tracker passe sous
  ratio 1, un H&R apparaît, l'agent hardware se déconnecte > 5 min,
  un disque dépasse 90 %, un scrape échoue 3 fois d'affilée.
- [ ] **Downsampling de l'historique hardware** : si l'agent envoie toutes
  les 2 sec, ça fait 43k points/jour. Garder tout sur 24h, downsamples à
  1/min entre 24h et 7j, 1/h au-delà. Sinon `hardware_snapshots` va
  exploser.
- [ ] **Healthcheck Docker** dans le compose : utiliser `/health` (le
  nouveau) qui reflète la vraie santé, pas le statique. Déjà fait dans
  le code, vérifier que Docker le respecte au prochain restart.

### Frontend
- [ ] **Dégager les couleurs custom inutilisées** dans `globals.css`
  (763 lignes du template TailAdmin, beaucoup ne servent plus).
- [ ] **Comparatif inter-trackers** : graph empilé, classement par buffer
  ou ratio, "où est ta donnée la plus rentable".
- [ ] **Détection d'anomalies** : Sharewood buffer qui chute brutalement,
  ratio qui dévisse, points bonus qui n'augmentent plus → tag visuel
  "anomalie" sur la TrackerCard.

### pcnat (côté Windows)
- [ ] **Upgrade cloudflared** vers 2026.3.0 sur pcnat (le bug binPath
  sera peut-être fixé en amont, et ton script du repo continuera à
  marcher dans les deux cas car le patch sc.exe est idempotent).
- [ ] **Mode passive du hw-agent** : si tu mets pcnat en sleep (gaming,
  arrêt), envoyer un "going offline" propre au lieu d'un timeout WS.
  Le frontend afficherait "PC en pause" au lieu de "déconnecté".

### Adapter Torr9 quand /stats revient
- [ ] **Réviser `backend/app/scrapers/torr9.py`** une fois `torr9.net/stats`
  sorti de maintenance. La structure HTML aura potentiellement changé
  par rapport à l'ancien `torr9.xyz`. Fetch la page une fois loggué,
  inspecter, ajuster les sélecteurs `find_value_after` / `find_value_before`.

### Métriques et observabilité
- [ ] **Export Prometheus** des stats hardware + tracker → branchement
  Grafana pour des dashboards plus poussés et de la rétention longue.
- [ ] **CLI Python** `trackboard-cli stats`, `trackboard-cli scrape gf`,
  `trackboard-cli login` pour piloter le backend depuis le terminal sans
  passer par le browser.

---

## Notes opérationnelles utiles

### Reconnexion SSH au VPS
```bash
ssh ubuntu@***REDACTED_IP***
```
(Et après désactivation password : ssh par clé only.)

### Lancer le diagnostic complet du VPS
```bash
cd ~/dashboard-ratio
bash scripts/diagnose.sh > /tmp/diag.txt
cat /tmp/diag.txt
```

### Re-tester le scrape Torr9 manuellement
```bash
docker compose exec backend python -c "
import asyncio
from playwright.async_api import async_playwright
from app.scrapers.registry import get_scraper
async def t():
    s = get_scraper('Torr9')
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        r = await s.run(b)
        print(r)
        await b.close()
asyncio.run(t())
"
```

### Réparer le service cloudflared sur pcnat (si jamais ça recasse)
```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\scripts\fix-cloudflare-tunnel.ps1" -TestHostname "tautulli.nathansaccol.fr"
```

### Voir l'état de la tâche hw-agent
```powershell
Get-ScheduledTask TrackBoard-hw-agent | Select State, *
Get-ScheduledTaskInfo TrackBoard-hw-agent
```
