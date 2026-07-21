#!/usr/bin/env bash
# Windows 작업 스케줄러 전용 래퍼. .env에서 키를 읽어 backup_db.sh를 실행하고
# 결과를 data/backups/backup.log에 남긴다.
#
# Task Scheduler는 bash.exe를 non-login으로 직접 실행해서 /etc/profile이
# 안 읽히고 PATH가 비어 dirname/curl 등을 못 찾는 문제가 있어, PATH를
# 명시적으로 잡고 경로도 하드코딩함(이 스크립트는 스케줄러 전용이라 이식성 불필요).
export PATH="/usr/bin:/mingw64/bin:${PATH}"
set -euo pipefail

cd "/c/Users/NT371B5L/네오테라/epiweather-api"

set -a
source .env
set +a

export EPIWEATHER_API_URL="https://epiweather-api-production.up.railway.app"

mkdir -p data/backups
{
  echo "===== $(date -u +%Y-%m-%dT%H:%M:%SZ) ====="
  bash scripts/backup_db.sh
} >> data/backups/backup.log 2>&1
