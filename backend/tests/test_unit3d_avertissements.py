"""Tableau « Avertissements » du profil UNIT3D et article de rachat de la boutique.

Extrait HTML figé d'après la page lue le 18/11/2026 (structure réelle, noms, identifiants
et dates inventés). La ligne active (fa-check) suit le gabarit UNIT3D : seules des lignes
levées (fa-times) étaient visibles ce jour-là.
"""
from datetime import datetime

from app.scrapers.boutique import parse_rachat_hnr, url_boutique_unit3d
from app.scrapers.unit3d import avertissements_actifs, parse_avertissements

ENTETE = """
<section class="panelV2"><header class="panel__header"><h2 class="panel__heading">Avertissements</h2></header>
<menu class="panel__tabs"><li class="panel__tab panel__tab--active" role="tab">Automated (3)</li></menu>
<div class="data-table-wrapper"><table class="data-table"><thead><tr>
  <th wire:click="sortBy('warned_by')" role="columnheader button">
      Averti par
      <!--[if BLOCK]><![endif]-->    <i class="fas fa-sort" style="opacity: 0.35"></i>
  </th>
  <!--[if BLOCK]><![endif]--><th wire:click="sortBy('torrent')" role="columnheader button">Torrent <i class="fas fa-sort"></i></th>
  <th wire:click="sortBy('reason')" role="columnheader button">Raison <i class="fas fa-sort"></i></th>
  <th wire:click="sortBy('created_at')" role="columnheader button">Cr&eacute;&eacute; le <i class="fas fa-sort"></i></th>
  <th wire:click="sortBy('expires_on')" role="columnheader button">Expire le <i class="fas fa-sort"></i></th>
  <th wire:click="sortBy('active')" role="columnheader button">Actif <i class="fas fa-sort"></i></th>
  <th>Actions</th>
</tr></thead><tbody>
"""


def ligne(ident, nom, cree, expire, icone):
    return f"""<tr x-data="userWarnings" data-warning-id="{ident}">
  <td> <span class="user-tag" style="background-image: none;">
      <a class="user-tag__link fas fa-user" href="https://tracker.example/users/System" title="Bot"> System </a> </span> </td>
  <td> <a href="https://tracker.example/torrents/{ident}">
          {nom}
      </a> </td>
  <td>Hit and Run Warning For Torrent {nom}</td>
  <td> <time datetime="{cree}" title="{cree}"> {cree} </time> </td>
  <td> <time datetime="{expire}" title="{expire}"> {expire} </time> </td>
  <td> <i class="fas {icone}"></i> </td>
</tr>"""


FIN = "</tbody></table></div></section>"

PROFIL = (
    "<html><body><table><thead><tr><th>Client</th><th>IP</th></tr></thead>"
    "<tbody><tr><td>qBittorrent</td><td>x</td></tr></tbody></table>"
    + ENTETE
    + ligne(501, "Film.Un.2020.MULTi.1080p.WEB.H265-GRP", "2026-11-17 18:19:37", "2026-11-24 18:19:37", "fa-check text-green")
    + ligne(502, "Serie.Deux.S01.COMPLETE.VFF.1080p.WEB.H265-GRP", "2026-11-17 18:19:37", "2026-11-18 13:03:52", "fa-times text-red")
    + ligne(503, "Anime.Trois.S23E20.VOSTFR.1080p.WEB.x264-GRP", "2026-08-22 00:00:22", "2026-09-05 00:00:20", "fa-times text-red")
    + FIN + "</body></html>"
)

VIDE = ENTETE + """<tr><td colspan="7">
    Il n'y a aucun avertissement dans la base de données pour cet utilisateur !
</td></tr>""" + FIN


def test_colonnes_lues_par_leur_en_tete():
    lignes = parse_avertissements(PROFIL)
    assert len(lignes) == 3
    assert lignes[0] == {
        "torrent": "Film.Un.2020.MULTi.1080p.WEB.H265-GRP",
        "url": "https://tracker.example/torrents/501",
        "cree_le": "2026-11-17 18:19:37",   # colonne « Créé le »
        "expire_le": "2026-11-24 18:19:37",  # colonne « Expire le »
        "actif": True,
    }
    assert [l["actif"] for l in lignes] == [True, False, False]


def test_seuls_les_actifs_sont_gardes():
    actifs = avertissements_actifs(parse_avertissements(PROFIL))
    assert [a["torrent"] for a in actifs] == ["Film.Un.2020.MULTi.1080p.WEB.H265-GRP"]
    assert "actif" not in actifs[0]


def test_icone_illisible_on_se_fie_a_l_expiration():
    html = ENTETE + ligne(1, "A", "2026-11-17 18:19:37", "2026-11-24 18:19:37", "fa-question") \
        + ligne(2, "B", "2026-01-01 00:00:00", "2026-01-15 00:00:00", "fa-question") + FIN
    lignes = parse_avertissements(html)
    assert [l["actif"] for l in lignes] == [None, None]
    assert [a["torrent"] for a in avertissements_actifs(lignes, datetime(2026, 11, 18, 14, 0))] == ["A"]


def test_lien_relatif_et_tableau_vide():
    html = PROFIL.replace("https://tracker.example/torrents/", "/torrents/")
    assert parse_avertissements(html, "https://tracker.example/users/moi")[0]["url"] == "https://tracker.example/torrents/501"
    assert parse_avertissements(VIDE) == []
    assert parse_avertissements("<html><body>rien</body></html>") == []


def test_article_de_rachat():
    g3mini = "Objet\tCost\tÉchange\n500 GiB Upload\t80 000\t\nRachat d'un H&R\t100 000\t\nVOS G3MS\n"
    assert parse_rachat_hnr(g3mini) == {"libelle": "Rachat d'un H&R", "cost": 100000}
    tos = "500 GiB Upload\t150000\t\nSupprimer un H&R\t5000\t\nVos points\n"
    assert parse_rachat_hnr(tos) == {"libelle": "Supprimer un H&R", "cost": 5000}
    gf = "450 GiB Upload\t510000\t\n500 GiB Upload\t560000\t\nVos GFrees (G★)\n"
    assert parse_rachat_hnr(gf) is None


def test_url_de_la_boutique():
    assert url_boutique_unit3d("https://tracker.example/users/moi") == "https://tracker.example/users/moi/transactions/create"
