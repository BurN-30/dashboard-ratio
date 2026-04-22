"""
Scraper specifique pour Torr9.

Notes :
- Le tracker a migre de torr9.xyz vers torr9.net en avril 2026.
- Site Next.js custom (PAS UNIT3D), parsing texte sans dt/dd.
- /stats peut etre temporairement en maintenance : on degrade gracieusement
  en mettant les champs concernes a "0", mais on continue a essayer /tokens
  pour le solde de points bonus.
- La page /stats a ete refondue le 22/04/2026 : labels en majuscules
  (UPLOAD TOTAL, DOWNLOAD TOTAL, RATIO, SEEDTIME, UPLOADÉS, COMPLÉTÉS, EN SEED)
  et les compteurs (uploaded/completed/seed) ont maintenant leur valeur APRES
  le label au lieu d'avant. Les valeurs utilisent une espace fine comme
  separateur de milliers (ex "2 010").
"""
import logging
import re
from playwright.async_api import Page, Browser

from app.scrapers.base import BaseScraper, ScraperConfig, ScrapedStats

logger = logging.getLogger("dashboard.scraper")

BASE_URL = "https://torr9.net"
STATS_URL = f"{BASE_URL}/stats"
TOKENS_URL = f"{BASE_URL}/tokens"


class Torr9Scraper(BaseScraper):
    """Scraper pour Torr9 (Next.js custom)."""

    async def login(self, page: Page) -> bool:
        """Login sur Torr9 (Next.js SPA)."""
        try:
            try:
                await page.wait_for_load_state('networkidle', timeout=15000)
            except:
                pass

            if not self.config.username or not self.config.password:
                logger.warning("[%s] Identifiants manquants", self.name)
                return False

            username_input = page.locator('input[name="username"]')
            password_input = page.locator('input[name="password"]')

            if await username_input.count() == 0 or await password_input.count() == 0:
                logger.info("[%s] Pas de formulaire, deja connecte", self.name)
                return True

            await page.fill('input[name="username"]', self.config.username)
            await page.fill('input[name="password"]', self.config.password)

            submit = page.locator('button[type="submit"]')
            if await submit.count() > 0:
                await submit.first.click()
            else:
                await password_input.press('Enter')

            await page.wait_for_timeout(3000)
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except:
                pass

            # Verifier qu'on n'est plus sur /login (signal de login OK).
            # On evite de naviguer vers /stats explicitement car il peut etre en maintenance.
            if '/login' in page.url:
                logger.warning("[%s] Login echoue (toujours sur /login)", self.name)
                return False

            logger.info("[%s] Login reussi", self.name)
            return True

        except Exception as e:
            logger.error("[%s] Erreur login: %s", self.name, e)
            return False

    async def scrape(self, page: Page) -> ScrapedStats:
        """Methode appelee par BaseScraper.run() (cookies path). Voir aussi run() override."""
        return await self._gather(page)

    async def run(self, browser: Browser) -> ScrapedStats:
        """Override : Torr9 n'a pas de page profil standard, on enchaine login + stats + tokens."""
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(60000)

        try:
            logger.info("[%s] Navigation vers %s", self.name, self.config.login_url)
            await page.goto(self.config.login_url, timeout=90000)

            if not await self.login(page):
                return ScrapedStats(tracker_name=self.name, raw_data={"error": "login_failed"})

            return await self._gather(page)

        except Exception as e:
            logger.error("[%s] Erreur: %s", self.name, e)
            return ScrapedStats(tracker_name=self.name, raw_data={"error": str(e)})

        finally:
            await context.close()

    async def _gather(self, page: Page) -> ScrapedStats:
        """
        Recupere stats + tokens, avec degradation gracieuse si l'un des deux echoue.
        On veut au minimum les points bonus si /stats est en maintenance.
        """
        stats: ScrapedStats = ScrapedStats(tracker_name=self.name, raw_data={})
        stats_ok = False
        tokens_value = "0"

        # 1. /stats (peut etre en maintenance, on ne plante pas)
        try:
            logger.info("[%s] Navigation vers %s", self.name, STATS_URL)
            await page.goto(STATS_URL, timeout=60000)
            try:
                await page.wait_for_load_state('networkidle', timeout=10000)
            except:
                pass

            if await self._is_maintenance(page):
                logger.warning("[%s] /stats en maintenance, skip", self.name)
                stats.raw_data["stats_status"] = "maintenance"
            else:
                parsed = await self._scrape_stats(page)
                # Conserver le tracker_name et raw_data accumule
                parsed.tracker_name = self.name
                if parsed.raw_data is None:
                    parsed.raw_data = {}
                parsed.raw_data.update(stats.raw_data)
                stats = parsed
                stats_ok = True
        except Exception as e:
            logger.warning("[%s] Erreur scrape /stats : %s", self.name, e)
            stats.raw_data["stats_status"] = "error"
            stats.raw_data["stats_error"] = str(e)[:200]

        # 2. /tokens (independant, on essaye toujours)
        try:
            logger.info("[%s] Navigation vers %s", self.name, TOKENS_URL)
            await page.goto(TOKENS_URL, timeout=60000)
            try:
                await page.wait_for_load_state('networkidle', timeout=15000)
            except:
                pass

            if await self._is_maintenance(page):
                logger.warning("[%s] /tokens en maintenance, skip", self.name)
            else:
                tokens_value = await self._scrape_tokens(page)
                stats.points_bonus = tokens_value
        except Exception as e:
            logger.warning("[%s] Erreur scrape /tokens : %s", self.name, e)

        # Si on n'a rien obtenu du tout, on renvoie un error pour ne pas polluer la DB
        if not stats_ok and tokens_value == "0":
            logger.warning("[%s] Ni stats ni tokens disponibles, abandon", self.name)
            return ScrapedStats(
                tracker_name=self.name,
                raw_data={"error": "all_endpoints_unavailable"}
            )

        logger.info(
            "[%s] Scraping termine (stats_ok=%s, points_bonus=%s)",
            self.name, stats_ok, stats.points_bonus or "0"
        )
        return stats

    async def _is_maintenance(self, page: Page) -> bool:
        """Heuristique pour detecter une page de maintenance Torr9."""
        try:
            body = await page.locator('body').inner_text(timeout=5000)
            text = body.lower()
            keywords = ["maintenance", "indisponible", "temporairement", "503"]
            return any(k in text for k in keywords) and len(text) < 500
        except:
            return False

    async def _scrape_stats(self, page: Page) -> ScrapedStats:
        """Parse la page /stats de Torr9."""
        raw_data = {}

        try:
            body = await page.locator('body').inner_text(timeout=10000)
        except:
            return ScrapedStats(tracker_name=self.name, raw_data={"error": "page_empty"})

        lines = [l.strip() for l in body.split('\n') if l.strip()]

        def find_value_after(keyword: str) -> str:
            """Trouve la valeur sur la ligne SUIVANT un keyword."""
            keyword_lower = keyword.lower()
            for i, line in enumerate(lines):
                if line.lower() == keyword_lower:
                    if i + 1 < len(lines):
                        return lines[i + 1].strip()
            return "0"

        def clean_count(value: str) -> str:
            """Normalise un compteur numerique ('2 010' ou '2 010' -> '2010')."""
            v = value.replace('\xa0', '').replace(' ', '').replace(' ', '').strip()
            return v if re.match(r'^\d+$', v) else "0"

        def find_index(keyword: str) -> int:
            keyword_lower = keyword.lower()
            for i, line in enumerate(lines):
                if line.lower() == keyword_lower:
                    return i
            return -1

        def parse_volume_block(label: str) -> tuple[str, str, str, str, str]:
            """
            Parse un bloc volume (UPLOAD TOTAL ou DOWNLOAD TOTAL) :
              LABEL / total / dont X bonus / 24h / Xh / 7j / Xj / 30j / Xj
            Retourne (total, dont_bonus, 24h, 7j, 30j). '0' pour les manquants.
            """
            idx = find_index(label)
            if idx < 0:
                return "0", "0", "0", "0", "0"
            total = lines[idx + 1] if idx + 1 < len(lines) else "0"
            dont_bonus = "0"
            d24, d7, d30 = "0", "0", "0"
            # Stopper au prochain gros label pour ne pas deborder sur un autre bloc.
            stop_labels = {"upload total", "download total", "seedtime", "rang", "streak", "activité", "chat", "commentaires", "uploadés", "complétés", "en seed"}
            end = min(idx + 12, len(lines))
            for j in range(idx + 2, end):
                l = lines[j]
                low = l.lower()
                if low in stop_labels:
                    break
                if dont_bonus == "0" and low.startswith("dont ") and "bonus" in low:
                    m = re.search(r'dont\s+([\d.,]+\s*[a-zA-Z]+)\s+bonus', l, re.IGNORECASE)
                    if m:
                        dont_bonus = m.group(1)
                elif low == "24h" and j + 1 < len(lines):
                    d24 = lines[j + 1]
                elif low == "7j" and j + 1 < len(lines):
                    d7 = lines[j + 1]
                elif low == "30j" and j + 1 < len(lines):
                    d30 = lines[j + 1]
            return total, dont_bonus, d24, d7, d30

        # Upload / Download totaux (+ dont_bonus + deltas 24h/7j/30j)
        vol_upload, upload_bonus, up24, up7, up30 = parse_volume_block("upload total")
        vol_download, download_bonus, dl24, dl7, dl30 = parse_volume_block("download total")

        # Ratio : nouvelle page = "RATIO" (la 1ere occurrence est le ratio du header,
        # meme valeur que celle du bloc stats, donc on prend la premiere match).
        ratio = find_value_after("ratio")

        # Compteurs : valeur APRES label sur la nouvelle page /stats (22/04/2026).
        count_uploaded = clean_count(find_value_after("uploadés"))
        count_completed = clean_count(find_value_after("complétés"))
        count_seed = clean_count(find_value_after("en seed"))

        # Temps de seed : label "SEEDTIME" suivi d'une seule ligne "32642j 4h".
        seed_raw = find_value_after("seedtime")
        seed_total = self.format_duration(seed_raw) if seed_raw != "0" else "0"

        # Rang + score (ex : "#5631" / "Score 501.0")
        rang = find_value_after("rang")
        score = "0"
        for line in lines:
            m = re.match(r'^score\s+([\d.,]+)\s*$', line, re.IGNORECASE)
            if m:
                score = m.group(1)
                break

        # Buffer = upload - download
        buffer = self._compute_buffer(vol_upload, vol_download)

        def clean_or_zero(v: str) -> str:
            return self.clean_text(v) if v and v != "0" else "0"

        raw_data = {
            "count_uploaded_torrents": count_uploaded,
            "upload_bonus": clean_or_zero(upload_bonus),
            "download_bonus": clean_or_zero(download_bonus),
            "upload_24h": clean_or_zero(up24),
            "upload_7j": clean_or_zero(up7),
            "upload_30j": clean_or_zero(up30),
            "download_24h": clean_or_zero(dl24),
            "download_7j": clean_or_zero(dl7),
            "download_30j": clean_or_zero(dl30),
            "rang": rang if rang != "0" else None,
            "score": score if score != "0" else None,
        }

        return ScrapedStats(
            tracker_name=self.name,
            ratio=ratio,
            buffer=buffer,
            vol_upload=self.clean_text(vol_upload),
            vol_download=self.clean_text(vol_download),
            points_bonus="0",
            fl_tokens="0",
            count_seed=count_seed,
            count_leech="0",
            count_downloaded=count_completed,
            seed_time_total=seed_total,
            seed_time_avg=None,
            warnings_active="0",
            hit_and_run="0",
            raw_data=raw_data,
        )

    async def _scrape_tokens(self, page: Page) -> str:
        """Parse la page /tokens pour le solde (SOLDE ACTUEL: N tokens)."""
        try:
            body = await page.locator('body').inner_text(timeout=10000)
            lines = [l.strip() for l in body.split('\n') if l.strip()]

            for i, line in enumerate(lines):
                # Chercher specifiquement "SOLDE ACTUEL" (le vrai label du solde)
                if line.lower() == "solde actuel":
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
