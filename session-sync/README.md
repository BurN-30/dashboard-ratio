# session-sync : renouveler la session C411 depuis le PC Windows

La connexion à C411 passe par un captcha et la session dure 7 jours fixes. TrackBoard ne s'y connecte donc jamais seul : il relit une session ouverte à la main. Ce script la transmet à TrackBoard depuis le PC Windows allumé en permanence (celui de `hw-agent`), tous les 6 jours.

**Ce qu'il ne fait pas** : se connecter à C411, remplir le formulaire, résoudre ou contourner le captcha. Quand la session est à refaire, il ouvre la page de connexion dans une fenêtre et attend que l'utilisateur se connecte lui-même.

## Fonctionnement

```
Tâche planifiée (compte utilisateur, tous les 6 jours)
  └─ session_sync.py --navigateur
       ├─ ouvre un profil de navigateur dédié (Edge, fenêtre visible)
       ├─ session du profil valable jusqu'au passage suivant (plus de 150 h) ?
       │      oui : rien à faire à la main
       │      non : page de connexion affichée, attente de la connexion manuelle (30 min)
       ├─ context.storage_state() : cookies de c411.org (session + cookies secondaires)
       └─ POST /scrapers/session/C411 {"storage_state": {...}}  ──►  TrackBoard (tailnet, TLS vérifié)
                                                                     relevé de contrôle : "ok" ou "refusee"
```

- **Authentification vers TrackBoard** : jeton dédié `SESSION_SYNC_TOKEN`, envoyé en `Authorization: Bearer`. Le serveur ne l'accepte que sur `POST /scrapers/session/{tracker}` : il n'ouvre ni l'interface ni les autres routes, et le PC ne détient pas le mot de passe d'administration. Le bouton « Reconnecter » de l'interface continue de passer par le jeton de connexion habituel.
- **Cookies envoyés** : ceux de `c411.org` seulement. Les cookies de Cloudflare (`cf_clearance`, `__cf_bm`) restent sur le poste, et le serveur les écarte aussi.
- **Rien de sensible dans le journal** : ni cookie, ni mot de passe, ni jeton.

## Installation

Prérequis : Python 3.10 ou plus dans le `PATH`, Microsoft Edge, Tailscale connecté.

1. Créer la configuration :

   ```powershell
   cd <dossier du dépôt>\session-sync
   Copy-Item .env.example .env
   notepad .env
   ```

   Renseigner `TRACKBOARD_URL` (adresse `https://...ts.net:8444` de TrackBoard) et `SESSION_SYNC_TOKEN`. Ce jeton doit être le même dans le `.env` du serveur (variable `SESSION_SYNC_TOKEN`, 32 caractères au moins, backend à redémarrer après l'ajout) ; pour en créer un : `openssl rand -hex 32`.

2. Installer la tâche planifiée, dans un PowerShell ordinaire (**pas en administrateur**) :

   ```powershell
   powershell.exe -ExecutionPolicy Bypass -File ..\scripts\install-session-sync-task.ps1
   ```

   Le script crée le venv, installe les dépendances, réserve la lecture de `.env` au compte courant, enregistre la tâche `TrackBoard-session-sync` (tous les 6 jours à 19:00, `-Heure 21:30` pour changer) et contrôle l'accès à TrackBoard.

   La tâche tourne sous le compte de l'utilisateur, **sans privilège** : `RunLevel Limited`, `LogonType Interactive`, jamais `SYSTEM`. Elle ne s'exécute que si une session Windows est ouverte, ce qui est voulu : la fenêtre de connexion doit pouvoir s'afficher. Une échéance manquée est rattrapée à l'ouverture de session suivante.

3. Premier dépôt : lancer la tâche une fois et se connecter à C411 dans la fenêtre qui s'ouvre.

   ```powershell
   Start-ScheduledTask -TaskName TrackBoard-session-sync
   ```

## Vérification

```powershell
# Compte et niveau de la tâche : UserId = le compte courant, Interactive, Limited
(Get-ScheduledTask -TaskName TrackBoard-session-sync).Principal | Format-List UserId, LogonType, RunLevel

# Accès à TrackBoard (certificat, jeton), sans rien déposer
.\venv\Scripts\python.exe session_sync.py --verifier

# Dernier passage : 0 = session acceptée
(Get-ScheduledTaskInfo -TaskName TrackBoard-session-sync).LastTaskResult
Get-Content .\logs\session-sync.log -Tail 20
```

| Code | Sens |
|---|---|
| 0 | Session acceptée, relevé de contrôle réussi |
| 1 | Erreur : configuration, réseau, certificat, TrackBoard |
| 2 | Session refusée par C411 |
| 3 | Connexion manuelle non faite dans le délai (relancer la tâche) |

Le journal est dans `logs\session-sync.log` (rotation : 5 fichiers de 512 Kio). Le profil de navigateur dédié est dans `%LOCALAPPDATA%\TrackBoard\session-sync`, hors du dépôt.

## Autres usages

```powershell
# Déposer un storage_state exporté ailleurs (context.storage_state() de Playwright)
.\venv\Scripts\python.exe session_sync.py --storage-state C:\chemin\etat.json

# Déposer la seule valeur du cookie __Host-c411_session (saisie masquée)
.\venv\Scripts\python.exe session_sync.py --cookie
```

Depuis un autre script Python :

```python
from session_sync import pousser_session

pousser_session(storage_state=etat)   # dictionnaire issu de context.storage_state()
pousser_session(valeur="...")         # ou la valeur du cookie de session
```

`pousser_session` rend la réponse de TrackBoard quand `status` vaut `"ok"` et lève `ErreurSync` sinon.

## Limites connues

- Si personne ne se connecte dans la fenêtre avant la fin du délai, la session n'est pas renouvelée : le rappel Discord de TrackBoard (36 h avant l'échéance) reste le filet. Relancer la tâche à la main.
- La fenêtre est pilotée par Playwright, sans aucun camouflage. Si le captcha de C411 refuse de valider dans cette fenêtre, se connecter dans son navigateur habituel et déposer la session par le bouton « Reconnecter » de TrackBoard ou par `--cookie`.
- La session durant 7 jours fixes, chaque passage (tous les 6 jours) demande en pratique une connexion manuelle : seule une session de moins de 18 h est réutilisée telle quelle. `SESSION_SYNC_SEUIL_HEURES` (150 h) doit rester supérieur à l'intervalle de la tâche (144 h), sinon une session pourrait expirer entre deux passages.
