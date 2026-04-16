"""
Routes API pour les scrapers.
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from playwright.async_api import async_playwright

logger = logging.getLogger("dashboard.scraper")

from app.auth.jwt import get_current_user, TokenData
from app.db.database import async_session
from app.db.models import TrackerStats, ScraperState
from app.scrapers.registry import (
    get_scrapers,
    get_scraper,
    list_available_scrapers,
    list_all_sites,
)
from app.scrapers.base import ScrapedStats
from app.notifications import (
    notify_scrape_failures, notify_scrape_recovery,
    notify_ratio_critical, notify_hit_and_run, notify_hit_and_run_critical,
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
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["tracker_name"],
                set_={
                    "consecutive_failures": stmt.excluded.consecutive_failures,
                    "last_success_at": stmt.excluded.last_success_at,
                    "last_known_active_warnings": stmt.excluded.last_known_active_warnings,
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
async def get_sites():
    """Liste tous les sites supportes."""
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
            prev_warnings = _scrape_results[name].last_known_active_warnings
            if warnings_val > prev_warnings:
                await notify_hit_and_run(name, warnings_val)
            if warnings_val >= 2:
                await notify_hit_and_run_critical(name, warnings_val)
            _scrape_results[name].last_known_active_warnings = warnings_val
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
            await notify_scrape_failures(name, _scrape_results[name].consecutive_failures, reason)

    except Exception as e:
        _scrape_results[name].status = "error"
        _scrape_results[name].last_error = str(e)
        _scrape_results[name].consecutive_failures += 1
        logger.error("Erreur %s: %s", name, e)
        await notify_scrape_failures(name, _scrape_results[name].consecutive_failures, str(e))

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
async def get_scraper_status():
    """Retourne le status du scraper."""
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
