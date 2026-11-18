"""
Notifications Discord via webhook.
Non-bloquant, ne crash jamais l'app.

Alertes :
- Relevé en échec : une alerte au 3e échec consécutif, puis un rappel par 24 h, et le
  rétablissement. Message dédié quand la session manuelle (C411, Ygg) a expiré.
- Session manuelle : alerte quand il reste moins de SESSION_ALERTE_HEURES (24 h) avant
  l'expiration prévue, signe que le renouvellement automatique n'a pas eu lieu.
- Ratio sous 0.85 (@here)
- Avertissements actifs (H&R en cours, le compteur historique est ignoré) : alerte quand le
  compteur augmente (@here à partir de 2), puis un rappel sans @here par 24 h tant qu'il en
  reste 2 ou plus. Lien de rachat, prix face au solde et torrents concernés.
- Agent hardware offline >1h (@here) + reconnect

Les fonctions `decider_*` et `embed_*` sont pures (testables sans réseau) ; les `notify_*`
envoient.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger("dashboard.notifications")

# « Un rappel par 24 h » : les relevés tombent à heures fixes, à quelques secondes près ;
# une marge évite de sauter le relevé du lendemain à la même heure.
RAPPEL_APRES = timedelta(hours=23, minutes=30)


def preavis_session() -> timedelta:
    """
    Seuil de l'alerte d'expiration de session (SESSION_ALERTE_HEURES, 24 h par défaut). La
    session est renouvelée par un script extérieur environ 48 h avant l'échéance : passer
    sous ce seuil veut dire que le renouvellement a échoué. L'alerte part au premier relevé
    réussi sous le seuil (relevés à 8 h, 14 h et 20 h).
    """
    return timedelta(hours=get_settings().session_alerte_heures)


ERREURS_SESSION = ("session_absente_reconnexion_manuelle", "session_expiree_reconnexion_manuelle",
                   "session_illisible_reconnexion_manuelle")

ROUGE, ORANGE, VERT = 0xFF4444, 0xFF8800, 0x44BB44


def _get_webhook_url() -> str | None:
    settings = get_settings()
    url = getattr(settings, "discord_webhook_url", None)
    return url if url else None


async def _send(embed: dict, ping_here: bool = False):
    """Envoie un embed Discord. Fire-and-forget, ne crash jamais."""
    url = _get_webhook_url()
    if not url:
        return

    try:
        payload = {"username": "TrackBoard", "embeds": [embed]}
        if ping_here:
            payload["content"] = "@here"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code not in (200, 204):
                logger.warning("Discord webhook %s: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.warning("Discord notification failed: %s", e)


def _utc(d: Optional[datetime]) -> Optional[datetime]:
    """Date sans fuseau (SQLite) -> UTC."""
    if d is not None and d.tzinfo is None:
        return d.replace(tzinfo=timezone.utc)
    return d


def _delai_ecoule(derniere_alerte: Optional[datetime], maintenant: datetime) -> bool:
    derniere_alerte = _utc(derniere_alerte)
    return derniere_alerte is None or _utc(maintenant) - derniere_alerte >= RAPPEL_APRES


def _milliers(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def _maj(texte: str) -> str:
    return texte[:1].upper() + texte[1:]


def _horodatage() -> str:
    return datetime.now(timezone.utc).isoformat()


# === RELEVÉS EN ÉCHEC ===

def decider_alerte_echec(consecutifs: int, derniere_alerte: Optional[datetime],
                         maintenant: datetime) -> Optional[str]:
    """
    Faut-il alerter après un relevé en échec ? « premiere » au 3e échec consécutif,
    « rappel » au plus une fois par 24 h ensuite, None sinon.
    """
    if consecutifs < 3:
        return None
    if derniere_alerte is None:
        return "premiere" if consecutifs == 3 else "rappel"
    return "rappel" if _delai_ecoule(derniere_alerte, maintenant) else None


def embed_echec(tracker_name: str, consecutifs: int, erreur: Optional[str], rappel: bool = False,
                reconnexion: Optional[dict] = None) -> dict:
    """
    Alerte d'échec. `reconnexion` ({"login_url", "cookie", "trackboard_url"} et, facultatif,
    "lien_reconnexion") accompagne les trackers à session manuelle : quand l'erreur est une
    session expirée, le message dit quoi faire au lieu d'afficher le code d'erreur.
    """
    prefixe = "Rappel : " if rappel else ""
    pied = {"text": "Un rappel par 24 h tant que la panne dure, puis un message au rétablissement."}

    if (erreur or "") in ERREURS_SESSION and reconnexion:
        cookie = reconnexion.get("cookie") or "de session"
        ou = reconnexion.get("trackboard_url")
        trackboard = f"[TrackBoard]({ou})" if ou else "TrackBoard"
        lien = reconnexion.get("lien_reconnexion")
        raccourci = f"\n**[Se reconnecter à {tracker_name}]({lien})**" if lien else ""
        etapes = [
            f"1. Se connecter à {reconnexion.get('login_url') or 'au site'} dans le navigateur (captcha compris).",
            f"2. F12, onglet Application (Chrome) ou Stockage (Firefox), Cookies : copier la valeur de `{cookie}`.",
            f"3. Ouvrir {trackboard}, carte {tracker_name}, « Reconnecter » : coller la valeur et valider.",
        ]
        return {
            "title": _maj(f"{prefixe}session expirée : {tracker_name}"),
            "description": (
                "La session ouverte à la main n'est plus valable : reconnexion à faire. "
                "La connexion passe par un captcha, TrackBoard ne la refait jamais seul.\n"
                f"**{consecutifs}** relevés sans données depuis l'expiration."
                f"{raccourci}"
            ),
            "color": ROUGE,
            "fields": [{"name": "Marche à suivre", "value": "\n".join(etapes), "inline": False}],
            "footer": pied,
            "timestamp": _horodatage(),
        }

    return {
        "title": _maj(f"{prefixe}relevé en échec : {tracker_name}"),
        "description": f"**{consecutifs}** échecs consécutifs.",
        "color": ROUGE,
        "fields": [{"name": "Erreur", "value": f"```{(erreur or '?')[:200]}```", "inline": False}],
        "footer": pied,
        "timestamp": _horodatage(),
    }


async def notify_scrape_failures(tracker_name: str, consecutifs: int, erreur: Optional[str],
                                 rappel: bool = False, reconnexion: Optional[dict] = None):
    """Alerte d'échec (la décision d'envoyer appartient à decider_alerte_echec)."""
    await _send(embed_echec(tracker_name, consecutifs, erreur, rappel, reconnexion))


async def notify_scrape_recovery(tracker_name: str, consecutive_before: int):
    """Rétablissement après 3 échecs ou plus."""
    if consecutive_before < 3:
        return
    await _send({
        "title": f"Relevé rétabli : {tracker_name}",
        "description": f"De retour après **{consecutive_before}** échecs.",
        "color": VERT,
        "timestamp": _horodatage(),
    })


# === SESSION MANUELLE ===

def session_bientot_expiree(expiration: Optional[datetime], deja_prevenu: Optional[datetime],
                            maintenant: datetime, preavis: Optional[timedelta] = None) -> bool:
    """
    Vrai une seule fois par session déposée : au premier relevé à moins de `preavis`
    (SESSION_ALERTE_HEURES par défaut) de l'expiration prévue.
    """
    if expiration is None or deja_prevenu is not None:
        return False
    return _utc(expiration) - _utc(maintenant) < (preavis_session() if preavis is None else preavis)


def _temps_restant(delai: timedelta) -> str:
    """« 23 h 30 », « 45 min » ; chaîne vide si l'échéance est passée."""
    minutes = int(delai.total_seconds() // 60)
    if minutes <= 0:
        return ""
    heures, minutes = divmod(minutes, 60)
    if heures and minutes:
        return f"{heures} h {minutes:02d}"
    return f"{heures} h" if heures else f"{minutes} min"


def embed_session_bientot_expiree(tracker_name: str, expiration: datetime, reconnexion: dict,
                                  maintenant: Optional[datetime] = None) -> dict:
    """
    Alerte « le renouvellement automatique n'a pas eu lieu » : temps restant, et lien de
    reconnexion quand le tracker en déclare un (`reconnexion["lien_reconnexion"]`).
    """
    from zoneinfo import ZoneInfo

    expiration = _utc(expiration)
    maintenant = _utc(maintenant) or datetime.now(timezone.utc)
    quand = expiration.astimezone(ZoneInfo("Europe/Paris")).strftime("%d/%m vers %H h %M")
    restant = _temps_restant(expiration - maintenant)
    echeance = (f"elle expire dans **{restant}**, le {quand} (heure de Paris)" if restant
                else f"son échéance prévue, le {quand} (heure de Paris), est dépassée")
    ou = reconnexion.get("trackboard_url")
    trackboard = f"[TrackBoard]({ou})" if ou else "TrackBoard"
    manuel = (f"copier la valeur du cookie `{reconnexion.get('cookie')}` (F12, Application ou Stockage, "
              f"Cookies) et la coller dans {trackboard}, carte {tracker_name}, « Reconnecter »")
    lien = reconnexion.get("lien_reconnexion")
    if lien:
        marche = (f"**[Se reconnecter à {tracker_name}]({lien})** : une fois la connexion faite, le script "
                  f"utilisateur dépose la nouvelle session.\nSans le script : {manuel}.")
    else:
        marche = f"Pour ne pas perdre de relevé : se reconnecter au site, puis {manuel}."
    return {
        "title": f"Session {tracker_name} : renouvellement automatique non effectué",
        "description": (
            f"Le renouvellement automatique de la session n'a pas eu lieu : {echeance}.\n{marche}"
        ),
        "color": ORANGE,
        "timestamp": _horodatage(),
    }


async def notify_session_bientot_expiree(tracker_name: str, expiration: datetime, reconnexion: dict,
                                         maintenant: Optional[datetime] = None):
    await _send(embed_session_bientot_expiree(tracker_name, expiration, reconnexion, maintenant))


# === RATIO ===

async def notify_ratio_critical(tracker_name: str, ratio: float):
    """Ratio passe sous 0.85. @here."""
    await _send({
        "title": f"Ratio critique : {tracker_name}",
        "description": f"Ratio a **{ratio:.2f}** (seuil : 0.85)",
        "color": ROUGE,
        "timestamp": _horodatage(),
    }, ping_here=True)


# === HIT & RUN ===

def decider_alerte_avertissements(nombre: int, precedent: int, derniere_alerte: Optional[datetime],
                                  maintenant: datetime) -> Optional[str]:
    """
    Faut-il alerter pour les avertissements actifs ?
    - le compteur augmente : « critique » (@here) à partir de 2, « nouveau » pour un seul ;
    - il reste 2 avertissements ou plus : « rappel » (sans @here) au plus une fois par 24 h ;
    - sinon None.
    """
    if nombre <= 0:
        return None
    if nombre > precedent:
        return "critique" if nombre >= 2 else "nouveau"
    if nombre >= 2 and _delai_ecoule(derniere_alerte, maintenant):
        return "rappel"
    return None


def _date_courte(texte: Optional[str]) -> str:
    """« 2026-11-17 18:19:37 » -> « 17/11 à 18:19 » (heure du site) ; texte inconnu laissé tel quel."""
    try:
        d = datetime.strptime((texte or "").strip()[:19], "%Y-%m-%d %H:%M:%S")
        return d.strftime("%d/%m à %H:%M")
    except ValueError:
        return (texte or "?").strip() or "?"


def _lignes_torrents(avertissements: list[dict], nombre: int, limite: int = 1000) -> str:
    lignes, taille = [], 0
    for a in avertissements:
        nom = (a.get("torrent") or "torrent inconnu").replace("[", "(").replace("]", ")")
        if len(nom) > 70:
            nom = nom[:67] + "..."
        titre = f"[{nom}]({a['url']})" if a.get("url") else nom
        ligne = f"• {titre} : averti le {_date_courte(a.get('cree_le'))}, expire le {_date_courte(a.get('expire_le'))}"
        if taille + len(ligne) + 1 > limite - 40:
            break
        lignes.append(ligne)
        taille += len(ligne) + 1
    reste = nombre - len(lignes)
    if reste > 0 and lignes:
        lignes.append(f"et {reste} autre(s), voir le profil")
    return "\n".join(lignes)


def texte_rachat(details: dict, nombre: int) -> Optional[str]:
    """Ligne « rachat » : lien de la boutique, prix face au solde. None si la boutique n'a pas été lue."""
    if not details.get("boutique_lue"):
        return None
    rachat = details.get("rachat_hnr")
    if not rachat or not rachat.get("cost"):
        return "Pas d'article de rachat dans la boutique de ce tracker : seul le partage lève l'avertissement."
    prix, solde = int(rachat["cost"]), details.get("solde")
    libelle = rachat.get("libelle") or "Rachat d'un H&R"
    lien = f"[{libelle}]({details['boutique_url']})" if details.get("boutique_url") else libelle
    texte = f"{lien} : **{_milliers(prix)}** points l'unité."
    if isinstance(solde, int):
        possibles = solde // prix
        if possibles <= 0:
            texte += f"\nSolde : {_milliers(solde)}, il manque **{_milliers(prix - solde)}** pour un rachat."
        else:
            pluriel = "s" if possibles > 1 else ""
            texte += (f"\nSolde : {_milliers(solde)}, suffisant pour **{possibles}** rachat{pluriel}"
                      f" ({nombre} avertissement{'s' if nombre > 1 else ''} à lever).")
    return texte


def embed_avertissements(tracker_name: str, nombre: int, niveau: str, details: Optional[dict] = None) -> dict:
    """
    Alerte d'avertissements actifs. `niveau` : « nouveau », « critique » ou « rappel ».
    `details` (collecteur UNIT3D, facultatif) : {"avertissements": [{"torrent", "url", "cree_le",
    "expire_le"}], "profil_url", "boutique_lue", "boutique_url", "rachat_hnr": {"libelle", "cost"},
    "solde"}.
    """
    details = details or {}
    pluriel = "s" if nombre > 1 else ""
    if niveau == "rappel":
        titre = f"Rappel : {nombre} avertissement{pluriel} toujours actif{pluriel} sur {tracker_name}"
    elif niveau == "critique":
        titre = f"Avertissements critiques : {tracker_name}"
    else:
        titre = f"Avertissement actif : {tracker_name}"
    description = f"**{nombre}** avertissement{pluriel} actif{pluriel} (hit and run en cours)"
    description += ", risque de ban." if nombre >= 2 else "."

    champs = []
    torrents = _lignes_torrents(details.get("avertissements") or [], nombre)
    if torrents:
        champs.append({
            "name": "Torrents concernés (les remettre en partage lève l'avertissement)",
            "value": torrents, "inline": False,
        })
    rachat = texte_rachat(details, nombre)
    if rachat:
        champs.append({"name": "Rachat avec les points", "value": rachat[:1024], "inline": False})
    if details.get("profil_url"):
        champs.append({"name": "Profil", "value": f"[Liste des avertissements]({details['profil_url']})",
                       "inline": False})

    embed = {
        "title": titre[:256],
        "description": description,
        "color": ORANGE if niveau == "nouveau" else ROUGE,
        "timestamp": _horodatage(),
    }
    if champs:
        embed["fields"] = champs
    if nombre >= 2:
        embed["footer"] = {"text": "Rappel sans @here au plus une fois par 24 h tant qu'il reste 2 avertissements ou plus."}
    return embed


async def notify_avertissements(tracker_name: str, nombre: int, niveau: str, details: Optional[dict] = None):
    """Envoie l'alerte d'avertissements ; @here seulement pour le niveau « critique »."""
    await _send(embed_avertissements(tracker_name, nombre, niveau, details), ping_here=(niveau == "critique"))


# === PARSER ===

async def notify_parser_suspect(tracker_name: str, reason: str):
    """Scrape OK mais certains champs stats principaux sont vides alors que tokens>0.
    Signal que le tracker a probablement change sa page et que le parser est HS."""
    await _send({
        "title": f"Parser suspect : {tracker_name}",
        "description": "Certains champs stats sont vides alors que les tokens remontent. Le parser a peut-etre besoin d'une mise a jour.",
        "color": ORANGE,
        "fields": [{"name": "Detail", "value": reason[:500], "inline": False}],
        "timestamp": _horodatage(),
    })


# === HARDWARE AGENT ===

async def notify_agent_disconnect():
    """PC offline depuis 1h. @here."""
    await _send({
        "title": "PC offline",
        "description": "L'agent hardware ne repond plus depuis 1 heure.",
        "color": ORANGE,
        "timestamp": _horodatage(),
    }, ping_here=True)


async def notify_agent_reconnect():
    """PC de retour."""
    await _send({
        "title": "PC de retour",
        "description": "L'agent hardware est reconnecte.",
        "color": VERT,
        "timestamp": _horodatage(),
    })
