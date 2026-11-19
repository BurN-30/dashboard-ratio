"""
Classe de base abstraite pour tous les scrapers de trackers.
"""
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
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

    # Trackers a session manuelle (captcha a la connexion : C411, Ygg) : cookie de session
    # que l'utilisateur depose depuis son navigateur. {"name", "domain", "duree_jours", "fixe"} ;
    # « fixe » = la duree court depuis la connexion, les releves ne la prolongent pas.
    # Facultatif : "lien_reconnexion", lien cliquable mis dans les alertes Discord de session.
    SESSION_COOKIE: Optional[dict] = None

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

    def deposer_session(self, valeur: str) -> None:
        """
        Ecrit le cookie de session au format storage_state de Playwright. Les autres cookies
        deja enregistres (cf_clearance...) sont gardes. La valeur n'est jamais journalisee.
        """
        modele = self.SESSION_COOKIE
        if not modele:
            raise ValueError("ce tracker n'a pas de session manuelle")
        chemin = self._cookies_path()
        etat = {"cookies": [], "origins": []}
        if chemin.exists():
            try:
                ancien = json.loads(chemin.read_text())
                etat["cookies"] = [c for c in ancien.get("cookies", []) if c.get("name") != modele["name"]]
                etat["origins"] = ancien.get("origins", [])
            except (OSError, ValueError):
                pass
        etat["cookies"].append({
            "name": modele["name"],
            "value": valeur,
            "domain": modele["domain"],
            "path": "/",
            "expires": int(time.time()) + int(modele.get("duree_jours", 7)) * 86400,
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax",
        })
        self._ecrire_etat(etat)

    def deposer_storage_state(self, etat: dict) -> None:
        """
        Écrit un storage_state complet de Playwright, déjà validé par la route de dépôt
        (cookies du site seulement, cookie de session présent). Ses cookies remplacent ceux
        de même (nom, domaine, chemin) et l'ancien cookie de session ; les autres cookies
        déjà enregistrés sont gardés, comme les origines absentes du nouvel état.
        Aucune valeur n'est journalisée.
        """
        modele = self.SESSION_COOKIE
        if not modele:
            raise ValueError("ce tracker n'a pas de session manuelle")
        cle = lambda c: (c.get("name"), str(c.get("domain", "")).lstrip("."), c.get("path", "/"))
        nouveaux = {cle(c) for c in etat["cookies"]}
        origines = {o["origin"] for o in etat.get("origins", [])}
        cookies, origins = [], []
        chemin = self._cookies_path()
        if chemin.exists():
            try:
                ancien = json.loads(chemin.read_text())
                cookies = [c for c in ancien.get("cookies", [])
                           if isinstance(c, dict) and c.get("name") != modele["name"] and cle(c) not in nouveaux]
                origins = [o for o in ancien.get("origins", [])
                           if isinstance(o, dict) and o.get("origin") not in origines]
            except (OSError, ValueError, AttributeError):
                pass
        self._ecrire_etat({"cookies": cookies + list(etat["cookies"]),
                           "origins": origins + list(etat.get("origins", []))})

    def _ecrire_etat(self, etat: dict) -> None:
        """Écriture atomique du fichier de cookies, lisible par le seul propriétaire."""
        chemin = self._cookies_path()
        COOKIES_DIR.mkdir(parents=True, exist_ok=True)
        provisoire = chemin.with_suffix(".json.tmp")
        descripteur = os.open(provisoire, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descripteur, "w") as f:
            json.dump(etat, f)
        os.replace(provisoire, chemin)

    def expiration_session(self, deposee_le: Optional[datetime] = None) -> Optional[datetime]:
        """
        Expiration prevue de la session manuelle : celle du cookie enregistre et, si la duree
        est fixe, la date de depot plus cette duree (la plus proche des deux). None si inconnue.
        """
        modele = self.SESSION_COOKIE
        if not modele:
            return None
        candidates = []
        try:
            for c in json.loads(self._cookies_path().read_text()).get("cookies", []):
                if c.get("name") == modele["name"] and (c.get("expires") or -1) > 0:
                    candidates.append(datetime.fromtimestamp(c["expires"], tz=timezone.utc))
        except (OSError, ValueError):
            return None
        if modele.get("fixe") and deposee_le is not None:
            if deposee_le.tzinfo is None:
                deposee_le = deposee_le.replace(tzinfo=timezone.utc)
            candidates.append(deposee_le + timedelta(days=int(modele.get("duree_jours", 7))))
        return min(candidates) if candidates else None

    async def _save_cookies(self, context: BrowserContext) -> None:
        """Sauvegarde les cookies du context pour reutilisation."""
        try:
            # État complet du contexte (tous les cookies, pas seulement celui de session),
            # écrit d'un bloc : un arrêt en cours d'écriture ne laisse pas de fichier tronque.
            self._ecrire_etat(await context.storage_state())
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
                logger.info(
                    "[%s] Scraping termine (via cookies, ratio=%s, upload=%s)",
                    self.name, getattr(stats, "ratio", None), getattr(stats, "vol_upload", None),
                )
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
            logger.info(
                "[%s] Scraping termine (ratio=%s, upload=%s)",
                self.name, getattr(stats, "ratio", None), getattr(stats, "vol_upload", None),
            )
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
