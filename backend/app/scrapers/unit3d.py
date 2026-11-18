"""
Scraper pour les trackers utilisant UNIT3D.
Compatible avec: Generation-Free, TheOldSchool, Gemini-Tracker
"""
import logging
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urljoin
from playwright.async_api import Page

from app.scrapers.base import BaseScraper, ScraperConfig, ScrapedStats
from app.scrapers.boutique import parse_rachat_hnr, points_en_entier, url_boutique_unit3d

logger = logging.getLogger("dashboard.scraper")

# Nombre d'avertissements detailles dans raw_data (le tableau du profil en montre 10 par page).
MAX_AVERTISSEMENTS = 10


class _Tableaux(HTMLParser):
    """Tableaux d'une page : en-tetes et cellules (texte, premier lien, date, classes des icones)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tableaux: list[dict] = []
        self._t: Optional[dict] = None
        self._ligne: Optional[list] = None
        self._cellule: Optional[dict] = None
        self._entete = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self._t = {"entetes": [], "lignes": []}
            self.tableaux.append(self._t)
        elif self._t is None:
            return
        elif tag == "tr":
            self._ligne = []
        elif tag in ("td", "th") and self._ligne is not None:
            self._cellule = {"texte": "", "lien": None, "date": None, "classes": ""}
            self._entete = tag == "th"
        elif self._cellule is not None:
            if tag == "a" and a.get("href") and self._cellule["lien"] is None:
                self._cellule["lien"] = a["href"]
            elif tag == "time" and a.get("datetime") and self._cellule["date"] is None:
                self._cellule["date"] = a["datetime"]
            elif tag == "i":
                self._cellule["classes"] += " " + (a.get("class") or "")

    def handle_data(self, data):
        if self._cellule is not None:
            self._cellule["texte"] += data

    def handle_endtag(self, tag):
        if self._t is None:
            return
        if tag in ("td", "th") and self._cellule is not None and self._ligne is not None:
            self._cellule["texte"] = " ".join(self._cellule["texte"].split())
            if self._entete:
                self._t["entetes"].append(self._cellule["texte"])
            else:
                self._ligne.append(self._cellule)
            self._cellule = None
        elif tag == "tr" and self._ligne is not None:
            if self._ligne:
                self._t["lignes"].append(self._ligne)
            self._ligne = None
        elif tag == "table":
            self._t = None


def _colonne(entetes: list[str], motif: str) -> Optional[int]:
    for i, e in enumerate(entetes):
        if re.search(motif, e, re.I):
            return i
    return None


def parse_avertissements(html: str, base_url: str = "") -> list[dict]:
    """
    HTML du profil UNIT3D -> lignes du tableau « Avertissements », actifs ou non :
    [{"torrent", "url", "cree_le", "expire_le", "actif"}].

    Colonnes reperees par leur en-tete (lu le 18/11/2026 sur TOS, G3MINI et GF-FREE :
    Averti par, Torrent, Raison, Cree le, Expire le, Actif). Les deux dates sont donc la
    creation de l'avertissement et son expiration, a l'heure du site. « Actif » est une
    icone : fa-check (actif) ou fa-times (leve ou expire) ; None si elle est illisible.
    """
    analyseur = _Tableaux()
    analyseur.feed(html)
    for t in analyseur.tableaux:
        e = t["entetes"]
        c_torrent, c_expire = _colonne(e, r"^torrent"), _colonne(e, r"expir")
        if c_torrent is None or c_expire is None:
            continue
        c_cree, c_actif = _colonne(e, r"^cr[ée]|creat"), _colonne(e, r"^acti(f|ve)$")
        resultat = []
        for ligne in t["lignes"]:
            if len(ligne) <= max(c_torrent, c_expire):
                continue  # « aucun avertissement » (une seule cellule)
            cellule = ligne[c_torrent]

            def date(i):
                return (ligne[i]["date"] or ligne[i]["texte"] or None) if i is not None and i < len(ligne) else None

            actif = None
            if c_actif is not None and c_actif < len(ligne):
                classes = ligne[c_actif]["classes"]
                if "fa-check" in classes:
                    actif = True
                elif "fa-times" in classes or "fa-xmark" in classes:
                    actif = False
            resultat.append({
                "torrent": cellule["texte"] or None,
                "url": urljoin(base_url, cellule["lien"]) if cellule["lien"] else None,
                "cree_le": date(c_cree),
                "expire_le": date(c_expire),
                "actif": actif,
            })
        return resultat
    return []


def avertissements_actifs(lignes: list[dict], maintenant: Optional[datetime] = None) -> list[dict]:
    """Garde les avertissements actifs ; icone illisible : actif si l'expiration est a venir."""
    maintenant = maintenant or datetime.now(timezone.utc).replace(tzinfo=None)
    actifs = []
    for a in lignes:
        actif = a.get("actif")
        if actif is None:
            try:
                actif = datetime.strptime((a.get("expire_le") or "")[:19], "%Y-%m-%d %H:%M:%S") > maintenant
            except ValueError:
                actif = False
        if actif:
            actifs.append({k: a.get(k) for k in ("torrent", "url", "cree_le", "expire_le")})
    return actifs


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
        # Intitules renommes : G3MINI (mai 2026) et GF-FREE (octobre 2026).
        # Correspondance exacte : "G3Ms Uploader" est un volume, pas des points.
        if points == "0":
            points = await get_value("G3Ms", exact=True)
        if points == "0":
            points = await get_value("GFrees", exact=True)
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

        # Avertissement actif : quels torrents, et combien coute le rachat. La boutique
        # n'est lue que dans ce cas (une page de plus, aucune en temps normal).
        try:
            nb_avertissements = int(warnings.split()[0])
        except (ValueError, IndexError):
            nb_avertissements = 0
        if nb_avertissements > 0:
            raw_data["avertissements_detail"] = await self._detail_avertissements(page, points)

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

    async def _detail_avertissements(self, page: Page, points: str) -> dict:
        """
        Detail pour l'alerte : avertissements actifs du profil (page deja chargee), puis
        article de rachat de la boutique. Lecture seule ; ne fait jamais echouer le releve.
        """
        detail: dict = {"profil_url": self.profile_url, "solde": points_en_entier(points)}
        try:
            lignes = parse_avertissements(await page.content(), self.profile_url)
            detail["avertissements"] = avertissements_actifs(lignes)[:MAX_AVERTISSEMENTS]
        except Exception as e:
            logger.warning("[%s] Tableau des avertissements illisible : %s", self.name, e)
        try:
            boutique = url_boutique_unit3d(self.profile_url)
            await page.goto(boutique, timeout=60000)
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            if "/login" not in page.url:
                corps = await page.locator("body").inner_text(timeout=10000)
                detail["boutique_lue"] = True
                rachat = parse_rachat_hnr(corps)
                if rachat:
                    detail["rachat_hnr"] = rachat
                    detail["boutique_url"] = boutique
        except Exception as e:
            logger.warning("[%s] Boutique illisible (rachat H&R) : %s", self.name, e)
        return detail
