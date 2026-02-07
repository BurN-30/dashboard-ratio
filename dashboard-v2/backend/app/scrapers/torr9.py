"""
Scraper specifique pour Torr9.xyz
Torr9 est un site Next.js custom (PAS UNIT3D).
Les stats sont sur /stats, les tokens sur /tokens.
Pas de structure dt/dd — tout est en texte dans des divs.
"""
import logging
import re
from playwright.async_api import Page, Browser

from app.scrapers.base import BaseScraper, ScraperConfig, ScrapedStats

logger = logging.getLogger("dashboard.scraper")


class Torr9Scraper(BaseScraper):
    """Scraper pour Torr9.xyz (Next.js custom)."""

    async def login(self, page: Page) -> bool:
        """Login sur Torr9."""
        try:
            if await page.locator('input[name="username"]').count() == 0:
                return True

            if not self.config.username or not self.config.password:
                logger.warning("[%s] Identifiants manquants", self.name)
                return False

            await page.fill('input[name="username"]', self.config.username)
            await page.fill('input[name="password"]', self.config.password)

            submit = page.locator('button[type="submit"]')
            if await submit.count() > 0:
                await submit.click()
            else:
                await page.press('input[name="password"]', 'Enter')

            try:
                await page.wait_for_load_state('networkidle', timeout=30000)
            except:
                pass

            if '/login' in page.url:
                logger.warning("[%s] Login echoue (toujours sur /login)", self.name)
                return False

            return True

        except Exception as e:
            logger.error("[%s] Erreur login: %s", self.name, e)
            return False

    async def scrape(self, page: Page) -> ScrapedStats:
        """Scrape les stats Torr9 depuis /stats et /tokens."""
        return await self._scrape_stats(page)

    async def run(self, browser: Browser) -> ScrapedStats:
        """Override run() car Torr9 n'a pas de page profil standard."""
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

            # Scrape /stats
            logger.info("[%s] Navigation vers /stats", self.name)
            await page.goto("https://torr9.xyz/stats", timeout=60000)
            try:
                await page.wait_for_load_state('networkidle', timeout=15000)
            except:
                pass

            stats = await self._scrape_stats(page)

            # Scrape /tokens pour le solde
            logger.info("[%s] Navigation vers /tokens", self.name)
            await page.goto("https://torr9.xyz/tokens", timeout=60000)
            try:
                await page.wait_for_load_state('networkidle', timeout=15000)
            except:
                pass

            tokens = await self._scrape_tokens(page)
            stats.fl_tokens = tokens

            logger.info("[%s] Scraping termine", self.name)
            return stats

        except Exception as e:
            logger.error("[%s] Erreur: %s", self.name, e)
            return ScrapedStats(tracker_name=self.name, raw_data={"error": str(e)})

        finally:
            await context.close()

    async def _scrape_stats(self, page: Page) -> ScrapedStats:
        """Parse la page /stats de Torr9."""
        raw_data = {}

        try:
            body = await page.locator('body').inner_text(timeout=10000)
        except:
            return ScrapedStats(tracker_name=self.name, raw_data={"error": "page_empty"})

        lines = [l.strip() for l in body.split('\n') if l.strip()]

        def find_value_after(keyword: str) -> str:
            """Trouve la valeur sur la ligne suivant un keyword."""
            keyword_lower = keyword.lower()
            for i, line in enumerate(lines):
                line_lower = line.lower().strip()
                # Match exact ou en debut de ligne (evite "en seed" dans "temps de seed")
                if line_lower == keyword_lower or line_lower.startswith(keyword_lower):
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        # Verifier que la ligne suivante ressemble a une valeur (pas un label)
                        if next_line and (re.search(r'\d', next_line) or next_line.lower() in ('n/a', '-')):
                            return next_line
            return "0"

        def find_value_on_line(keyword: str) -> str:
            """Trouve la valeur sur la meme ligne qu'un keyword."""
            keyword_lower = keyword.lower()
            for line in lines:
                if keyword_lower in line.lower():
                    # Extraire les nombres de la ligne
                    nums = re.findall(r'[\d,.]+', line)
                    if nums:
                        return nums[-1]
            return "0"

        # Upload / Download totaux
        vol_upload = find_value_after("upload total")
        vol_download = find_value_after("download total")

        # Ratio
        ratio = find_value_after("ratio actuel")
        if ratio == "0":
            ratio = find_value_after("ratio")

        # Compteurs
        count_uploaded = find_value_after("torrents upload")
        count_completed = find_value_after("torrents compl")
        count_seed = find_value_after("en seed")

        # Temps de seed
        seed_total = find_value_after("temps de seed total")
        if seed_total and seed_total != "0":
            seed_total = self.format_duration(seed_total)

        # Buffer = upload - download (calculer si possible)
        buffer = self._compute_buffer(vol_upload, vol_download)

        raw_data = {
            "count_uploaded_torrents": count_uploaded,
        }

        return ScrapedStats(
            tracker_name=self.name,
            ratio=ratio,
            buffer=buffer,
            vol_upload=vol_upload,
            vol_download=vol_download,
            points_bonus="0",
            fl_tokens="0",
            count_seed=count_seed,
            count_leech="0",
            count_downloaded=count_completed,
            seed_time_total=seed_total,
            seed_time_avg="0",
            warnings_active="0",
            hit_and_run="0",
            raw_data=raw_data,
        )

    async def _scrape_tokens(self, page: Page) -> str:
        """Parse la page /tokens pour le solde."""
        try:
            body = await page.locator('body').inner_text(timeout=10000)
            lines = [l.strip() for l in body.split('\n') if l.strip()]

            for i, line in enumerate(lines):
                lower = line.lower()
                if "solde actuel" in lower or "balance" in lower or "token" in lower:
                    # Chercher un nombre sur cette ligne ou la suivante
                    nums = re.findall(r'(\d+)', line)
                    if nums:
                        return nums[0]
                    if i + 1 < len(lines):
                        nums = re.findall(r'(\d+)', lines[i + 1])
                        if nums:
                            return nums[0]
        except Exception as e:
            logger.warning("[%s] Erreur scrape tokens: %s", self.name, e)

        return "0"

    @staticmethod
    def _compute_buffer(upload_str: str, download_str: str) -> str:
        """Calcule le buffer (upload - download) a partir des strings."""
        try:
            def parse_size(s: str) -> float:
                """Parse '50.0 GB' en bytes."""
                s = s.strip()
                match = re.match(r'([\d,.]+)\s*(To|Go|Mo|Ko|TB|GB|MB|KB|TiB|GiB|MiB|KiB)', s, re.IGNORECASE)
                if not match:
                    return 0
                val = float(match.group(1).replace(',', '.'))
                unit = match.group(2).upper()
                multipliers = {
                    'TO': 1e12, 'TB': 1e12, 'TIB': 1e12,
                    'GO': 1e9, 'GB': 1e9, 'GIB': 1e9,
                    'MO': 1e6, 'MB': 1e6, 'MIB': 1e6,
                    'KO': 1e3, 'KB': 1e3, 'KIB': 1e3,
                }
                return val * multipliers.get(unit, 1)

            def format_size(bytes_val: float) -> str:
                """Formate des bytes en string lisible."""
                if abs(bytes_val) >= 1e12:
                    return f"{bytes_val / 1e12:.2f} To"
                elif abs(bytes_val) >= 1e9:
                    return f"{bytes_val / 1e9:.2f} Go"
                elif abs(bytes_val) >= 1e6:
                    return f"{bytes_val / 1e6:.2f} Mo"
                else:
                    return f"{bytes_val / 1e3:.2f} Ko"

            up = parse_size(upload_str)
            dl = parse_size(download_str)
            if up > 0 or dl > 0:
                return format_size(up - dl)
        except:
            pass
        return "0"
