"""
Planificateur de scraping automatique.
Execute les scrapers a intervalle regulier en arriere-plan.
"""
import asyncio
import logging
from datetime import datetime, timezone

from playwright.async_api import async_playwright

from app.config import get_settings
from app.db.database import async_session
from app.scrapers.registry import get_scrapers
from app.scrapers.routes import save_stats_to_db

logger = logging.getLogger("dashboard.scheduler")

# Tache asyncio globale
_scheduler_task: asyncio.Task | None = None


async def _run_scheduled_scrape():
    """Execute un cycle de scraping pour tous les trackers configures."""
    scrapers = get_scrapers()
    if not scrapers:
        logger.warning("Aucun scraper configure, scraping automatique ignore")
        return

    logger.info("Scraping automatique demarre pour %d tracker(s)", len(scrapers))
    start = datetime.now(timezone.utc)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            for name, scraper in scrapers.items():
                try:
                    logger.info("[Auto] Scraping: %s", name)
                    stats = await scraper.run(browser)

                    async with async_session() as db:
                        await save_stats_to_db(db, stats)

                    logger.info("[Auto] OK: %s", name)
                except Exception as e:
                    logger.error("[Auto] Erreur %s: %s", name, e)

            await browser.close()

    except Exception as e:
        logger.error("Erreur globale scraping automatique: %s", e)

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info("Scraping automatique termine en %.1fs", elapsed)


async def _scheduler_loop():
    """Boucle principale du planificateur."""
    settings = get_settings()
    interval = settings.scrape_interval

    if interval <= 0:
        logger.info("Scraping automatique desactive (SCRAPE_INTERVAL=%d)", interval)
        return

    logger.info(
        "Planificateur demarre: scraping toutes les %d secondes (%d min)",
        interval, interval // 60
    )

    # Attendre un peu au demarrage pour laisser l'app s'initialiser
    await asyncio.sleep(30)

    while True:
        try:
            await _run_scheduled_scrape()
        except asyncio.CancelledError:
            logger.info("Planificateur arrete")
            break
        except Exception as e:
            logger.error("Erreur inattendue dans le planificateur: %s", e)

        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("Planificateur arrete pendant l'attente")
            break


def start_scheduler():
    """Demarre le planificateur en arriere-plan."""
    global _scheduler_task
    if _scheduler_task is not None and not _scheduler_task.done():
        logger.warning("Planificateur deja en cours")
        return

    _scheduler_task = asyncio.create_task(_scheduler_loop())
    logger.info("Tache du planificateur creee")


def stop_scheduler():
    """Arrete le planificateur."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        logger.info("Planificateur annule")
    _scheduler_task = None
