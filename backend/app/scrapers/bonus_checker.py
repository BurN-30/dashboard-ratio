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

logger = logging.getLogger("dashboard.bonus_checker")

TIERS_FILE = "/app/cookies/bonus_tiers.json"

# Pages boutique par tracker. Les UNIT3D utilisent /users/{username}/transactions/create.
# Torr9 utilise /tokens.
BONUS_PAGES = {
    "GF-FREE": "https://generation-free.org/users/{username}/transactions/create",
    "TOS": "https://theoldschool.cc/users/{username}/transactions/create",
    "G3MINI TR4CK3R": "https://gemini-tracker.org/users/{username}/transactions/create",
    "Torr9": "https://torr9.net/tokens",
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


def _parse_unit3d_tiers(body: str) -> list[dict]:
    """Parse les tiers d'une page UNIT3D transactions/create."""
    tiers = []
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        # Pattern: "500 GiB Upload" suivi d'un nombre (cout)
        if "Upload" in line and ("GiB" in line or "TiB" in line):
            label = line
            # Le cout est sur la ligne suivante ou precedente
            if i + 1 < len(lines):
                try:
                    cost = int(lines[i + 1].replace(",", "").replace(" ", ""))
                    tiers.append({"label": label, "cost": cost})
                    i += 2
                    continue
                except ValueError:
                    pass
        i += 1
    return tiers


def _parse_torr9_tiers(body: str) -> list[dict]:
    """Parse les tiers de la page /tokens de Torr9."""
    tiers = []
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if "Upload" in line and ("Go" in line or "To" in line):
            label = line
            # Chercher le cout dans les lignes suivantes
            for j in range(i + 1, min(i + 5, len(lines))):
                try:
                    cost = int(lines[j].replace(",", "").replace(" ", ""))
                    tiers.append({"label": label, "cost": cost})
                    break
                except ValueError:
                    continue
            i += 1
            continue
        i += 1
    return tiers


async def _scrape_tracker_tiers(name: str) -> list[dict] | None:
    """Scrape les tiers d'un tracker. Retourne None en cas d'erreur."""
    settings = get_settings()
    url_template = BONUS_PAGES.get(name)
    if not url_template:
        return None

    # Construire l'URL
    username = ""
    if name == "GF-FREE":
        username = settings.gf_username or ""
    elif name == "TOS":
        username = settings.tos_username or ""
    elif name == "G3MINI TR4CK3R":
        username = settings.gemini_username or ""
    url = url_template.format(username=username)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            # Cookies ou login
            cookie_file = COOKIE_FILES.get(name)
            if cookie_file:
                cpath = f"/app/cookies/{cookie_file}"
                if not os.path.exists(cpath):
                    logger.warning("[bonus] %s: pas de cookies", name)
                    await browser.close()
                    return None
                ctx = await browser.new_context(storage_state=cpath)
            else:
                # Torr9: login
                ctx = await browser.new_context()
                page = await ctx.new_page()
                page.set_default_timeout(30000)
                await page.goto("https://torr9.net/login", timeout=30000)
                await asyncio.sleep(3)
                u_input = page.locator('input[name="username"]')
                if await u_input.count() > 0:
                    await page.fill('input[name="username"]', settings.torr9_user or "")
                    await page.fill('input[name="password"]', settings.torr9_pass or "")
                    submit = page.locator('button[type="submit"]')
                    if await submit.count() > 0:
                        await submit.first.click()
                    await asyncio.sleep(4)
                await page.close()

            page = await ctx.new_page()
            page.set_default_timeout(30000)
            await page.goto(url, timeout=30000)
            await asyncio.sleep(4)
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except:
                pass

            body = await page.locator("body").inner_text(timeout=10000)
            await ctx.close()
            await browser.close()

        if name == "Torr9":
            return _parse_torr9_tiers(body)
        else:
            return _parse_unit3d_tiers(body)

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
        _save_tiers(current)

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
            "footer": {"text": "Verifier les valeurs MAX_REDEEM dans le frontend"},
        })

    logger.info("[bonus] Verification terminee. %d changement(s) detecte(s).", len(changes))
    return current
