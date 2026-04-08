"""
Scraper pour les trackers utilisant UNIT3D.
Compatible avec: Generation-Free, TheOldSchool, Gemini-Tracker
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

        async def get_first_value(*labels: str, exact: bool = False) -> str:
            """Essaye plusieurs labels et retourne le premier resultat non-nul."""
            for label in labels:
                val = await get_value(label, exact=exact)
                if val and val != "0":
                    return val
            return "0"

        # Avertissements
        warnings = await get_first_value(
            "Avertissements actifs", "Active Warnings",
        )

        # Hit & Run (& et and)
        hit_run = await get_first_value(
            "Hit and Run Count", "Hit & Run",
            "Compteur de Hit and Run", "Compteur de Hit & Run",
        )

        # Temps de seed
        seed_total = self.format_duration(await get_first_value(
            "Durée totale des seeds", "Temps de seed total",
            "Total Seedtime", "Total Seed Time",
        ))

        seed_avg = self.format_duration(await get_first_value(
            "Temps de seed moyen", "Average Seedtime", "Avg Seed Time",
        ))

        seed_size = await get_first_value(
            "Seeding Size", "Volume de Seed", "Taille de seed",
        )

        # Compteurs torrents
        count_dl = await get_first_value(
            "Total des téléchargés", "Total complétés",
            "Total Downloaded", "Total Completed",
        )

        count_seed = await get_first_value(
            "Total en seed", "Total Seeding",
        )

        count_leech = await get_first_value(
            "Total en leech", "Total Leeching",
        )

        # Traffic
        ratio = await get_first_value("Ratio")
        real_ratio = await get_first_value("Real Ratio", "Vrai Ratio")

        buffer = await get_first_value("Tampon", "Buffer")

        vol_up = await get_first_value(
            "Compte Envoyer (Total)", "Compte Uploader (Total)",
            "Upload (Total)", "Uploaded (Total)",
        )

        vol_dl = await get_first_value(
            "Compte Télécharger (Total)", "Compte Télécharger",
            "Download (Total)", "Downloaded (Total)",
        )

        # Points / Recompenses — exact match d'abord pour eviter de matcher
        # "Point Bonus Uploader" (volume) au lieu de "Point Bonus" (points)
        points = await get_value("BON", exact=True)
        if points == "0":
            points = await get_value("Point Bonus", exact=True)
        if points == "0":
            points = await get_value("Coupon", exact=True)
        if points == "0":
            points = await get_value("G3M", exact=True)
        if points == "0":
            points = await get_first_value(
                "Bonus Points", "Points Bonus",
            )

        fl_tokens = await get_first_value(
            "Jetons Freeleech", "Freeleech Tokens", "FL Tokens",
        )

        # Donnees brutes supplementaires
        torrent_up = await get_first_value(
            "Torrent Envoyer", "Torrent Uploaded",
        )
        torrent_up_credited = await get_first_value(
            "Torrent Envoyer (crédité)", "Torrent Uploaded (credited)",
        )
        torrent_dl = await get_first_value(
            "Torrent Télécharger", "Torrent Downloaded",
        )

        raw_data = {
            "real_ratio": real_ratio,
            "seed_size": seed_size,
            "torrent_uploader": torrent_up,
            "torrent_uploader_credited": torrent_up_credited,
            "torrent_downloader": torrent_dl,
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
