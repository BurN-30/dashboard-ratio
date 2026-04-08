"""
Classe de base abstraite pour tous les scrapers de trackers.
"""
import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from playwright.async_api import Page, Browser, BrowserContext
import re

logger = logging.getLogger("dashboard.scraper")

COOKIES_DIR = Path("/app/cookies") if os.path.isdir("/app") else Path("cookies")


@dataclass
class ScraperConfig:
    """Configuration d'un scraper."""
    name: str
    login_url: str
    profile_url_template: str  # Utilise {username} comme placeholder
    username: Optional[str] = None
    password: Optional[str] = None
    profile_username: Optional[str] = None  # Pour l'URL du profil


@dataclass
class ScrapedStats:
    """Statistiques scrapees d'un tracker."""
    tracker_name: str

    # Stats principales
    ratio: Optional[str] = None
    buffer: Optional[str] = None
    vol_upload: Optional[str] = None
    vol_download: Optional[str] = None

    # Stats secondaires
    points_bonus: Optional[str] = None
    fl_tokens: Optional[str] = None
    count_seed: Optional[str] = None
    count_leech: Optional[str] = None
    count_downloaded: Optional[str] = None
    seed_time_total: Optional[str] = None
    seed_time_avg: Optional[str] = None
    warnings_active: Optional[str] = None
    hit_and_run: Optional[str] = None

    # Donnees brutes
    raw_data: Optional[dict] = None


class BaseScraper(ABC):
    """
    Classe de base pour les scrapers de trackers torrent.
    Chaque tracker herite de cette classe et implemente ses specificites.
    """

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.name = config.name

    @property
    def profile_url(self) -> str:
        """Construit l'URL du profil utilisateur."""
        return self.config.profile_url_template.format(
            username=self.config.profile_username or self.config.username
        )

    @abstractmethod
    async def login(self, page: Page) -> bool:
        """
        Effectue le login sur le tracker.

        Args:
            page: Page Playwright

        Returns:
            True si le login a reussi, False sinon
        """
        pass

    @abstractmethod
    async def scrape(self, page: Page) -> ScrapedStats:
        """
        Scrape les statistiques du profil utilisateur.

        Args:
            page: Page Playwright (deja sur la page profil)

        Returns:
            ScrapedStats avec les donnees extraites
        """
        pass

    def _cookies_path(self) -> Path:
        """Chemin du fichier cookies pour ce tracker."""
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', self.name).lower()
        return COOKIES_DIR / f"{safe_name}.json"

    async def _save_cookies(self, context: BrowserContext) -> None:
        """Sauvegarde les cookies du context pour reutilisation."""
        try:
            COOKIES_DIR.mkdir(parents=True, exist_ok=True)
            state = await context.storage_state()
            self._cookies_path().write_text(json.dumps(state))
            logger.info("[%s] Cookies sauvegardes", self.name)
        except Exception as e:
            logger.warning("[%s] Impossible de sauvegarder les cookies: %s", self.name, e)

    async def _try_with_cookies(self, browser: Browser) -> Optional[ScrapedStats]:
        """Tente le scraping avec des cookies sauvegardes (skip login)."""
        cookies_path = self._cookies_path()
        if not cookies_path.exists():
            return None

        try:
            state = json.loads(cookies_path.read_text())
            context = await browser.new_context(storage_state=state)
            page = await context.new_page()
            page.set_default_timeout(60000)

            try:
                logger.info("[%s] Tentative avec cookies sauvegardes", self.name)
                await page.goto(self.profile_url, timeout=90000)
                await page.wait_for_load_state("networkidle", timeout=30000)

                # Si on est redirige vers /login, les cookies sont expires
                if "/login" in page.url:
                    logger.info("[%s] Cookies expires, suppression", self.name)
                    cookies_path.unlink(missing_ok=True)
                    return None

                stats = await self.scrape(page)
                # Rafraichir les cookies apres usage reussi
                await self._save_cookies(context)
                logger.info("[%s] Scraping termine (via cookies)", self.name)
                return stats
            finally:
                await context.close()

        except Exception as e:
            logger.warning("[%s] Erreur avec cookies: %s", self.name, e)
            cookies_path.unlink(missing_ok=True)
            return None

    async def run(self, browser: Browser) -> ScrapedStats:
        """
        Execute le scraping complet.
        Tente d'abord avec des cookies sauvegardes, puis login classique.
        """
        # Essayer avec les cookies sauvegardes
        result = await self._try_with_cookies(browser)
        if result is not None:
            return result

        # Login classique
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(60000)

        try:
            logger.info("[%s] Navigation vers %s", self.name, self.config.login_url)
            await page.goto(self.config.login_url, timeout=90000)

            if not await self.login(page):
                logger.warning("[%s] Echec du login", self.name)
                return ScrapedStats(tracker_name=self.name, raw_data={"error": "login_failed"})

            # Sauvegarder les cookies apres login reussi
            await self._save_cookies(context)

            # Navigation vers le profil
            logger.info("[%s] Navigation vers %s", self.name, self.profile_url)
            await page.goto(self.profile_url, timeout=90000)
            await page.wait_for_load_state("networkidle", timeout=30000)

            # Scrape
            stats = await self.scrape(page)
            logger.info("[%s] Scraping termine", self.name)
            return stats

        except Exception as e:
            logger.error("[%s] Erreur: %s", self.name, e)
            return ScrapedStats(tracker_name=self.name, raw_data={"error": str(e)})

        finally:
            await context.close()

    # === UTILS ===

    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        """Nettoie un texte (espaces, retours ligne, unites)."""
        if not text:
            return "0"

        text = text.replace('\xa0', ' ').replace('\u202f', ' ')
        text = text.strip().replace('\n', ' ')

        # Conversion des unites (Anglais -> Francais)
        replacements = {
            "TiB": "To", "GiB": "Go", "MiB": "Mo", "KiB": "Ko",
            "TB": "To", "GB": "Go", "MB": "Mo", "KB": "Ko",
        }
        for eng, fr in replacements.items():
            text = text.replace(eng, fr)

        if text.endswith(" B"):
            text = text[:-1] + "o"

        # "0 o" ou "0 Go" etc. quand la valeur est juste zero
        if re.match(r'^0\s*[A-Za-z]*o$', text):
            return "0"

        return text

    @staticmethod
    def format_duration(text: Optional[str]) -> str:
        """Formate une duree en abbreviations courtes."""
        if not text or text == "0":
            return "0"

        # D'abord remplacer les mots francais complets par des abbreviations
        word_replacements = [
            (r'années?', 'a'),
            (r'an\(s\)', 'a'),
            (r'ans?', 'a'),
            (r'mois', 'mo'),
            (r'semaines?', 'sem'),
            (r'jours?', 'j'),
            (r'heures?', 'h'),
            (r'minutes?', 'min'),
            (r'secondes?', 's'),
        ]
        for pattern, replacement in word_replacements:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Ajouter espaces entre chiffres et lettres
        text = re.sub(r'(\d+)([a-zA-Z]+)', r'\1 \2', text)
        text = re.sub(r'([a-zA-Z]+)(\d+)', r'\1 \2', text)
        text = re.sub(r'\s+', ' ', text).strip()

        # Remplacements d'unites courtes (Y, M, D, H, etc.)
        replacements = [
            (r'\b(\d+)\s*[Yy]\b', r'\1a'),
            (r'\b(\d+)\s*M\b', r'\1mo'),
            (r'\b(\d+)\s*[Ww]\b', r'\1sem'),
            (r'\b(\d+)\s*S\b', r'\1sem'),
            (r'\b(\d+)\s*[Dd]\b', r'\1j'),
            (r'\b(\d+)\s*[Jj]\b', r'\1j'),
            (r'\b(\d+)\s*[Hh]\b', r'\1h'),
            (r'\b(\d+)\s*m\b', r'\1min'),
            (r'\b(\d+)\s*s\b', r'\1s'),
        ]

        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text)

        # Format compact uniforme: "34a 7mo 3sem 1j 10h 28min 54s"
        text = re.sub(r'(\d+)\s+([a-zA-Z]+)', r'\1\2', text)
        text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
        text = re.sub(r'\s+', ' ', text).strip()

        # Tronquer aux segments significatifs
        # Avec annees → 2 segments, sinon → 3 segments
        segments = text.split()
        if segments and 'a' in segments[0]:
            segments = segments[:2]
        else:
            segments = segments[:3]

        return ' '.join(segments)
