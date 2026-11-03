"""
Scraper specifique pour TR4KER (ex-Torr9).

Notes :
- Torr9 (torr9.xyz puis torr9.net) est devenu TR4KER (tr4ker.net) durant l'ete 2026 :
  torr9.net redirige vers tr4ker.net et les comptes ont ete migres. L'ancien scraper
  lisait des pages qui n'existent plus et enregistrait des zeros sans erreur
  (10/08/2026 -> 03/11/2026).
- Site SPA (Vite/React). On se connecte par le formulaire (champs `identifier` et
  `password`), puis on lit l'API JSON du site avec les cookies de la session :
  GET /api/me/stats -> summary (uploaded, downloaded, bonus_upload, bonus_download,
  money, ratio_warning) + statistics (torrents_seeding, torrents_completed,
  total_seedtime_seconds, uploaded_last_24h/7d/30d, downloaded_last_24h/7d/30d).
- Ratio affiche par le site = (uploaded + bonus_upload) / (downloaded + bonus_download)
  (lu dans le code du site le 03/11/2026).
- Toute reponse inattendue renvoie une erreur explicite : plus jamais de zeros muets.
- Les identifiants restent dans TORR9_USER / TORR9_PASS (meme compte, migre).
"""
import logging
from typing import Optional

from playwright.async_api import Browser, Page

from app.scrapers.base import BaseScraper, ScrapedStats

logger = logging.getLogger("dashboard.scraper")

BASE_URL = "https://tr4ker.net"
LOGIN_URL = f"{BASE_URL}/login"
STATS_API = f"{BASE_URL}/api/me/stats"


def format_bytes(n: float) -> str:
    """Octets -> texte court en unites decimales, comme les autres trackers ('4.41 To')."""
    signe = "-" if n < 0 else ""
    n = abs(n)
    for seuil, unite in ((1e12, "To"), (1e9, "Go"), (1e6, "Mo")):
        if n >= seuil:
            return f"{signe}{n / seuil:.2f} {unite}"
    return f"{signe}{n / 1e3:.2f} Ko" if n else "0"


def format_seedtime(secondes: Optional[float]) -> str:
    """Secondes -> 'Xa Ymo' (ou 'Yj Zh' si moins d'un mois), meme style que les UNIT3D."""
    if not secondes or secondes <= 0:
        return "0"
    jours = int(secondes // 86400)
    annees, reste = divmod(jours, 365)
    mois = reste // 30
    if annees:
        return f"{annees}a {mois}mo" if mois else f"{annees}a"
    if mois:
        return f"{mois}mo {reste % 30}j"
    return f"{jours}j {int(secondes % 86400 // 3600)}h"


def parse_stats(payload: dict) -> dict:
    """
    Transforme la reponse de /api/me/stats en champs ScrapedStats.
    Leve ValueError si la structure attendue manque (changement d'API).
    """
    summary = payload.get("summary")
    statistics = payload.get("statistics") or {}
    if not isinstance(summary, dict) or "uploaded" not in summary or "downloaded" not in summary:
        raise ValueError("reponse /api/me/stats sans summary.uploaded/downloaded")

    up = float(summary.get("uploaded") or 0) + float(summary.get("bonus_upload") or 0)
    down = float(summary.get("downloaded") or 0) + float(summary.get("bonus_download") or 0)
    if up <= 0 and down <= 0:
        raise ValueError("upload et download a zero (compte vide ou API changee)")
    ratio = f"{up / down:.2f}" if down > 0 else "999"

    def entier(cle: str) -> str:
        v = statistics.get(cle)
        return str(int(v)) if isinstance(v, (int, float)) else "0"

    def volume(cle: str) -> str:
        v = statistics.get(cle)
        return format_bytes(float(v)) if isinstance(v, (int, float)) else "0"

    return {
        "ratio": ratio,
        "buffer": format_bytes(up - down),
        "vol_upload": format_bytes(up),
        "vol_download": format_bytes(down),
        "points_bonus": f"{int(summary.get('money') or 0):,}".replace(",", " "),
        "count_seed": entier("torrents_seeding"),
        "count_downloaded": entier("torrents_completed"),
        "seed_time_total": format_seedtime(statistics.get("total_seedtime_seconds")),
        "warnings_active": "1" if summary.get("ratio_warning") else "0",
        "raw_data": {
            "upload_bonus": format_bytes(float(summary.get("bonus_upload") or 0)),
            "download_bonus": format_bytes(float(summary.get("bonus_download") or 0)),
            "upload_reel": format_bytes(float(summary.get("uploaded") or 0)),
            "download_reel": format_bytes(float(summary.get("downloaded") or 0)),
            "upload_24h": volume("uploaded_last_24h"),
            "upload_7j": volume("uploaded_last_7d"),
            "upload_30j": volume("uploaded_last_30d"),
            "download_24h": volume("downloaded_last_24h"),
            "download_7j": volume("downloaded_last_7d"),
            "download_30j": volume("downloaded_last_30d"),
            "ratio_warning": bool(summary.get("ratio_warning")),
        },
    }


class Tr4kerScraper(BaseScraper):
    """Scraper pour TR4KER : login par formulaire, puis API JSON /api/me/stats."""

    async def login(self, page: Page) -> bool:
        try:
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass

            if not self.config.username or not self.config.password:
                logger.warning("[%s] Identifiants manquants", self.name)
                return False

            ident = page.locator('input[name="identifier"]')
            mdp = page.locator('input[name="password"]')
            if await ident.count() == 0 or await mdp.count() == 0:
                # Ne plus supposer « deja connecte » : c'est ce qui masquait la panne de 2026.
                logger.warning("[%s] Formulaire de connexion introuvable sur %s", self.name, page.url)
                return False

            await ident.fill(self.config.username)
            await mdp.fill(self.config.password)
            bouton = page.locator('button[type="submit"]')
            async with page.expect_response(lambda r: "/api/auth/login" in r.url, timeout=30000) as info:
                if await bouton.count() > 0:
                    await bouton.first.click()
                else:
                    await mdp.press("Enter")
            reponse = await info.value
            if not reponse.ok:
                # 429 = trop de connexions recentes (blocage de quelques minutes cote site)
                logger.warning("[%s] Connexion refusee par le site (HTTP %s)", self.name, reponse.status)
                self.derniere_erreur = f"login_http_{reponse.status}"
                return False
            await page.wait_for_timeout(1500)
            return True
        except Exception as e:
            logger.error("[%s] Erreur login: %s", self.name, e)
            return False

    async def scrape(self, page: Page) -> ScrapedStats:
        """Lit /api/me/stats avec les cookies de la page connectee."""
        # La session est posee quelques secondes apres le clic : on reessaie jusqu'a ~15 s.
        for _ in range(10):
            r = await page.context.request.get(STATS_API, timeout=30000)
            if r.status not in (401, 403):
                break
            await page.wait_for_timeout(1500)
        if r.status == 401 or r.status == 403:
            return ScrapedStats(tracker_name=self.name, raw_data={"error": "login_failed"})
        if not r.ok:
            return ScrapedStats(tracker_name=self.name, raw_data={"error": f"api_me_stats_http_{r.status}"})
        try:
            champs = parse_stats(await r.json())
        except Exception as e:
            return ScrapedStats(tracker_name=self.name, raw_data={"error": f"api_me_stats_illisible: {e}"[:200]})
        raw = champs.pop("raw_data")
        stats = ScrapedStats(tracker_name=self.name, fl_tokens="0", count_leech="0",
                             seed_time_avg=None, hit_and_run="0", raw_data=raw, **champs)
        logger.info("[%s] Scraping termine (ratio=%s, upload=%s)", self.name, stats.ratio, stats.vol_upload)
        return stats

    async def run(self, browser: Browser) -> ScrapedStats:
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(60000)
        try:
            logger.info("[%s] Navigation vers %s", self.name, LOGIN_URL)
            await page.goto(LOGIN_URL, timeout=90000)
            self.derniere_erreur = "login_failed"
            if not await self.login(page):
                return ScrapedStats(tracker_name=self.name, raw_data={"error": self.derniere_erreur})
            return await self.scrape(page)
        except Exception as e:
            logger.error("[%s] Erreur: %s", self.name, e)
            return ScrapedStats(tracker_name=self.name, raw_data={"error": str(e)[:200]})
        finally:
            await context.close()
