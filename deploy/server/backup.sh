#!/usr/bin/env bash
# Runs ON the server every night (systemd timer budget-backup.timer, installed
# by update.sh): a full pg_dump of the database, streamed straight to S3.
# The ops bucket deletes backups after 35 days. Restore: deploy/README.md.
set -euo pipefail
# shellcheck source=/dev/null
source /etc/budget.env
export AWS_REGION

STAMP=$(date -u +%Y-%m-%dT%H%MZ)
cd /opt/budget
docker compose exec -T db pg_dump -U budget -d budget --format=custom \
  | aws s3 cp - "s3://$OPS_BUCKET/backups/budget-$STAMP.dump"
echo "backup budget-$STAMP.dump uploaded"
