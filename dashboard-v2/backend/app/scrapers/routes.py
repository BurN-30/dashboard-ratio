"""
Routes API pour les scrapers.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from playwright.async_api import async_playwright

logger = logging.getLogger("dashboard.scraper")

from app.auth.jwt import get_current_user, TokenData
from app.db.database import async_session
from app.db.models import TrackerStats
from app.scrapers.registry import (
    get_scrapers,
    get_scraper,
    list_available_scrapers,
    list_all_sites,
)
from app.scrapers.base import ScrapedStats

router = APIRouter()

# Flag pour eviter les scrapes simultanees
_scraping_in_progress = False


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
    try:
        logger.info("Demarrage: %s", name)
        stats = await scraper.run(browser)
        async with async_session() as db:
            await save_stats_to_db(db, stats)
        logger.info("Termine: %s", name)
    except Exception as e:
        logger.error("Erreur %s: %s", name, e)


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


async def save_stats_to_db(db: AsyncSession, stats: ScrapedStats):
    """Sauvegarde les stats en base de donnees."""
    try:
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

    except Exception as e:
        logger.error("Erreur sauvegarde DB: %s", e)
        await db.rollback()


@router.get("/status")
async def get_scraper_status():
    """Retourne le status du scraper."""
    return {
        "scraping_in_progress": _scraping_in_progress,
        "configured_scrapers": list_available_scrapers(),
    }
