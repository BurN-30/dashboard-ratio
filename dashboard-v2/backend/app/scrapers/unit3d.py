"""
Scraper pour les trackers utilisant UNIT3D.
Compatible avec: Generation-Free, TheOldSchool, Torr9, Gemini-Tracker
"""
import logging
from typing import Optional
from playwright.async_api import Page

from app.scrapers.base import BaseScraper, ScraperConfig, ScrapedStats

logger = logging.getLogger("dashboard.scraper")


class Unit3DScraper(BaseScraper):
    """
    Scraper generique pour les trackers UNIT3D.
    UNIT3D est un framework PHP populaire pour les trackers privés.
    """

    async def login(self, page: Page) -> bool:
        """Login sur un tracker UNIT3D."""
        try:
            # Verifier si le formulaire de login est present
            if await page.locator('input[name="username"]').count() == 0:
                # Deja connecte ou page differente
                return True

            if not self.config.username or not self.config.password:
                logger.warning("[%s] Identifiants manquants", self.name)
                return False

            await page.fill('input[name="username"]', self.config.username)
            await page.fill('input[name="password"]', self.config.password)
            await page.press('input[name="password"]', 'Enter')
            await page.wait_for_load_state('networkidle', timeout=60000)

            return True

        except Exception as e:
            logger.error("[%s] Erreur login: %s", self.name, e)
            return False

    async def scrape(self, page: Page) -> ScrapedStats:
        """Scrape les stats d'un profil UNIT3D."""
        raw_data = {}

        # Helper pour extraire les valeurs des listes dt/dd
        async def get_value(label: str, exact: bool = False) -> str:
            try:
                if exact:
                    xpath = f'//dt[normalize-space(.)="{label}"]/following-sibling::dd'
                else:
                    xpath = f'//dt[contains(normalize-space(.), "{label}")]/following-sibling::dd'

                element = page.locator(xpath).first
                text = await element.inner_text(timeout=1000)
                return self.clean_text(text)
            except:
                return "0"

        # Avertissements
        warnings = await get_value("Avertissements actifs")
        hit_run = await get_value("Hit and Run Count")
        if hit_run == "0":
            hit_run = await get_value("Compteur de Hit and Run")

        # Temps de seed
        seed_total = self.format_duration(await get_value("Durée totale des seeds"))
        if seed_total == "0":
            seed_total = self.format_duration(await get_value("Temps de seed total"))

        seed_avg = self.format_duration(await get_value("Temps de seed moyen"))

        seed_size = await get_value("Seeding Size")
        if seed_size == "0":
            seed_size = await get_value("Volume de Seed")

        # Compteurs torrents
        count_dl = await get_value("Total des téléchargés")
        if count_dl == "0":
            count_dl = await get_value("Total complétés")

        count_seed = await get_value("Total en seed")
        count_leech = await get_value("Total en leech")

        # Traffic
        ratio = await get_value("Ratio")
        real_ratio = await get_value("Real Ratio")
        buffer = await get_value("Tampon")

        vol_up = await get_value("Compte Envoyer (Total)")
        if vol_up == "0":
            vol_up = await get_value("Compte Uploader (Total)")

        vol_dl = await get_value("Compte Télécharger (Total)")
        if vol_dl == "0":
            vol_dl = await get_value("Compte Télécharger")

        # Points / Recompenses
        points = await get_value("Coupon", exact=True)
        if points == "0" or points == "":
            points = await get_value("Point Bonus", exact=True)

        fl_tokens = await get_value("Jetons Freeleech")

        # Donnees brutes supplementaires
        raw_data = {
            "real_ratio": real_ratio,
            "seed_size": seed_size,
            "torrent_uploader": await get_value("Torrent Envoyer"),
            "torrent_downloader": await get_value("Torrent Télécharger"),
        }

        return ScrapedStats(
            tracker_name=self.name,
            ratio=ratio,
            buffer=buffer,
            vol_upload=vol_up,
            vol_download=vol_dl,
            points_bonus=points,
            fl_tokens=fl_tokens,
            count_seed=count_seed,
            count_leech=count_leech,
            count_downloaded=count_dl,
            seed_time_total=seed_total,
            seed_time_avg=seed_avg,
            warnings_active=warnings,
            hit_and_run=hit_run,
            raw_data=raw_data,
        )
