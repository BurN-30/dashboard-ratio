"""
Boutiques de bonus des trackers : paliers d'upload achetables et estimation
de l'upload que les points actuels permettent d'acheter.

Paliers enregistres dans /app/cookies/bonus_tiers.json, au format
{"TOS": [{"gib": 500.0, "cost": 150000}, ...], ...} :
- UNIT3D (TOS, G3MINI, GF-FREE) : verification hebdomadaire (bonus_checker) ;
- TR4KER : a chaque releve, par l'API /api/shop (meme session que les stats).
"""
import json
import logging
import os
import re
from typing import Iterable, Optional

logger = logging.getLogger("dashboard.boutique")

TIERS_FILE = "/app/cookies/bonus_tiers.json" if os.path.isdir("/app") else "cookies/bonus_tiers.json"

# « 500 GiB Upload<tab>80 000 » (libelle et prix sur la meme ligne depuis 2026)
_UNIT3D = re.compile(r"(\d+(?:[.,]\d+)?)\s*(GiB|TiB)\s+Upload\s+(\d[\d\s  ,.]*)")


def _entier(texte: str) -> Optional[int]:
    chiffres = re.sub(r"[^\d]", "", texte)
    return int(chiffres) if chiffres else None


def parse_paliers_unit3d(body: str) -> list[dict]:
    """Texte de /users/{u}/transactions/create -> [{"gib", "cost"}]."""
    paliers = []
    for ligne in body.split("\n"):
        m = _UNIT3D.search(ligne)
        if not m:
            continue
        taille = float(m.group(1).replace(",", "."))
        gib = taille * 1024 if m.group(2) == "TiB" else taille
        cout = _entier(m.group(3))
        if cout:
            paliers.append({"gib": gib, "cost": cout})
    return paliers


def paliers_tr4ker(items: Iterable[dict]) -> list[dict]:
    """Articles de /api/shop (TR4KER) -> paliers d'upload (bonus_bytes en octets binaires)."""
    paliers = []
    for it in items or []:
        octets, prix = it.get("bonus_bytes"), it.get("price")
        if isinstance(octets, (int, float)) and octets > 0 and isinstance(prix, (int, float)) and prix > 0:
            paliers.append({"gib": octets / 1024 ** 3, "cost": int(prix)})
    return paliers


def points_en_entier(points: Optional[str]) -> int:
    """« 9 040 535 G★ », « 1,917,419.50 », « 2 752 312 » -> entier (partie entiere)."""
    if not points:
        return 0
    texte = str(points)
    # Une decimale finale (.50 ou ,50 apres un groupe de milliers) n'est pas un separateur.
    texte = re.sub(r"[.,]\d{1,2}(?!\d)", "", texte)
    return _entier(texte) or 0


def estimer_gib(points: int, paliers: list[dict]) -> float:
    """
    Upload achetable avec `points` : on achete d'abord les paliers les moins chers
    au Go (souvent les plus gros), autant que possible, puis les suivants.
    """
    total = 0.0
    reste = points
    for p in sorted(paliers, key=lambda p: (p["cost"] / p["gib"], -p["gib"])):
        if p["cost"] <= 0:
            continue
        n, reste = divmod(reste, p["cost"])
        total += n * p["gib"]
    return total


def format_gib(gib: float) -> str:
    """Go binaires -> « 11.6 To » ou « 580 Go » (memes unites que les compteurs des sites)."""
    if gib >= 1024:
        return f"{gib / 1024:.1f} To"
    return f"{gib:.0f} Go"


def charger_paliers() -> dict:
    try:
        with open(TIERS_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def enregistrer_paliers(nom: str, paliers: list[dict]) -> None:
    """Met a jour les paliers d'un tracker (sans toucher aux autres)."""
    if not paliers:
        return
    tous = charger_paliers()
    tous[nom] = paliers
    try:
        with open(TIERS_FILE, "w") as f:
            json.dump(tous, f, indent=2, ensure_ascii=False)
    except OSError as e:
        logger.warning("[boutique] Impossible d'enregistrer les paliers de %s : %s", nom, e)


def upload_achetable(nom: str, points: Optional[str], paliers_par_tracker: dict) -> Optional[str]:
    """Texte « ≈ X To » pour /api/stats, ou None si les paliers sont inconnus."""
    paliers = paliers_par_tracker.get(nom) or []
    if not paliers:
        return None
    return format_gib(estimer_gib(points_en_entier(points), paliers))
