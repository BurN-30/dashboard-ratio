#!/bin/bash
# scripts/diagnose.sh
# A executer sur le VPS, depuis la racine du projet (la ou est docker-compose.yml).
# Collecte tout ce qu'il faut pour comprendre l'etat de la stack.
#
# Usage :
#   bash scripts/diagnose.sh > /tmp/trackboard-diag.txt
#   cat /tmp/trackboard-diag.txt   # puis copier-coller le contenu
#
# Aucune donnee sensible n'est recoltee : les valeurs des secrets sont MASQUEES.

set +e  # ne pas s'arreter sur erreur, on veut tout collecter

SEP() { echo; echo "============================================================"; echo "  $1"; echo "============================================================"; }

SEP "1. Environnement systeme"
echo "Date           : $(date -Is)"
echo "Hostname       : $(hostname)"
echo "OS             : $(. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME" || uname -a)"
echo "Uptime         : $(uptime -p 2>/dev/null || uptime)"
echo "Disk           :"; df -h / 2>/dev/null | tail -1
echo "Mem free       :"; free -h 2>/dev/null | head -2
echo "Docker version : $(docker --version 2>/dev/null || echo 'NOT INSTALLED')"
echo "Compose version: $(docker compose version 2>/dev/null || docker-compose --version 2>/dev/null || echo 'NOT INSTALLED')"

SEP "2. Reseau / ports"
echo "Public IP      : $(curl -s --max-time 5 https://ifconfig.me 2>/dev/null || echo 'N/A')"
echo "Listening on 80/443/8000/3000/5432 :"
ss -tlnp 2>/dev/null | grep -E ':80\b|:443\b|:8000\b|:3000\b|:5432\b' || \
  netstat -tlnp 2>/dev/null | grep -E ':80\b|:443\b|:8000\b|:3000\b|:5432\b' || \
  echo "(ss et netstat indisponibles)"
echo
echo "Connexions actives WebSocket vers /hardware/ws :"
ss -tn 2>/dev/null | grep -c ESTAB || echo "N/A"

SEP "3. .env present (sans afficher les valeurs)"
if [ -f .env ]; then
  echo ".env trouve. Variables definies :"
  grep -E '^[A-Z_]+=' .env | cut -d= -f1 | sort -u
  echo
  echo "Variables CRITIQUES (statut) :"
  for var in DOMAIN ACME_EMAIL JWT_SECRET ADMIN_PASSWORD HW_AGENT_TOKEN POSTGRES_PASSWORD DATABASE_URL TRACKER_USERNAME; do
    val=$(grep -E "^${var}=" .env | head -1 | cut -d= -f2-)
    if [ -z "$val" ]; then
      echo "  $var : VIDE"
    elif [ ${#val} -lt 4 ]; then
      echo "  $var : tres court (${#val} chars) - SUSPECT"
    else
      echo "  $var : defini (${#val} chars)"
    fi
  done
else
  echo "ATTENTION : .env absent !"
fi

SEP "4. Docker compose state"
if [ -f docker-compose.yml ]; then
  docker compose ps 2>&1 || docker-compose ps 2>&1
else
  echo "docker-compose.yml absent dans $(pwd)"
fi

SEP "5. Status sante des containers"
for svc in db backend frontend caddy; do
  echo "--- $svc ---"
  status=$(docker compose ps --format json $svc 2>/dev/null | head -1)
  if [ -n "$status" ]; then
    echo "$status" | head -3
  else
    docker compose ps $svc 2>/dev/null | tail -1
  fi
  echo
done

SEP "6. Logs recents (150 lignes / service)"
for svc in caddy backend frontend db; do
  echo "--- $svc ---"
  docker compose logs --tail=150 --no-color $svc 2>&1 | tail -150
  echo
done

SEP "7. Test endpoints depuis l'host"
DOMAIN=$(grep -E '^DOMAIN=' .env 2>/dev/null | cut -d= -f2 | tr -d '"' | tr -d "'")
echo "DOMAIN configure : ${DOMAIN:-?}"
echo
echo "GET https://$DOMAIN/health :"
curl -sk -o - --max-time 10 -w "\nHTTP %{http_code}\n" "https://$DOMAIN/health" 2>&1 | head -10
echo
echo "GET https://$DOMAIN/ (frontend home) :"
curl -sk -o /dev/null --max-time 10 -w "HTTP %{http_code}, %{size_download} bytes\n" "https://$DOMAIN/" 2>&1
echo
echo "GET http://localhost:8000/health (backend direct, depuis le host) :"
curl -s -o - --max-time 5 -w "\nHTTP %{http_code}\n" "http://localhost:8000/health" 2>&1 | head -10

SEP "8. Test backend depuis dans le container (DNS interne)"
docker compose exec -T backend sh -c 'curl -s -o - --max-time 5 -w "\nHTTP %{http_code}\n" http://localhost:8000/health 2>&1 | head -10' 2>&1
echo
echo "Connexion DB depuis le backend :"
docker compose exec -T backend python -c "
import asyncio, os
from sqlalchemy.ext.asyncio import create_async_engine
url = os.environ.get('DATABASE_URL', '').replace('postgresql://', 'postgresql+asyncpg://', 1)
async def t():
    try:
        e = create_async_engine(url, pool_pre_ping=True)
        async with e.begin() as c:
            from sqlalchemy import text
            r = await c.execute(text('SELECT 1'))
            print('DB OK :', r.scalar())
        await e.dispose()
    except Exception as ex:
        print('DB ERROR :', type(ex).__name__, str(ex)[:200])
asyncio.run(t())
" 2>&1

SEP "9. Tables et nombre de rows par table"
docker compose exec -T db psql -U "${POSTGRES_USER:-trackboard}" -d "${POSTGRES_DB:-trackboard}" -c "\dt" 2>&1
echo
docker compose exec -T db psql -U "${POSTGRES_USER:-trackboard}" -d "${POSTGRES_DB:-trackboard}" -c "
SELECT schemaname, relname AS table, n_live_tup AS rows
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
" 2>&1

SEP "10. Cookies trackers presents"
docker compose exec -T backend ls -la /app/cookies/ 2>&1 | head -20

SEP "11. Scrapers configures"
docker compose exec -T backend python -c "
from app.scrapers.registry import list_all_sites, list_available_scrapers
import json
print('Tous les sites :')
print(json.dumps(list_all_sites(), indent=2, ensure_ascii=False))
print()
print('Scrapers configures (avec credentials) :', list_available_scrapers())
" 2>&1

SEP "12. Caddyfile actif"
docker compose exec -T caddy cat /etc/caddy/Caddyfile 2>&1 | head -50
echo
echo "Caddy admin API (si disponible) :"
docker compose exec -T caddy wget -qO- http://localhost:2019/config/ 2>/dev/null | head -50 || echo "(admin API non exposee)"

SEP "FIN"
echo "Diagnostic termine. Copie tout ce qui est au-dessus dans la conversation."
