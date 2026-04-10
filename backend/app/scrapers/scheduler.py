"""
Planificateur de scraping automatique.
- Scrapes reguliers : 8h, 14h, 20h (Europe/Paris)
- Check bonus tiers : mercredi 3h00 (1x/semaine)
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta, time as dt_time
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

from app.scrapers.registry import get_scrapers
from app.scrapers.routes import _scrape_single

logger = logging.getLogger("dashboard.scheduler")

# Taches asyncio globales
_scheduler_task: asyncio.Task | None = None
_bonus_task: asyncio.Task | None = None

# Heures de scraping (Europe/Paris)
SCRAPE_TIMES = [dt_time(8, 0), dt_time(14, 0), dt_time(20, 0)]
BONUS_CHECK_DAY = 2  # Mercredi (0=lundi)
BONUS_CHECK_TIME = dt_time(3, 0)
TZ = ZoneInfo("Europe/Paris")


def _seconds_until_next_run() -> float:
    """Calcule le nombre de secondes avant le prochain horaire de scraping."""
    now = datetime.now(TZ)
    today = now.date()

    # Chercher le prochain horaire aujourd'hui ou demain
    for t in SCRAPE_TIMES:
        candidate = datetime.combine(today, t, tzinfo=TZ)
        if candidate > now:
            delta = (candidate - now).total_seconds()
            return delta

    # Tous les horaires d'aujourd'hui sont passes -> premier horaire demain
    tomorrow = today + timedelta(days=1)
    candidate = datetime.combine(tomorrow, SCRAPE_TIMES[0], tzinfo=TZ)
    return (candidate - now).total_seconds()


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

            # Scraper tous les trackers en parallele
            tasks = [
                _scrape_single(name, scraper, browser)
                for name, scraper in scrapers.items()
            ]
            await asyncio.gather(*tasks)

            await browser.close()

    except Exception as e:
        logger.error("Erreur globale scraping automatique: %s", e)

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info("Scraping automatique termine en %.1fs", elapsed)


async def _scheduler_loop():
    """Boucle principale du planificateur a heures fixes."""

    logger.info(
        "Planificateur demarre: scraping a %s (Europe/Paris)",
        ", ".join(t.strftime("%Hh%M") for t in SCRAPE_TIMES),
    )

    # Attendre un peu au demarrage pour laisser l'app s'initialiser
    await asyncio.sleep(30)

    while True:
        wait = _seconds_until_next_run()
        next_run = datetime.now(TZ) + timedelta(seconds=wait)
        logger.info(
            "Prochain scraping dans %.0f min (%s)",
            wait / 60,
            next_run.strftime("%H:%M"),
        )

        try:
            await asyncio.sleep(wait)
        except asyncio.CancelledError:
            logger.info("Planificateur arrete pendant l'attente")
            break

        try:
            await _run_scheduled_scrape()
        except asyncio.CancelledError:
            logger.info("Planificateur arrete")
            break
        except Exception as e:
            logger.error("Erreur inattendue dans le planificateur: %s", e)


def _seconds_until_next_bonus_check() -> float:
    """Calcule les secondes avant le prochain mercredi 3h00."""
    now = datetime.now(TZ)
    days_ahead = BONUS_CHECK_DAY - now.weekday()
    if days_ahead < 0 or (days_ahead == 0 and now.time() >= BONUS_CHECK_TIME):
        days_ahead += 7
    target = datetime.combine(now.date() + timedelta(days=days_ahead), BONUS_CHECK_TIME, tzinfo=TZ)
    return (target - now).total_seconds()


async def _bonus_check_loop():
    """Boucle hebdomadaire pour verifier les paliers bonus."""
    from app.scrapers.bonus_checker import check_bonus_tiers

    logger.info("Bonus checker demarre: mercredi 3h00 (Europe/Paris)")
    await asyncio.sleep(60)  # Laisser l'app demarrer

    while True:
        wait = _seconds_until_next_bonus_check()
        next_run = datetime.now(TZ) + timedelta(seconds=wait)
        logger.info("Prochain check bonus dans %.0fh (%s)", wait / 3600, next_run.strftime("%a %d/%m %H:%M"))

        try:
            await asyncio.sleep(wait)
        except asyncio.CancelledError:
            break

        try:
            await check_bonus_tiers()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Erreur bonus checker: %s", e)


def start_scheduler():
    """Demarre le planificateur en arriere-plan."""
    global _scheduler_task, _bonus_task

    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_scheduler_loop())
        logger.info("Tache du planificateur creee")

    if _bonus_task is None or _bonus_task.done():
        _bonus_task = asyncio.create_task(_bonus_check_loop())
        logger.info("Tache bonus checker creee")


def stop_scheduler():
    """Arrete le planificateur."""
    global _scheduler_task, _bonus_task
    for task in (_scheduler_task, _bonus_task):
        if task and not task.done():
            task.cancel()
    _scheduler_task = None
    _bonus_task = None
    logger.info("Planificateurs arretes")
