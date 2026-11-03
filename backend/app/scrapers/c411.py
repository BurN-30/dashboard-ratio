"""
Scraper pour C411 (c411.org, application Nuxt).

Notes :
- Connexion protegee par un captcha Cloudflare (Turnstile) : jamais de connexion
  automatique. Le scraper reutilise la session ouverte a la main par l'utilisateur
  (cookies/c411.json, cookie __Host-c411_session), rafraichie a chaque releve.
- Donnees lues par l'API JSON du site (03/11/2026) :
  GET /api/auth/me        -> user.uploaded, downloaded, uploadCredit, ratio, warnings, ratioWarning
  GET /api/tokens/balance -> balance (Zen)
  GET /shop (HTML)        -> charge utile Nuxt (__NUXT_DATA__) : articles « go_credit »
                             (5 Go, 50 Go, 1 To, 10 To ; 1 Zen le Go au 03/11/2026)
- Session expiree (401 ou authenticated=false) -> erreur explicite, cookies supprimes.
  Une panne reseau ne supprime rien.
"""
import json
import logging
import re
from typing import Optional

from playwright.async_api import Browser, Page

from app.scrapers.base import BaseScraper, ScrapedStats
from app.scrapers.boutique import enregistrer_paliers

logger = logging.getLogger("dashboard.scraper")

BASE_URL = "https://c411.org"
ME_API = f"{BASE_URL}/api/auth/me"
BALANCE_API = f"{BASE_URL}/api/tokens/balance"
SHOP_URL = f"{BASE_URL}/shop"


def format_octets(n: float) -> str:
    signe = "-" if n < 0 else ""
    n = abs(n)
    for seuil, unite in ((1e12, "To"), (1e9, "Go"), (1e6, "Mo")):
        if n >= seuil:
            return f"{signe}{n / seuil:.2f} {unite}"
    return f"{signe}{n / 1e3:.2f} Ko" if n else "0"


def parse_me(me: dict, balance: Optional[dict]) -> dict:
    """Reponses /api/auth/me et /api/tokens/balance -> champs ScrapedStats."""
    user = (me or {}).get("user")
    if not me.get("authenticated") or not isinstance(user, dict):
        raise PermissionError("session C411 expiree")
    if "uploaded" not in user or "downloaded" not in user:
        raise ValueError("reponse /api/auth/me sans uploaded/downloaded")
    up, down = float(user.get("uploaded") or 0), float(user.get("downloaded") or 0)
    ratio = user.get("ratio")
    if not isinstance(ratio, (int, float)):
        ratio = up / down if down else 999
    zen = (balance or {}).get("balance")
    return {
        "ratio": f"{ratio:.2f}",
        "buffer": format_octets(up - down),
        "vol_upload": format_octets(up),
        "vol_download": format_octets(down),
        "points_bonus": f"{int(zen):,}".replace(",", " ") if isinstance(zen, (int, float)) else "0",
        "warnings_active": str(int(user.get("warnings") or 0) + (1 if user.get("ratioWarning") else 0)),
        "raw_data": {
            "credit_upload": format_octets(float(user.get("uploadCredit") or 0)),
            "credit_download": format_octets(float(user.get("downloadCredit") or 0)),
            "ratio_min_dl": str(user.get("minRatioForDownload") or ""),
            "peut_telecharger": bool(user.get("canDownload")),
        },
    }


def paliers_boutique(html: str) -> list[dict]:
    """Page /shop -> paliers d'upload [{"gib", "cost"}] lus dans la charge utile Nuxt."""
    m = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return []
    a = json.loads(m.group(1))

    def val(i):
        v = a[i] if isinstance(i, int) and not isinstance(i, bool) and 0 <= i < len(a) else i
        if isinstance(v, list) and v and v[0] in ("Reactive", "ShallowReactive", "Ref", "ShallowRef"):
            return val(v[1])
        return v

    paliers = []
    for x in a:
        if not (isinstance(x, dict) and "price" in x and "category" in x and "payload" in x):
            continue
        if val(x["category"]) != "go_credit":
            continue
        prix, charge = val(x["price"]), val(x["payload"])
        octets = val(charge.get("bytes")) if isinstance(charge, dict) else None
        if isinstance(prix, (int, float)) and prix > 0 and isinstance(octets, (int, float)) and octets > 0:
            paliers.append({"gib": octets / 1024 ** 3, "cost": int(prix)})
    return paliers


class C411Scraper(BaseScraper):
    """C411 : API JSON avec la session de l'utilisateur (jamais de connexion automatique)."""

    async def login(self, page: Page) -> bool:
        return False  # captcha a la connexion : jamais automatique

    async def scrape(self, page: Page) -> ScrapedStats:
        req = page.context.request
        r = await req.get(ME_API, timeout=30000)
        if r.status in (401, 403):
            raise PermissionError("session C411 expiree")
        if not r.ok:
            raise RuntimeError(f"api_auth_me_http_{r.status}")
        me = await r.json()
        rb = await req.get(BALANCE_API, timeout=30000)
        balance = await rb.json() if rb.ok else None
        champs = parse_me(me, balance)

        try:
            rs = await req.get(SHOP_URL, timeout=30000)
            if rs.ok:
                enregistrer_paliers(self.name, paliers_boutique(await rs.text()))
        except Exception as e:
            logger.warning("[%s] Boutique illisible : %s", self.name, e)

        raw = champs.pop("raw_data")
        stats = ScrapedStats(tracker_name=self.name, fl_tokens="0", count_seed=None, count_leech=None,
                             hit_and_run="0", raw_data=raw, **champs)
        logger.info("[%s] Scraping termine (ratio=%s, upload=%s)", self.name, stats.ratio, stats.vol_upload)
        return stats

    async def run(self, browser: Browser) -> ScrapedStats:
        chemin = self._cookies_path()
        if not chemin.exists():
            return ScrapedStats(tracker_name=self.name, raw_data={"error": "session_absente_reconnexion_manuelle"})
        context = await browser.new_context(storage_state=str(chemin))
        page = await context.new_page()
        try:
            stats = await self.scrape(page)
            await self._save_cookies(context)
            return stats
        except PermissionError:
            logger.warning("[%s] Session expiree : reconnexion manuelle necessaire (captcha)", self.name)
            chemin.unlink(missing_ok=True)
            return ScrapedStats(tracker_name=self.name, raw_data={"error": "session_expiree_reconnexion_manuelle"})
        except Exception as e:
            logger.error("[%s] Erreur: %s", self.name, e)
            return ScrapedStats(tracker_name=self.name, raw_data={"error": str(e)[:200]})
        finally:
            await context.close()
