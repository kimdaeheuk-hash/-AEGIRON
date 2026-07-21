#!/usr/bin/env bash
# 로컬 머신(사용자 PC)에서 실행하는 운영 DB 백업 스크립트.
#
# 왜 필요한가: Railway 같은 컨테이너 배포 환경은 영구 볼륨을 마운트하지
# 않으면 재배포할 때마다 파일시스템이 초기화될 수 있다. 그러면 시간이
# 지나야 쌓이는 자산(예측 트랙레코드, 검증 이력, 추출된 신호 등)이 전부
# 사라진다 — 이 세션(샌드박스)은 Railway 대시보드에 접근할 수 없어 볼륨
# 설정 여부를 직접 확인할 수 없으므로, 대신 이 스크립트로 주기적인 백업을
# "로컬에서" 만들어두는 안전장치를 둔다. main.py의 GET /api/admin/db-backup
# 엔드포인트(인증 필요)를 호출해 sqlite3 backup API로 뜬 일관된 스냅샷을
# 내려받는다.
#
# 사용법:
#   EPIWEATHER_API_URL=https://<배포된 도메인> EPIWEATHER_API_KEY=<키> \
#     ./scripts/backup_db.sh
#
# cron 예시(매일 새벽 3시):
#   0 3 * * * EPIWEATHER_API_URL=https://... EPIWEATHER_API_KEY=... \
#     /path/to/epiweather-api/scripts/backup_db.sh >> /path/to/backup.log 2>&1

set -euo pipefail

API_URL="${EPIWEATHER_API_URL:-http://localhost:8000}"
API_KEY="${EPIWEATHER_API_KEY:?EPIWEATHER_API_KEY 환경변수를 설정하세요 (.env의 값과 동일)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/../data/backups"
KEEP=30  # 최근 30개만 보관(디스크 무한 증식 방지)

mkdir -p "${BACKUP_DIR}"
stamp="$(date -u +%Y%m%d_%H%M%S)"
out_file="${BACKUP_DIR}/epiweather_backup_${stamp}.db"

echo "백업 요청: ${API_URL}/api/admin/db-backup"
curl -fsS -H "X-API-Key: ${API_KEY}" "${API_URL}/api/admin/db-backup" -o "${out_file}"

size="$(du -h "${out_file}" | cut -f1)"
echo "완료: ${out_file} (${size})"

# 오래된 백업 정리
ls -1t "${BACKUP_DIR}"/epiweather_backup_*.db 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f
count="$(ls -1 "${BACKUP_DIR}"/epiweather_backup_*.db 2>/dev/null | wc -l)"
echo "보관 중인 백업: ${count}개 (최근 ${KEEP}개까지 유지)"
