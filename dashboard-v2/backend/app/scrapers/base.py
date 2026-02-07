"""
Classe de base abstraite pour tous les scrapers de trackers.
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass
from playwright.async_api import Page, Browser
import re

logger = logging.getLogger("dashboard.scraper")


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

    async def run(self, browser: Browser) -> ScrapedStats:
        """
        Execute le scraping complet (login + scrape).

        Args:
            browser: Instance Browser Playwright

        Returns:
            ScrapedStats ou None en cas d'erreur
        """
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(60000)

        try:
            # Login
            logger.info("[%s] Navigation vers %s", self.name, self.config.login_url)
            await page.goto(self.config.login_url, timeout=90000)

            if not await self.login(page):
                logger.warning("[%s] Echec du login", self.name)
                return ScrapedStats(tracker_name=self.name, raw_data={"error": "login_failed"})

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

        return text

    @staticmethod
    def format_duration(text: Optional[str]) -> str:
        """Formate une duree en francais."""
        if not text or text == "0":
            return "0"

        # Ajouter espaces entre chiffres et lettres
        text = re.sub(r'(\d+)([a-zA-Z]+)', r'\1 \2', text)
        text = re.sub(r'([a-zA-Z]+)(\d+)', r'\1 \2', text)
        text = text.replace("  ", " ").strip()

        # Remplacements d'unites
        replacements = [
            (r'\b(\d+)\s*[Yy]\b', r'\1 an(s)'),
            (r'\b(\d+)\s*M\b', r'\1 mois'),
            (r'\b(\d+)\s*[Ww]\b', r'\1 sem'),
            (r'\b(\d+)\s*S\b', r'\1 sem'),
            (r'\b(\d+)\s*[Dd]\b', r'\1 j'),
            (r'\b(\d+)\s*[Jj]\b', r'\1 j'),
            (r'\b(\d+)\s*[Hh]\b', r'\1 h'),
            (r'\b(\d+)\s*m\b', r'\1 min'),
            (r'\b(\d+)\s*s\b', r'\1 s'),
        ]

        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text)

        return text
