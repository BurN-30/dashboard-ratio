# Migrations Alembic

Alembic gere les changements de schema PostgreSQL pour TrackBoard.
Sans Alembic, chaque modification de modele necessitait de DROP les tables
(et donc de perdre l'historique des stats trackers).

## Premiere mise en place (a faire UNE SEULE FOIS)

### Cas 1 : DB vierge (premiere installation)

```bash
docker compose up -d db backend
docker compose exec backend alembic revision --autogenerate -m "initial schema"
docker compose exec backend alembic upgrade head
```

La migration `initial schema` est generee a partir des modeles SQLAlchemy
de `app/db/models.py`. Elle est ensuite appliquee a la DB vierge.

### Cas 2 : DB existante (migration depuis l'ancien `create_all`)

Si la stack tournait deja avec `Base.metadata.create_all()`, les tables
existent mais Alembic ne le sait pas. Il faut **marquer** la DB comme
deja a jour :

```bash
docker compose up -d db backend
docker compose exec backend alembic revision --autogenerate -m "initial schema"
docker compose exec backend alembic stamp head
```

`stamp head` cree la table `alembic_version` et y inscrit la revision
courante, sans rien modifier d'autre. Les tables existantes sont
preservees.

> Tres important : faire `stamp` AVANT le premier `upgrade`, sinon
> Alembic essaiera de creer les tables et echouera sur les conflits.

## Workflow normal (changements de schema)

```bash
# 1. Modifier les modeles dans app/db/models.py

# 2. Generer une migration auto (Alembic compare modeles vs DB)
docker compose exec backend alembic revision --autogenerate -m "add column foo to bar"

# 3. INSPECTER le fichier genere dans alembic/versions/
#    Alembic detecte la plupart des changements mais peut rater des cas (renames, etc.)
#    Editer manuellement si besoin.

# 4. Appliquer
docker compose exec backend alembic upgrade head

# 5. Commit le fichier de migration dans git
git add backend/alembic/versions/*.py
git commit -m "db: add column foo"
```

## Commandes utiles

```bash
# Etat actuel
docker compose exec backend alembic current

# Historique
docker compose exec backend alembic history

# Annuler la derniere migration
docker compose exec backend alembic downgrade -1

# Generer du SQL pur (sans appliquer)
docker compose exec backend alembic upgrade head --sql
```

## Note sur init_db()

`app/db/database.py:init_db()` appelle encore `Base.metadata.create_all`
pour preserver le bootstrap automatique au demarrage du backend.

Une fois Alembic mis en place via `stamp head` (ou via une premiere
`upgrade head` sur DB vierge), tu peux retirer l'appel a `init_db()`
dans `app/main.py` pour que le schema soit gere uniquement par Alembic.

C'est une transition manuelle volontairement non automatisee pour eviter
de casser une DB existante par megarde.
