"""
Routes API pour les scrapers.
"""
import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from playwright.async_api import async_playwright

logger = logging.getLogger("dashboard.scraper")

from app.auth.jwt import get_current_user, get_session_depositor, TokenData
from app.db.database import async_session
from app.db.models import TrackerStats, ScraperState
from app.scrapers.registry import (
    get_scrapers,
    get_scraper,
    list_available_scrapers,
    list_all_sites,
)
from app.scrapers.base import ScrapedStats
from app.config import get_settings
from app.notifications import (
    decider_alerte_avertissements, decider_alerte_echec, session_bientot_expiree,
    notify_scrape_failures, notify_scrape_recovery,
    notify_ratio_critical, notify_avertissements, notify_session_bientot_expiree,
    notify_parser_suspect,
)

router = APIRouter()

# Flag pour eviter les scrapes simultanees
_scraping_in_progress = False


@dataclass
class ScrapeResult:
    tracker_name: str
    status: str  # "ok", "error", "skipped"
    last_success_at: datetime | None = None
    last_attempt_at: datetime | None = None
    last_error: str | None = None
    consecutive_failures: int = 0
    last_known_active_warnings: int = 0  # Pour detecter les nouveaux avertissements actifs (H&R en cours)
    last_failure_alert_at: datetime | None = None  # Derniere alerte d'echec (un rappel par 24 h)
    last_warning_alert_at: datetime | None = None  # Derniere alerte d'avertissements (idem)
    session_deposited_at: datetime | None = None  # Session manuelle : date du depot
    session_expiry_alert_at: datetime | None = None  # Session manuelle : rappel d'expiration envoye
    parser_suspect: bool = False  # In-memory only : dedupe l'alerte Discord "parser casse"


_scrape_results: dict[str, ScrapeResult] = {}


async def load_scraper_state_from_db() -> None:
    """
    Restaure _scrape_results depuis la DB au démarrage.
    Sans ça, les compteurs (consecutive_failures, last_known_active_warnings)
    repartiraient à zéro à chaque restart et les notifications "3+ échecs"
    ou "nouvel avertissement actif" ne se déclencheraient jamais correctement.
    """
    try:
        async with async_session() as db:
            result = await db.execute(select(ScraperState))
            for row in result.scalars().all():
                _scrape_results[row.tracker_name] = ScrapeResult(
                    tracker_name=row.tracker_name,
                    status="ok",
                    last_success_at=row.last_success_at,
                    consecutive_failures=row.consecutive_failures or 0,
                    last_known_active_warnings=row.last_known_active_warnings or 0,
                    last_failure_alert_at=row.last_failure_alert_at,
                    last_warning_alert_at=row.last_warning_alert_at,
                    session_deposited_at=row.session_deposited_at,
                    session_expiry_alert_at=row.session_expiry_alert_at,
                )
        logger.info("Etat scraper restaure depuis la DB: %d tracker(s)", len(_scrape_results))
    except Exception as e:
        logger.warning("Impossible de restaurer l'etat scraper (premier run ?): %s", e)


async def _persist_scraper_state(name: str) -> None:
    """Upsert l'état courant d'un tracker en DB. Appelé après chaque scrape."""
    sr = _scrape_results.get(name)
    if sr is None:
        return
    try:
        async with async_session() as db:
            stmt = pg_insert(ScraperState).values(
                tracker_name=sr.tracker_name,
                consecutive_failures=sr.consecutive_failures,
                last_success_at=sr.last_success_at,
                last_known_active_warnings=sr.last_known_active_warnings,
                last_failure_alert_at=sr.last_failure_alert_at,
                last_warning_alert_at=sr.last_warning_alert_at,
                session_deposited_at=sr.session_deposited_at,
                session_expiry_alert_at=sr.session_expiry_alert_at,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["tracker_name"],
                set_={
                    "consecutive_failures": stmt.excluded.consecutive_failures,
                    "last_success_at": stmt.excluded.last_success_at,
                    "last_known_active_warnings": stmt.excluded.last_known_active_warnings,
                    "last_failure_alert_at": stmt.excluded.last_failure_alert_at,
                    "last_warning_alert_at": stmt.excluded.last_warning_alert_at,
                    "session_deposited_at": stmt.excluded.session_deposited_at,
                    "session_expiry_alert_at": stmt.excluded.session_expiry_alert_at,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            await db.execute(stmt)
            await db.commit()
    except Exception as e:
        logger.warning("Echec persist etat scraper %s: %s", name, e)


class ScrapeStatus(BaseModel):
    """Status d'un scrape."""
    status: str
    message: str
    tracker: Optional[str] = None


class TrackerStatsResponse(BaseModel):
    """Reponse avec les stats d'un tracker."""
    tracker_name: str
    ratio: str
    buffer: str
    vol_upload: str
    vol_download: str
    points_bonus: str
    count_seed: str
    seed_time_total: str
    scraped_at: Optional[str] = None


@router.get("/sites")
async def get_sites(user: TokenData = Depends(get_current_user)):
    """Liste tous les sites supportes. (Auth requise : URL de connexion des sites)"""
    return {
        "sites": list_all_sites(),
        "configured_count": len(list_available_scrapers()),
    }


@router.get("/available")
async def get_available_scrapers(user: TokenData = Depends(get_current_user)):
    """Liste les scrapers avec identifiants configures. (Auth requise)"""
    return {
        "scrapers": list_available_scrapers(),
    }


@router.post("/run", response_model=ScrapeStatus)
async def run_all_scrapers(
    background_tasks: BackgroundTasks,
    user: TokenData = Depends(get_current_user),
):
    """
    Lance le scraping de tous les trackers configures.
    Le scraping s'execute en arriere-plan.
    """
    global _scraping_in_progress

    if _scraping_in_progress:
        return ScrapeStatus(
            status="busy",
            message="Un scraping est deja en cours. Reessayez dans quelques minutes."
        )

    scrapers = get_scrapers()
    if not scrapers:
        raise HTTPException(status_code=500, detail="Aucun scraper configure")

    # Lancer en arriere-plan
    background_tasks.add_task(run_scraping_task)

    return ScrapeStatus(
        status="started",
        message=f"Scraping lance pour {len(scrapers)} tracker(s)"
    )


@router.post("/run/{tracker_name}", response_model=ScrapeStatus)
async def run_single_scraper(
    tracker_name: str,
    background_tasks: BackgroundTasks,
    user: TokenData = Depends(get_current_user),
):
    """Lance le scraping d'un tracker specifique."""
    global _scraping_in_progress

    if _scraping_in_progress:
        return ScrapeStatus(
            status="busy",
            message="Un scraping est deja en cours."
        )

    scraper = get_scraper(tracker_name)
    if not scraper:
        raise HTTPException(status_code=404, detail=f"Tracker '{tracker_name}' non trouve ou non configure")

    background_tasks.add_task(run_scraping_task, tracker_name=tracker_name)

    return ScrapeStatus(
        status="started",
        message=f"Scraping lance pour {tracker_name}",
        tracker=tracker_name
    )


def session_manuelle(name: str) -> bool:
    """Vrai pour un tracker dont la session est deposee a la main (captcha a la connexion)."""
    scraper = get_scraper(name)
    return bool(scraper and scraper.SESSION_COOKIE)


def _reconnexion(scraper) -> Optional[dict]:
    """Elements de la marche a suivre de reconnexion (None hors session manuelle)."""
    if not getattr(scraper, "SESSION_COOKIE", None):
        return None
    return {
        "login_url": scraper.config.login_url,
        "cookie": scraper.SESSION_COOKIE["name"],
        "trackboard_url": get_settings().trackboard_url,
    }


def nettoyer_valeur_cookie(valeur, nom: str) -> Optional[str]:
    """
    Valeur collee par l'utilisateur -> valeur du cookie, ou None si elle est inutilisable.
    Accepte « nom=valeur » et les guillemets autour ; refuse tout caractere interdit dans
    une valeur de cookie (espace, point-virgule, virgule, guillemet, antislash, controle).
    """
    if not isinstance(valeur, str):
        return None
    valeur = valeur.strip()
    if valeur.startswith(nom + "="):
        valeur = valeur[len(nom) + 1:]
    valeur = valeur.strip().strip('"').strip()
    if not 16 <= len(valeur) <= 4096:
        return None
    if any(c in ' ";,\\' or not 0x21 <= ord(c) <= 0x7E for c in valeur):
        return None
    return valeur


# Bornes d'un storage_state déposé (un état de navigateur complet reste très en dessous).
MAX_COOKIES_RECUS = 500
MAX_COOKIES_GARDES = 60
MAX_ENTREES_LOCALSTORAGE = 200
MAX_TAILLE_LOCALSTORAGE = 200_000


def _cookie_cloudflare(nom: str) -> bool:
    """
    Cookies de Cloudflare (cf_clearance, __cf_bm...) : liés à la machine et au navigateur qui
    ont passé le défi. Jamais importés d'un autre poste : ce serait rejouer ailleurs un défi
    passé, et ils écraseraient ceux que le collecteur a obtenus lui-même.
    """
    nom = nom.lower()
    return nom.startswith(("cf_", "__cf", "_cf"))


def _domaine_du_site(modele: dict) -> str:
    domaine = modele["domain"].lstrip(".").lower()
    return domaine[4:] if domaine.startswith("www.") else domaine


def _dans_le_site(hote, site: str) -> bool:
    if not isinstance(hote, str):
        return False
    hote = hote.lstrip(".").lower()
    return hote == site or hote.endswith("." + site)


def _texte_de_cookie(v, maxi: int, interdits: str, mini: int = 0) -> bool:
    return (isinstance(v, str) and mini <= len(v) <= maxi
            and not any(c in interdits or not 0x20 <= ord(c) <= 0x7E for c in v))


def nettoyer_storage_state(etat, modele: dict, maintenant: Optional[float] = None) -> Optional[dict]:
    """
    storage_state de Playwright reçu du poste de l'utilisateur -> état à écrire, ou None s'il
    est inutilisable. Garde les cookies du site (domaine du tracker et sous-domaines), donc
    les éventuels cookies secondaires de longue durée, et le localStorage de ses origines ;
    écarte les autres domaines, les cookies Cloudflare et tout cookie mal formé.
    Exige exactement un cookie de session, valide et non expiré, remis au gabarit du
    tracker (hôte, chemin /, Secure). Rien de ce qui est reçu n'est journalisé ni renvoyé.
    """
    if not isinstance(etat, dict):
        return None
    recus = etat.get("cookies")
    if not isinstance(recus, list) or len(recus) > MAX_COOKIES_RECUS:
        return None
    maintenant = time.time() if maintenant is None else maintenant
    site = _domaine_du_site(modele)
    session, cookies, vus = None, [], set()
    for c in recus:
        if not isinstance(c, dict) or not _dans_le_site(c.get("domain"), site):
            continue
        nom = c.get("name")
        if not _texte_de_cookie(nom, 256, ' "=;,\\', mini=1) or _cookie_cloudflare(nom):
            continue
        expire = c.get("expires")
        if isinstance(expire, bool) or not isinstance(expire, (int, float)) or expire <= 0:
            expire = -1  # cookie de session du navigateur
        if nom == modele["name"]:
            valeur = nettoyer_valeur_cookie(c.get("value"), nom)
            if valeur is None or session is not None or 0 < expire <= maintenant:
                return None
            if expire == -1:
                expire = int(maintenant) + int(modele.get("duree_jours", 7)) * 86400
            session = {"name": nom, "value": valeur, "domain": modele["domain"], "path": "/",
                       "expires": expire, "httpOnly": True, "secure": True,
                       "sameSite": c.get("sameSite") if c.get("sameSite") in ("Strict", "Lax", "None") else "Lax"}
            continue
        if 0 < expire <= maintenant or not _texte_de_cookie(c.get("value"), 4096, ";"):
            continue
        chemin = c.get("path")
        if not (_texte_de_cookie(chemin, 1024, ";", mini=1) and chemin.startswith("/")):
            chemin = "/"
        cle = (nom, c["domain"].lower(), chemin)
        if cle in vus:
            continue
        vus.add(cle)
        cookies.append({
            "name": nom, "value": c["value"], "domain": c["domain"].lower(),
            "path": chemin, "expires": expire, "httpOnly": c.get("httpOnly") is True, "secure": c.get("secure") is True,
            "sameSite": c.get("sameSite") if c.get("sameSite") in ("Strict", "Lax", "None") else "Lax",
        })
    if session is None or len(cookies) >= MAX_COOKIES_GARDES:
        return None

    origins, taille = [], 0
    recues = etat.get("origins")
    for o in recues if isinstance(recues, list) else []:
        if not isinstance(o, dict) or not isinstance(o.get("origin"), str):
            continue
        origine = o["origin"]
        if not origine.startswith("https://") or not _dans_le_site(origine[8:].split(":")[0].split("/")[0], site):
            continue
        entrees = [{"name": e["name"], "value": e["value"]} for e in (o.get("localStorage") or [])
                   if isinstance(e, dict) and isinstance(e.get("name"), str) and isinstance(e.get("value"), str)]
        taille += sum(len(e["name"]) + len(e["value"]) for e in entrees)
        if len(entrees) > MAX_ENTREES_LOCALSTORAGE or taille > MAX_TAILLE_LOCALSTORAGE:
            return None
        origins.append({"origin": origine, "localStorage": entrees})
    return {"cookies": cookies + [session], "origins": origins}


async def _signaler_echec(name: str, scraper, raison: str, maintenant: datetime) -> None:
    """Alerte d'echec : une au 3e echec consecutif, puis un rappel par 24 h."""
    sr = _scrape_results[name]
    decision = decider_alerte_echec(sr.consecutive_failures, sr.last_failure_alert_at, maintenant)
    if decision:
        await notify_scrape_failures(
            name, sr.consecutive_failures, raison,
            rappel=(decision == "rappel"), reconnexion=_reconnexion(scraper),
        )
        sr.last_failure_alert_at = maintenant


@router.post("/session/{tracker_name}", response_model=ScrapeStatus)
async def deposer_session(
    tracker_name: str,
    request: Request,
    user: TokenData = Depends(get_session_depositor),
):
    """
    Depose la session d'un tracker a connexion manuelle (C411, Ygg), ouverte par l'utilisateur
    lui-meme dans son navigateur. Deux corps acceptes, jamais les deux a la fois :
    - {"valeur": "..."} : valeur du cookie de session (ou « nom=valeur ») ;
    - {"storage_state": {...}} : etat complet de Playwright (context.storage_state()), qui
      garde aussi les cookies secondaires du site (voir nettoyer_storage_state).
    Ecrit le fichier de cookies puis lance un releve de controle.
    Jeton : celui de l'interface, ou SESSION_SYNC_TOKEN (jeton dedie a cette seule route).
    Rien de ce qui est recu n'est journalise ni renvoye (corps lu a la main : une erreur de
    validation automatique recopierait l'entree dans la reponse).
    """
    scraper = get_scraper(tracker_name)
    if not scraper or not scraper.SESSION_COOKIE:
        raise HTTPException(status_code=404, detail=f"Tracker '{tracker_name}' sans session manuelle")

    try:
        corps = await request.json()
    except Exception:
        corps = None
    if not isinstance(corps, dict):
        corps = {}
    if "storage_state" in corps:
        if "valeur" in corps:
            raise HTTPException(status_code=400, detail="Fournir « valeur » ou « storage_state », pas les deux")
        etat = nettoyer_storage_state(corps["storage_state"], scraper.SESSION_COOKIE)
        if etat is None:
            raise HTTPException(
                status_code=400, detail="storage_state mal forme, ou cookie de session absent, invalide ou expire")
        deposer, forme = (lambda: scraper.deposer_storage_state(etat)), f"storage_state, {len(etat['cookies'])} cookie(s)"
    else:
        valeur = nettoyer_valeur_cookie(corps.get("valeur"), scraper.SESSION_COOKIE["name"])
        if valeur is None:
            raise HTTPException(status_code=400, detail="Valeur de cookie vide ou mal formee")
        deposer, forme = (lambda: scraper.deposer_session(valeur)), "cookie seul"
    if _scraping_in_progress:
        raise HTTPException(status_code=409, detail="Un releve est en cours, reessayer dans une minute")

    try:
        deposer()
    except OSError:
        raise HTTPException(status_code=500, detail="Ecriture du fichier de session impossible")
    logger.info("[%s] Session deposee a la main par %s (%s, valeurs non journalisees)", tracker_name, user.sub, forme)

    if tracker_name not in _scrape_results:
        _scrape_results[tracker_name] = ScrapeResult(tracker_name=tracker_name, status="ok")
    sr = _scrape_results[tracker_name]
    sr.session_deposited_at = datetime.now(timezone.utc)
    sr.session_expiry_alert_at = None

    # Releve de controle (quelques secondes) : la reponse dit si le site accepte la session.
    await run_scraping_task(tracker_name=tracker_name)
    if sr.status == "ok":
        return ScrapeStatus(status="ok", message="Session acceptee, releve reussi", tracker=tracker_name)
    sr.session_deposited_at = None
    await _persist_scraper_state(tracker_name)
    return ScrapeStatus(
        status="refusee",
        message=f"Session refusee par le site ({sr.last_error or 'erreur inconnue'})",
        tracker=tracker_name,
    )


def _detect_parser_suspect(stats) -> tuple[bool, str]:
    """
    Heuristique : si points_bonus > 0 (page /tokens a repondu) mais que des champs
    stats principaux sont vides/zeros, c'est probablement que le parser /stats est HS
    (nouveau HTML du tracker). Sert a detecter les silent-break comme Torr9 04/2026.
    """
    try:
        points_val = int((stats.points_bonus or "0").replace(" ", ""))
    except (ValueError, AttributeError):
        points_val = 0
    if points_val <= 0:
        return False, ""
    broken = []
    if not stats.ratio or stats.ratio in ("0", ""):
        broken.append("ratio")
    if not stats.vol_upload or stats.vol_upload in ("0", ""):
        broken.append("vol_upload")
    if not stats.vol_download or stats.vol_download in ("0", ""):
        broken.append("vol_download")
    if not broken:
        return False, ""
    return True, f"points_bonus={points_val} mais champs vides : {', '.join(broken)}"


async def _scrape_single(name: str, scraper, browser) -> None:
    """Scrape un tracker et sauvegarde en DB."""
    now = datetime.now(timezone.utc)

    # Initialiser l'entree si elle n'existe pas encore
    if name not in _scrape_results:
        _scrape_results[name] = ScrapeResult(tracker_name=name, status="ok")

    _scrape_results[name].last_attempt_at = now

    try:
        logger.info("Demarrage: %s", name)
        stats = await scraper.run(browser)
        async with async_session() as db:
            saved = await save_stats_to_db(db, stats)

        if saved:
            prev_failures = _scrape_results[name].consecutive_failures
            _scrape_results[name].status = "ok"
            _scrape_results[name].last_success_at = now
            _scrape_results[name].consecutive_failures = 0
            _scrape_results[name].last_error = None
            logger.info("Termine: %s", name)

            # Notification: recovery apres echecs
            await notify_scrape_recovery(name, prev_failures)
            _scrape_results[name].last_failure_alert_at = None

            # Notification: ratio sous 0.85
            ratio_val = None
            if stats.ratio and stats.ratio != "0":
                try:
                    ratio_val = float(stats.ratio.replace(",", "."))
                except ValueError:
                    pass
            if ratio_val is not None and ratio_val < 0.85:
                await notify_ratio_critical(name, ratio_val)

            # Notification: avertissements actifs (H&R en cours uniquement,
            # on ignore le compteur historique `hit_and_run` qui garde les H&R expires)
            warnings_val = 0
            if stats.warnings_active and stats.warnings_active != "0":
                try:
                    warnings_val = int(stats.warnings_active.split()[0])
                except (ValueError, IndexError):
                    pass
            # Une alerte quand le compteur augmente (@here a partir de 2), puis un rappel
            # sans @here par 24 h tant qu'il reste 2 avertissements ou plus.
            prev_warnings = _scrape_results[name].last_known_active_warnings
            decision = decider_alerte_avertissements(
                warnings_val, prev_warnings, _scrape_results[name].last_warning_alert_at, now)
            if decision:
                detail = (stats.raw_data or {}).get("avertissements_detail") if isinstance(stats.raw_data, dict) else None
                await notify_avertissements(name, warnings_val, decision, detail)
                _scrape_results[name].last_warning_alert_at = now
            if warnings_val == 0:
                _scrape_results[name].last_warning_alert_at = None
            _scrape_results[name].last_known_active_warnings = warnings_val

            # Session manuelle a duree limitee : rappel avant l'echeance (une fois par session).
            if scraper.SESSION_COOKIE:
                sr = _scrape_results[name]
                expiration = scraper.expiration_session(sr.session_deposited_at)
                if session_bientot_expiree(expiration, sr.session_expiry_alert_at, now):
                    await notify_session_bientot_expiree(name, expiration, _reconnexion(scraper))
                    sr.session_expiry_alert_at = now

            # Notification: parser suspect (tokens OK mais champs stats vides)
            suspect, suspect_reason = _detect_parser_suspect(stats)
            if suspect and not _scrape_results[name].parser_suspect:
                await notify_parser_suspect(name, suspect_reason)
            _scrape_results[name].parser_suspect = suspect
        else:
            # save_stats_to_db a skippe (donnees en erreur)
            reason = (
                stats.raw_data.get("error", "unknown skip reason")
                if stats.raw_data and isinstance(stats.raw_data, dict)
                else "unknown skip reason"
            )
            _scrape_results[name].status = "skipped"
            _scrape_results[name].last_error = reason
            _scrape_results[name].consecutive_failures += 1
            logger.warning("Skippe: %s (%s)", name, reason)
            await _signaler_echec(name, scraper, reason, now)

    except Exception as e:
        _scrape_results[name].status = "error"
        _scrape_results[name].last_error = str(e)
        _scrape_results[name].consecutive_failures += 1
        logger.error("Erreur %s: %s", name, e)
        await _signaler_echec(name, scraper, str(e), now)

    # Persister l'etat (compteurs) pour survivre aux restart du container.
    await _persist_scraper_state(name)


async def run_scraping_task(db: AsyncSession = None, tracker_name: Optional[str] = None):
    """
    Tache de scraping (executee en arriere-plan).
    Tous les trackers sont scrapes en parallele.
    """
    global _scraping_in_progress
    _scraping_in_progress = True

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            scrapers = get_scrapers()
            if tracker_name:
                scrapers = {tracker_name: scrapers[tracker_name]}

            # Scraper tous les trackers en parallele
            tasks = [
                _scrape_single(name, scraper, browser)
                for name, scraper in scrapers.items()
            ]
            await asyncio.gather(*tasks)

            await browser.close()

    finally:
        _scraping_in_progress = False


async def save_stats_to_db(db: AsyncSession, stats: ScrapedStats) -> bool:
    """Sauvegarde les stats en base de donnees. Retourne True si sauvegarde, False si skippe."""
    try:
        # Ne pas sauvegarder les stats en erreur (login_failed, etc.)
        if stats.raw_data and isinstance(stats.raw_data, dict) and "error" in stats.raw_data:
            logger.warning("Skip sauvegarde %s: %s", stats.tracker_name, stats.raw_data["error"])
            return False

        # Ne pas sauvegarder les stats partielles (ex: Torr9 /stats en maintenance,
        # seuls les points bonus sont remplis, ratio/buffer/volumes sont a zero).
        # On garde les anciennes donnees completes en DB.
        if stats.raw_data and isinstance(stats.raw_data, dict) and stats.raw_data.get("stats_status") == "maintenance":
            logger.warning("Skip sauvegarde %s: stats partielles (maintenance), conservation des anciennes donnees", stats.tracker_name)
            return False

        # Convertir ratio en float si possible
        ratio_float = None
        if stats.ratio and stats.ratio != "0":
            try:
                ratio_float = float(stats.ratio.replace(",", "."))
            except:
                pass

        db_stats = TrackerStats(
            tracker_name=stats.tracker_name,
            ratio=ratio_float,
            buffer=stats.buffer,
            vol_upload=stats.vol_upload,
            vol_download=stats.vol_download,
            points_bonus=stats.points_bonus,
            fl_tokens=stats.fl_tokens,
            count_seed=stats.count_seed,
            count_leech=stats.count_leech,
            count_downloaded=stats.count_downloaded,
            seed_time_total=stats.seed_time_total,
            seed_time_avg=stats.seed_time_avg,
            warnings_active=stats.warnings_active,
            hit_and_run=stats.hit_and_run,
            raw_data=stats.raw_data,
            scraped_at=datetime.now(timezone.utc),
        )

        db.add(db_stats)
        await db.commit()
        return True

    except Exception as e:
        logger.error("Erreur sauvegarde DB: %s", e)
        await db.rollback()
        return False


@router.get("/status")
async def get_scraper_status(user: TokenData = Depends(get_current_user)):
    """Retourne le status du scraper. (Auth requise : erreurs et sites configures)"""
    tracker_status = {}
    for name, sr in _scrape_results.items():
        tracker_status[name] = {
            "status": sr.status,
            "last_success_at": sr.last_success_at.isoformat() if sr.last_success_at else None,
            "last_attempt_at": sr.last_attempt_at.isoformat() if sr.last_attempt_at else None,
            "last_error": sr.last_error,
            "consecutive_failures": sr.consecutive_failures,
        }

    return {
        "scraping_in_progress": _scraping_in_progress,
        "configured_scrapers": list_available_scrapers(),
        "tracker_status": tracker_status,
    }
