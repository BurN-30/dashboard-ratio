"""
Verification hebdomadaire des paliers bonus des trackers.
Scrape les pages boutique, compare avec les valeurs connues,
notifie Discord si un prix change.

Tourne 1x/semaine (mercredi 3h00 Europe/Paris), decale des scrapes
reguliers (8h/14h/20h) pour rester discret.
"""
import asyncio
import json
import logging
import os
from pathlib import Path

from playwright.async_api import async_playwright

from app.config import get_settings
from app.notifications import _send
from app.scrapers.boutique import parse_paliers_unit3d

logger = logging.getLogger("dashboard.bonus_checker")

TIERS_FILE = "/app/cookies/bonus_tiers.json"

# Pages boutique par tracker. Les UNIT3D utilisent /users/{username}/transactions/create.
# TR4KER (ex-Torr9) n'est pas suivi ici : sa boutique (/shop) n'a pas encore de parseur.
BONUS_PAGES = {
    "GF-FREE": "https://generation-free.org/users/{username}/transactions/create",
    "TOS": "https://theoldschool.cc/users/{username}/transactions/create",
    "G3MINI TR4CK3R": "https://gemini-tracker.org/users/{username}/transactions/create",
}

COOKIE_FILES = {
    "GF-FREE": "gf_free.json",
    "TOS": "tos.json",
    "G3MINI TR4CK3R": "g3mini_tr4ck3r.json",
}


def _load_saved_tiers() -> dict:
    """Charge les paliers sauvegardes."""
    if os.path.exists(TIERS_FILE):
        with open(TIERS_FILE) as f:
            return json.load(f)
    return {}


def _save_tiers(tiers: dict):
    """Sauvegarde les paliers."""
    with open(TIERS_FILE, "w") as f:
        json.dump(tiers, f, indent=2, ensure_ascii=False)


async def _scrape_tracker_tiers(name: str) -> list[dict] | None:
    """Lit les paliers d'un tracker UNIT3D. Retourne None en cas d'erreur."""
    from app.scrapers.registry import get_scraper

    settings = get_settings()
    url_template = BONUS_PAGES.get(name)
    if not url_template:
        return None
    username = {
        "GF-FREE": settings.gf_username,
        "TOS": settings.tos_username,
        "G3MINI TR4CK3R": settings.gemini_username,
    }.get(name) or ""
    url = url_template.format(username=username)
    cpath = f"/app/cookies/{COOKIE_FILES[name]}"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(storage_state=cpath if os.path.exists(cpath) else None)
            page = await ctx.new_page()
            page.set_default_timeout(30000)
            await page.goto(url, timeout=30000)

            # Cookies expires : connexion par le scraper du tracker (formulaire sans captcha),
            # sinon on abandonne (le releve suivant rafraichira les cookies).
            if "/login" in page.url:
                scraper = get_scraper(name)
                if scraper is None or not await scraper.login(page):
                    logger.warning("[bonus] %s: cookies expires et connexion impossible", name)
                    await browser.close()
                    return None
                await ctx.storage_state(path=cpath)
                await page.goto(url, timeout=30000)

            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            body = await page.locator("body").inner_text(timeout=10000)
            await browser.close()

        paliers = parse_paliers_unit3d(body)
        if not paliers:
            logger.warning("[bonus] %s: aucun palier lu (page changee ?)", name)
            return None
        return paliers

    except Exception as e:
        logger.error("[bonus] Erreur scrape %s: %s", name, e)
        return None


async def check_bonus_tiers():
    """
    Verifie les paliers de tous les trackers.
    Compare avec les valeurs sauvegardees, notifie si changement.
    """
    logger.info("[bonus] Debut de la verification hebdomadaire des paliers")
    saved = _load_saved_tiers()
    current = {}
    changes = []

    for name in BONUS_PAGES:
        logger.info("[bonus] Scrape %s...", name)
        tiers = await _scrape_tracker_tiers(name)

        if tiers is None:
            logger.warning("[bonus] %s: echec scrape, skip", name)
            continue

        current[name] = tiers

        # Comparer avec les valeurs sauvegardees
        old_tiers = saved.get(name, [])
        if old_tiers and tiers != old_tiers:
            changes.append(name)
            logger.info("[bonus] %s: paliers ont change!", name)

        # Pause entre chaque tracker (discret)
        await asyncio.sleep(8)

    # Sauvegarder les nouvelles valeurs
    if current:
        tous = {k: v for k, v in saved.items() if k != "Torr9"}
        tous.update(current)
        _save_tiers(tous)

    # Notifier les changements
    if changes:
        desc_parts = []
        for name in changes:
            old = saved.get(name, [])
            new = current.get(name, [])
            old_max = max((t["cost"] for t in old), default=0) if old else 0
            new_max = max((t["cost"] for t in new), default=0) if new else 0
            desc_parts.append(f"**{name}** : max tier {old_max:,} → {new_max:,}")

        await _send({
            "title": "Paliers bonus modifies",
            "description": "\n".join(desc_parts),
            "color": 0x3B82F6,
            "footer": {"text": "Estimation d'upload achetable mise a jour automatiquement"},
        })

    logger.info("[bonus] Verification terminee. %d changement(s) detecte(s).", len(changes))
    return current
