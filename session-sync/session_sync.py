#!/usr/bin/env python3
"""
Session Sync - Dépose sur TrackBoard la session d'un tracker à connexion manuelle (C411).

La connexion de C411 passe par un captcha : ce script ne s'y connecte jamais, ne remplit
aucun formulaire et ne touche à aucun captcha. Il transmet à TrackBoard une session que
l'utilisateur a ouverte lui-même, par POST /scrapers/session/{tracker}.

Trois sources possibles :
    --navigateur          profil de navigateur dédié (Playwright, fenêtre visible) : si la
                          session du profil est encore assez longue, elle est envoyée ; sinon
                          la page de connexion s'ouvre et le script attend que l'utilisateur
                          se connecte lui-même, puis envoie le storage_state.
    --storage-state F     fichier JSON issu de context.storage_state() (Playwright).
    --cookie              valeur du cookie de session, lue sur l'entrée standard.
    --verifier            ne dépose rien : contrôle la configuration et l'accès à TrackBoard.

Authentification : jeton dédié SESSION_SYNC_TOKEN (en-tête « Authorization: Bearer »), le
même ici et dans le .env du serveur. TrackBoard ne l'accepte que sur la route de dépôt : il
n'ouvre ni l'interface ni les autres routes, et ce poste ne détient pas le mot de passe
d'administration.

Configuration via .env (à côté de ce fichier) ou variables d'environnement utilisateur :
    TRACKBOARD_URL=https://<machine>.<tailnet>.ts.net:8444
    SESSION_SYNC_TOKEN=<SESSION_SYNC_TOKEN du serveur>

Codes de sortie : 0 session acceptée, 1 erreur (configuration, réseau, TrackBoard),
2 session refusée par le site, 3 connexion manuelle non faite dans le délai.
"""
import argparse
import hashlib
import json
import logging
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

ICI = Path(__file__).resolve().parent
load_dotenv(ICI / ".env")  # sans écraser les variables d'environnement déjà définies

# Configuration
TRACKBOARD_URL = os.getenv("TRACKBOARD_URL", "").rstrip("/")
SESSION_SYNC_TOKEN = os.getenv("SESSION_SYNC_TOKEN", "").strip()
TRACKER = os.getenv("SESSION_SYNC_TRACKER", "C411")
ATTENTE_MIN = float(os.getenv("SESSION_SYNC_ATTENTE_MIN", "30"))    # attente de la connexion manuelle
# Session du profil à moins de tant d'heures de son échéance : nouvelle connexion demandée.
# Doit dépasser l'intervalle de la tâche planifiée (6 jours = 144 h), sinon une session
# jugée « assez longue » expirerait avant le passage suivant.
SEUIL_HEURES = float(os.getenv("SESSION_SYNC_SEUIL_HEURES", "150"))
CANAL = os.getenv("SESSION_SYNC_CANAL", "msedge")                   # navigateur installé (msedge, chrome)
DOSSIER_LOG = Path(os.getenv("SESSION_SYNC_LOG_DIR") or ICI / "logs")
DOSSIER_DONNEES = Path(os.getenv("SESSION_SYNC_DATA_DIR")
                       or Path(os.getenv("LOCALAPPDATA") or Path.home()) / "TrackBoard" / "session-sync")

# Sites à session manuelle (mêmes repères que backend/app/scrapers/c411.py)
SITES = {
    "C411": {
        "domaine": "c411.org",
        "cookie": "__Host-c411_session",
        "accueil": "https://c411.org/",
        "connexion": "https://c411.org/login",
        "moi": "https://c411.org/api/auth/me",
        "duree_jours": 7,  # durée fixe : les visites ne prolongent pas la session
    },
}

OK, ERREUR, REFUSEE, ATTENTE_DEPASSEE = 0, 1, 2, 3

journal = logging.getLogger("session-sync")


class ErreurSync(Exception):
    """Échec expliqué, avec son code de sortie. Le message ne contient jamais de secret."""

    def __init__(self, message: str, code: int = ERREUR):
        super().__init__(message)
        self.code = code


def configurer_journal() -> None:
    """Journal horodaté dans logs/session-sync.log, avec rotation (5 fichiers de 512 Kio)."""
    if journal.handlers:
        return
    DOSSIER_LOG.mkdir(parents=True, exist_ok=True)
    forme = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    fichier = RotatingFileHandler(DOSSIER_LOG / "session-sync.log", maxBytes=512 * 1024,
                                  backupCount=5, encoding="utf-8")
    fichier.setFormatter(forme)
    journal.addHandler(fichier)
    if sys.stderr is not None:  # absent sous pythonw.exe (tâche planifiée sans console)
        console = logging.StreamHandler()
        console.setFormatter(forme)
        journal.addHandler(console)
    journal.setLevel(logging.INFO)


# === TRACKBOARD ===

class _SansRedirection(urllib.request.HTTPRedirectHandler):
    """Aucune redirection suivie : le jeton ne part que vers l'hôte configuré."""

    def redirect_request(self, *args, **kwargs):
        return None


def _base_url() -> str:
    if not TRACKBOARD_URL:
        raise ErreurSync("TRACKBOARD_URL non configurée (fichier .env)")
    url = urllib.parse.urlsplit(TRACKBOARD_URL)
    local = url.hostname in ("localhost", "127.0.0.1", "::1")
    if url.scheme != "https" and not (url.scheme == "http" and local):
        raise ErreurSync("TRACKBOARD_URL doit commencer par https:// (certificat vérifié)")
    return TRACKBOARD_URL


def _appel(chemin: str, corps: Optional[dict] = None, jeton: Optional[str] = None,
           delai: float = 30) -> tuple[int, dict]:
    """Requête JSON vers TrackBoard, certificat TLS vérifié. Rend (code HTTP, corps JSON)."""
    entetes = {"Accept": "application/json", "User-Agent": "trackboard-session-sync"}
    donnees = None
    if corps is not None:
        donnees = json.dumps(corps).encode()
        entetes["Content-Type"] = "application/json"
    if jeton:
        entetes["Authorization"] = f"Bearer {jeton}"
    requete = urllib.request.Request(_base_url() + chemin, data=donnees, headers=entetes,
                                     method="POST" if corps is not None else "GET")
    ouvreur = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl.create_default_context()), _SansRedirection())
    try:
        with ouvreur.open(requete, timeout=delai) as reponse:
            code, brut = reponse.status, reponse.read()
    except urllib.error.HTTPError as e:
        code, brut = e.code, e.read()
    except ssl.SSLCertVerificationError as e:
        raise ErreurSync(f"Certificat TLS de TrackBoard refusé ({e.verify_message})")
    except (urllib.error.URLError, OSError) as e:
        raison = getattr(e, "reason", e)
        if isinstance(raison, ssl.SSLCertVerificationError):
            raise ErreurSync(f"Certificat TLS de TrackBoard refusé ({raison.verify_message})")
        raise ErreurSync(f"TrackBoard injoignable ({type(raison).__name__} : {raison}). Tailscale est-il connecté ?")
    try:
        contenu = json.loads(brut)
    except ValueError:
        contenu = {}
    return code, contenu if isinstance(contenu, dict) else {}


def _jeton() -> str:
    """Jeton dédié SESSION_SYNC_TOKEN, jamais journalisé."""
    if len(SESSION_SYNC_TOKEN) < 32:
        raise ErreurSync("SESSION_SYNC_TOKEN non configuré ou trop court (fichier .env, 32 caractères au moins)")
    return SESSION_SYNC_TOKEN


def _refus_du_jeton(code: int) -> None:
    if code in (401, 403):
        raise ErreurSync("TrackBoard refuse le jeton : SESSION_SYNC_TOKEN doit être le même ici et sur le serveur")


def pousser_session(storage_state: Optional[dict] = None, valeur: Optional[str] = None,
                    tracker: Optional[str] = None, essais: int = 3, pause: float = 60) -> dict:
    """
    Dépose une session sur TrackBoard : soit un storage_state de Playwright (dictionnaire),
    soit la valeur du cookie de session, jamais les deux. TrackBoard écrit la session, lance
    un relevé de contrôle et répond {"status": "ok" | "refusee", "message": ...}.

    Rend la réponse si le statut est « ok ». Lève ErreurSync sinon : code REFUSEE quand le
    site refuse la session, code ERREUR pour le reste. Aucune valeur n'est journalisée.
    """
    if (storage_state is None) == (valeur is None):
        raise ValueError("fournir storage_state ou valeur, l'un des deux")
    tracker = tracker or TRACKER
    if storage_state is not None:
        corps, forme = {"storage_state": storage_state}, f"storage_state, {len(storage_state.get('cookies', []))} cookie(s)"
    else:
        corps, forme = {"valeur": valeur}, "cookie seul"
    jeton = _jeton()
    chemin = f"/scrapers/session/{urllib.parse.quote(tracker, safe='')}"
    for essai in range(1, essais + 1):
        journal.info("[%s] Envoi de la session à TrackBoard (%s)", tracker, forme)
        # Le relevé de contrôle se fait pendant la requête (navigateur côté serveur).
        code, reponse = _appel(chemin, corps, jeton, delai=240)
        if code != 409 or essai == essais:
            break
        journal.warning("[%s] Un relevé est en cours sur TrackBoard, nouvel essai dans %d s", tracker, pause)
        time.sleep(pause)
    _refus_du_jeton(code)
    if code != 200:
        raise ErreurSync(f"[{tracker}] TrackBoard a répondu HTTP {code} : {reponse.get('detail') or 'sans détail'}")
    if reponse.get("status") != "ok":
        raise ErreurSync(f"[{tracker}] {reponse.get('message') or 'Session refusée'}", REFUSEE)
    journal.info("[%s] %s", tracker, reponse.get("message") or "Session acceptée")
    return reponse


def verifier() -> None:
    """
    Contrôle la configuration, le certificat et le jeton, sans rien déposer : le jeton ne
    vaut que pour la route de dépôt, on lui envoie donc un corps vide, que TrackBoard
    refuse (HTTP 400) après avoir accepté le jeton et reconnu le tracker.
    """
    code, reponse = _appel(f"/scrapers/session/{urllib.parse.quote(TRACKER, safe='')}", {}, _jeton())
    _refus_du_jeton(code)
    if code == 404:
        raise ErreurSync(f"[{TRACKER}] Tracker inconnu de TrackBoard ou sans session manuelle")
    if code != 400:
        raise ErreurSync(f"TrackBoard a répondu HTTP {code} au contrôle : {reponse.get('detail') or 'sans détail'}")
    journal.info("TrackBoard joignable, certificat valide, jeton accepté (%s, tracker %s)",
                 urllib.parse.urlsplit(_base_url()).hostname, TRACKER)


# === STORAGE_STATE ===

def _dans_le_site(hote, domaine: str) -> bool:
    hote = str(hote or "").lstrip(".").lower()
    return hote == domaine or hote.endswith("." + domaine)


def filtrer_storage_state(etat: dict, tracker: Optional[str] = None) -> dict:
    """
    Ne garde d'un storage_state que ce qui concerne le site du tracker : ses cookies (session
    et cookies secondaires) et son localStorage. Les cookies de Cloudflare (cf_clearance,
    __cf_bm...) restent sur ce poste : ils sont liés à la machine qui a passé le défi.
    """
    site = SITES[tracker or TRACKER]
    cookies = [c for c in etat.get("cookies", [])
               if _dans_le_site(c.get("domain"), site["domaine"])
               and not str(c.get("name", "")).lower().startswith(("cf_", "__cf", "_cf"))]
    origines = [o for o in etat.get("origins", [])
                if _dans_le_site(urllib.parse.urlsplit(str(o.get("origin", ""))).hostname, site["domaine"])]
    if not any(c.get("name") == site["cookie"] for c in cookies):
        raise ErreurSync(f"storage_state sans cookie {site['cookie']}")
    return {"cookies": cookies, "origins": origines}


# === NAVIGATEUR (profil dédié, connexion faite par l'utilisateur) ===

def _fichier_etat() -> Path:
    return DOSSIER_DONNEES / f"etat-{TRACKER.lower()}.json"


def _duree_restante(cookie: dict, site: dict) -> float:
    """
    Secondes de session restantes. La durée est fixe : on retient la date où cette session a
    été vue pour la première fois (empreinte de la valeur, jamais la valeur) et l'échéance
    annoncée par le cookie, la plus proche des deux.
    """
    maintenant = time.time()
    empreinte = hashlib.sha256(cookie["value"].encode()).hexdigest()[:16]
    try:
        etat = json.loads(_fichier_etat().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        etat = {}
    if etat.get("empreinte") != empreinte:
        etat = {"empreinte": empreinte, "vue_le": maintenant}
        _fichier_etat().write_text(json.dumps(etat), encoding="utf-8")
    echeances = [float(etat["vue_le"]) + site["duree_jours"] * 86400]
    if (cookie.get("expires") or -1) > 0:
        echeances.append(float(cookie["expires"]))
    return min(echeances) - maintenant


def session_depuis_navigateur() -> dict:
    """
    Ouvre le profil dédié dans une fenêtre visible et rend le storage_state du site.

    Session du profil valide pour plus de SESSION_SYNC_SEUIL_HEURES : rien à faire. Sinon la
    page de connexion est affichée et le script attend, sans rien remplir ni cliquer, que
    l'utilisateur se connecte lui-même (captcha compris), SESSION_SYNC_ATTENTE_MIN au plus.
    """
    site = SITES.get(TRACKER)
    if not site:
        raise ErreurSync(f"[{TRACKER}] Mode navigateur non prévu pour ce tracker")
    try:
        from playwright.sync_api import Error as ErreurPlaywright, sync_playwright
    except ImportError:
        raise ErreurSync("Playwright absent : pip install -r requirements.txt")
    profil = DOSSIER_DONNEES / f"profil-{TRACKER.lower()}"
    profil.mkdir(parents=True, exist_ok=True)

    def connecte(contexte) -> bool:
        reponse = contexte.request.get(site["moi"], timeout=30000)
        try:
            return reponse.ok and reponse.json().get("authenticated") is True
        except ValueError:
            return False  # page de défi ou d'erreur à la place du JSON

    def cookie_de_session(contexte) -> Optional[dict]:
        return next((c for c in contexte.cookies(site["accueil"]) if c["name"] == site["cookie"]), None)

    with sync_playwright() as p:
        try:
            contexte = p.chromium.launch_persistent_context(
                str(profil), channel=CANAL or None, headless=False, no_viewport=True)
        except ErreurPlaywright as e:
            raise ErreurSync(f"Navigateur « {CANAL} » impossible à lancer ({str(e).splitlines()[0][:150]})")
        try:
            page = contexte.pages[0] if contexte.pages else contexte.new_page()
            page.goto(site["accueil"], wait_until="domcontentloaded", timeout=60000)
            cookie = cookie_de_session(contexte)
            restant = _duree_restante(cookie, site) if cookie and connecte(contexte) else None
            if restant is not None and restant >= SEUIL_HEURES * 3600:
                journal.info("[%s] Session du profil valide encore %.0f h : pas de connexion à refaire",
                             TRACKER, restant / 3600)
            else:
                if restant is not None:
                    journal.info("[%s] Session du profil à %.0f h de l'échéance : nouvelle connexion demandée",
                                 TRACKER, restant / 3600)
                    contexte.clear_cookies(name=site["cookie"])  # sinon le site n'affiche plus sa page de connexion
                page.goto(site["connexion"], wait_until="domcontentloaded", timeout=60000)
                page.bring_to_front()
                journal.info("[%s] Connexion manuelle attendue dans la fenêtre ouverte (%g min au plus)",
                             TRACKER, ATTENTE_MIN)
                limite = time.monotonic() + ATTENTE_MIN * 60
                while True:
                    if not contexte.pages:
                        raise ErreurSync(f"[{TRACKER}] Fenêtre fermée avant la connexion", ATTENTE_DEPASSEE)
                    if time.monotonic() >= limite:
                        raise ErreurSync(f"[{TRACKER}] Pas de connexion manuelle en {ATTENTE_MIN:g} min : "
                                         "relancer la tâche pour réessayer", ATTENTE_DEPASSEE)
                    contexte.pages[0].wait_for_timeout(10000)
                    cookie = cookie_de_session(contexte)
                    if cookie and connecte(contexte):
                        break
                _duree_restante(cookie, site)  # note la date de cette nouvelle session
                journal.info("[%s] Connexion faite par l'utilisateur, session relevée", TRACKER)
            return filtrer_storage_state(contexte.storage_state())
        except ErreurPlaywright as e:
            if not contexte.pages:
                raise ErreurSync(f"[{TRACKER}] Fenêtre fermée avant la fin", ATTENTE_DEPASSEE)
            raise ErreurSync(f"[{TRACKER}] Navigateur : {str(e).splitlines()[0][:150]}")
        finally:
            try:
                contexte.close()
            except ErreurPlaywright:
                pass


# === MAIN ===

def main(arguments: Optional[list[str]] = None) -> int:
    analyseur = argparse.ArgumentParser(description="Dépose sur TrackBoard une session ouverte à la main (C411).")
    source = analyseur.add_mutually_exclusive_group(required=True)
    source.add_argument("--navigateur", action="store_true", help="profil de navigateur dédié (fenêtre visible)")
    source.add_argument("--storage-state", metavar="FICHIER", help="fichier JSON issu de context.storage_state()")
    source.add_argument("--cookie", action="store_true", help="valeur du cookie de session lue sur l'entrée standard")
    source.add_argument("--verifier", action="store_true", help="contrôle l'accès à TrackBoard, ne dépose rien")
    options = analyseur.parse_args(arguments)
    configurer_journal()
    try:
        if options.verifier:
            verifier()
        elif options.navigateur:
            _base_url()  # configuration contrôlée avant d'ouvrir une fenêtre
            pousser_session(storage_state=session_depuis_navigateur())
        elif options.storage_state:
            try:
                etat = json.loads(Path(options.storage_state).read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                raise ErreurSync(f"Fichier storage_state illisible ({type(e).__name__})")
            if not isinstance(etat, dict):
                raise ErreurSync("Fichier storage_state : objet JSON attendu")
            pousser_session(storage_state=filtrer_storage_state(etat) if TRACKER in SITES else etat)
        else:
            if sys.stdin is not None and sys.stdin.isatty():
                from getpass import getpass
                valeur = getpass("Valeur du cookie de session (saisie masquée) : ")
            else:
                valeur = sys.stdin.readline() if sys.stdin is not None else ""
            if not valeur.strip():
                raise ErreurSync("Aucune valeur de cookie reçue")
            pousser_session(valeur=valeur.strip())
        return OK
    except ErreurSync as e:
        journal.error("%s", e)
        return e.code
    except Exception as e:  # imprévu : type et message seulement, les données n'y figurent pas
        journal.error("Erreur imprévue : %s : %s", type(e).__name__, str(e)[:200])
        return ERREUR


if __name__ == "__main__":
    sys.exit(main())
