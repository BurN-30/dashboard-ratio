"""
Scraper specifique pour Sharewood.tv
Sharewood utilise une structure HTML differente des trackers UNIT3D.
"""
import logging
from playwright.async_api import Page

from app.scrapers.base import BaseScraper, ScraperConfig, ScrapedStats

logger = logging.getLogger("dashboard.scraper")


class SharewoodScraper(BaseScraper):
    """Scraper pour Sharewood.tv"""

    async def login(self, page: Page) -> bool:
        """Login sur Sharewood."""
        try:
            if await page.locator('input[name="username"]').count() == 0:
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
        """Scrape les stats Sharewood."""
        raw_data = {}

        async def safe_text(selector: str, xpath: bool = False) -> str:
            try:
                if xpath:
                    text = await page.inner_text(selector, timeout=2000)
                else:
                    text = await page.locator(selector).first.inner_text(timeout=2000)
                return self.clean_text(text)
            except:
                return "0"

        async def extract_table_value(label: str) -> str:
            """Extrait une valeur d'un tableau Sharewood."""
            try:
                xpath = f'//tr[td[strong[contains(text(), "{label}")]]]/td[2]'
                return self.clean_text(await page.inner_text(xpath, timeout=2000))
            except:
                return "0"

        # 1. BARRE DU HAUT - Compteurs
        try:
            count_dl_text = await safe_text('//span[contains(., "Total downloads")]', xpath=True)
            count_dl = count_dl_text.split(':')[-1].strip() if ':' in count_dl_text else "0"
        except:
            count_dl = "0"

        try:
            count_seed_text = await safe_text('//span[contains(., "Total en seed")]', xpath=True)
            count_seed = count_seed_text.split(':')[-1].strip() if ':' in count_seed_text else "0"
        except:
            count_seed = "0"

        try:
            count_leech_text = await safe_text('//span[contains(., "Total en leech")]', xpath=True)
            count_leech = count_leech_text.split(':')[-1].strip() if ':' in count_leech_text else "0"
        except:
            count_leech = "0"

        # 2. TABLEAU PRINCIPAL
        vol_download = await safe_text('span[data-original-title="Téléchargé"]')

        try:
            vol_upload = await safe_text('span[data-original-title="Upload enregistré"]')
        except:
            vol_upload = await extract_table_value("Upload")

        ratio = await extract_table_value("Ratio")
        buffer = await extract_table_value("Capacité de DL")

        seed_total = self.format_duration(await extract_table_value("Temps total de seed"))
        seed_avg = self.format_duration(await extract_table_value("Temps de seed moyen"))

        # 3. SECTION EXTRA
        try:
            points_text = await safe_text('//strong[contains(., "Bonus")]/following-sibling::span', xpath=True)
            points_bonus = points_text
        except:
            points_bonus = "0"

        try:
            fl_text = await safe_text('//strong[contains(., "Jetons FL")]/following-sibling::span', xpath=True)
            fl_tokens = fl_text
        except:
            fl_tokens = "0"

        try:
            hnr_text = await safe_text('//strong[contains(., "Hit&Run")]/following-sibling::span', xpath=True)
            hit_and_run = hnr_text
        except:
            hit_and_run = "0"

        # Warnings
        warnings = "0"
        try:
            warnings_text = await safe_text('//span[contains(., "Avertissements en cours")]', xpath=True)
            parts = warnings_text.split(":")[-1].strip().split("/")
            warnings = parts[0].strip()
            raw_data["warnings_limit"] = parts[1].strip() if len(parts) > 1 else "3"
        except:
            pass

        return ScrapedStats(
            tracker_name=self.name,
            ratio=ratio,
            buffer=buffer,
            vol_upload=vol_upload,
            vol_download=vol_download,
            points_bonus=points_bonus,
            fl_tokens=fl_tokens,
            count_seed=count_seed,
            count_leech=count_leech,
            count_downloaded=count_dl,
            seed_time_total=seed_total,
            seed_time_avg=seed_avg,
            warnings_active=warnings,
            hit_and_run=hit_and_run,
            raw_data=raw_data,
        )
