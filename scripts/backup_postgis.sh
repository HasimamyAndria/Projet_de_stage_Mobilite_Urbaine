# Backup PostGIS minimal (Docker Compose)
# Usage (bash / Git Bash) :
#   ./scripts/backup_postgis.sh
# Sortie : backups/mobilite_YYYYMMDD_HHMM.dump

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/backups"
STAMP="$(date +%Y%m%d_%H%M)"
OUT="$ROOT/backups/mobilite_${STAMP}.dump"

DB_NAME="${DB_NAME:-mobilite}"
DB_USER="${DB_USER:-mobilite}"

echo "Backup -> $OUT"
docker compose -f "$ROOT/docker-compose.yml" exec -T db \
  pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc > "$OUT"

echo "OK ($(du -h "$OUT" | cut -f1))"
