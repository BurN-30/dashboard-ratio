"""
Scraper pour YggReborn (www.yggreborn.org).

Notes :
- La connexion est protegee par un captcha Cloudflare (Turnstile) : le scraper ne se
  connecte jamais lui-meme. Il reutilise les cookies d'une session ouverte a la main
  par l'utilisateur (cookies/ygg.json, avec « se souvenir de moi »), rafraichis a chaque releve.
  Session expiree -> erreur explicite, a refaire a la main.
- Page /account/ (lue le 03/11/2026) : chaque valeur precede son intitule
  (« 164.06 Go » puis « UPLOAD », « 0.91 » puis « RATIO », « — » puis « SCORE »).
- Pas de compteur de torrents en seed sur cette page.
"""
import logging
import re
from typing import Optional

from playwright.async_api import Browser, Page

from app.scrapers.base import BaseScraper, ScrapedStats

logger = logging.getLogger("dashboard.scraper")

BASE_URL = "https://www.yggreborn.org"
ACCOUNT_URL = f"{BASE_URL}/account/"

_UNITES = {"o": 1, "ko": 1e3, "mo": 1e6, "go": 1e9, "to": 1e12, "kio": 1024, "mio": 1024 ** 2,
           "gio": 1024 ** 3, "tio": 1024 ** 4}


def taille_en_octets(texte: str) -> Optional[float]:
    m = re.match(r"\s*(-?\d+(?:[.,]\d+)?)\s*([kmgt]?i?o)\b", texte or "", re.I)
    if not m:
        return None
    return float(m.group(1).replace(",", ".")) * _UNITES[m.group(2).lower()]


def format_octets(n: float) -> str:
    signe = "-" if n < 0 else ""
    n = abs(n)
    for seuil, unite in ((1e12, "To"), (1e9, "Go"), (1e6, "Mo")):
        if n >= seuil:
            return f"{signe}{n / seuil:.2f} {unite}"
    return f"{signe}{n / 1e3:.2f} Ko" if n else "0"


def parse_compte(texte: str) -> dict:
    """Texte de /account/ -> champs ScrapedStats. ValueError si la page a change."""
    lignes = [l.strip() for l in texte.split("\n") if l.strip()]

    def avant(intitule: str) -> Optional[str]:
        for i, l in enumerate(lignes):
            if l.upper() == intitule and i > 0:
                return lignes[i - 1]
        return None

    up, down, ratio = avant("UPLOAD"), avant("DOWNLOAD"), avant("RATIO")
    o_up, o_down = taille_en_octets(up), taille_en_octets(down)
    if o_up is None or o_down is None or not ratio or not re.match(r"^\d+(?:[.,]\d+)?$|^∞$", ratio):
        raise ValueError("page /account/ sans UPLOAD/DOWNLOAD/RATIO lisibles")

    score = avant("SCORE")
    points = re.sub(r"[^\d]", "", score or "")
    return {
        "ratio": ratio.replace(",", ".").replace("∞", "999"),
        "buffer": format_octets(o_up - o_down),
        "vol_upload": format_octets(o_up),
        "vol_download": format_octets(o_down),
        "points_bonus": f"{int(points):,}".replace(",", " ") if points else "0",
        "raw_data": {
            "freeleech_dl": avant("FREELEECH DL") or "0",
            "uploads": avant("UPLOADS") or "0",
        },
    }


class YggScraper(BaseScraper):
    """YggReborn : lecture de /account/ avec la session de l'utilisateur (jamais de connexion auto)."""

    async def login(self, page: Page) -> bool:
        # Captcha a la connexion : pas de connexion automatique, par principe.
        return False

    async def scrape(self, page: Page) -> ScrapedStats:
        if "/account" not in page.url:
            await page.goto(ACCOUNT_URL, timeout=90000)
        texte = await page.inner_text("body")
        champs = parse_compte(texte)  # ValueError -> geree par _try_with_cookies (cookies supprimes)
        raw = champs.pop("raw_data")
        stats = ScrapedStats(tracker_name=self.name, fl_tokens="0", count_seed=None, count_leech=None,
                             warnings_active="0", hit_and_run="0", raw_data=raw, **champs)
        logger.info("[%s] Scraping termine (ratio=%s, upload=%s)", self.name, stats.ratio, stats.vol_upload)
        return stats

    async def run(self, browser: Browser) -> ScrapedStats:
        """
        Comme BaseScraper._try_with_cookies, mais les cookies ne sont supprimes que si le
        site redemande la connexion : une panne reseau ou une page changee ne doit pas
        obliger l'utilisateur a refaire une connexion manuelle.
        """
        chemin = self._cookies_path()
        if not chemin.exists():
            return ScrapedStats(tracker_name=self.name, raw_data={"error": "session_absente_reconnexion_manuelle"})
        context = await browser.new_context(storage_state=str(chemin))
        page = await context.new_page()
        page.set_default_timeout(60000)
        try:
            await page.goto(ACCOUNT_URL, timeout=90000)
            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                pass
            if "/login" in page.url:
                logger.warning("[%s] Session expiree : reconnexion manuelle necessaire (captcha)", self.name)
                chemin.unlink(missing_ok=True)
                return ScrapedStats(tracker_name=self.name, raw_data={"error": "session_expiree_reconnexion_manuelle"})
            stats = await self.scrape(page)
            await self._save_cookies(context)
            return stats
        except Exception as e:
            logger.error("[%s] Erreur: %s", self.name, e)
            return ScrapedStats(tracker_name=self.name, raw_data={"error": str(e)[:200]})
        finally:
            await context.close()
