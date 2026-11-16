#!/usr/bin/env bash
# Runs ON the EC2 server, as root. deploy/deploy.sh starts it through SSM Run
# Command (no SSH) after copying this folder to /opt/budget/releases/<commit>/.
#
#   update.sh <commit> <image repository URI>
#
# 1. writes /opt/budget/.env: passwords from SSM Parameter Store, never from git
# 2. pulls the new API image, runs the migrations as the owner, restarts the API
# 3. checks /health through Caddy, the same way CloudFront reaches it
# 4. installs the nightly backup timer (idempotent)
set -euo pipefail

SHA=$1
REPO=$2
RELEASE_DIR=$(cd "$(dirname "$0")" && pwd)
APP_DIR=/opt/budget

# On a brand-new server, wait for the first boot (Docker, the data volume) to finish.
if ! cloud-init status --wait >/dev/null; then
  echo "The server's first boot failed. See /var/log/cloud-init-output.log on the server." >&2
  exit 1
fi

# AWS_REGION, OPS_BUCKET, ORIGIN_DOMAIN, ACME_EMAIL, LOG_GROUP, PARAM_PREFIX:
# written by the instance's first boot (deploy/cloudformation.yml, UserData).
# shellcheck source=/dev/null
source /etc/budget.env
export AWS_REGION

param() {
  aws ssm get-parameter --name "$PARAM_PREFIX/$1" --with-decryption --query Parameter.Value --output text
}

echo "== Config for $SHA"
mkdir -p "$APP_DIR"
umask 077 # .env holds passwords: readable by root only
ORIGIN_SECRET=$(param origin-secret)
cat > "$APP_DIR/.env" <<EOF
API_IMAGE=$REPO:$SHA
OWNER_DB_PASSWORD=$(param db-owner-password)
APP_DB_PASSWORD=$(param db-app-password)
ORIGIN_SECRET=$ORIGIN_SECRET
ORIGIN_DOMAIN=$ORIGIN_DOMAIN
ACME_EMAIL=$ACME_EMAIL
AWS_REGION=$AWS_REGION
LOG_GROUP=$LOG_GROUP
EOF
umask 022
cp "$RELEASE_DIR/compose.yml" "$RELEASE_DIR/Caddyfile" "$RELEASE_DIR/backup.sh" "$APP_DIR/"
chmod 700 "$APP_DIR/backup.sh"

echo "== Pull images"
aws ecr get-login-password | docker login --username AWS --password-stdin "${REPO%%/*}"
cd "$APP_DIR"
docker compose pull --quiet

echo "== Migrate (as the owner), then start"
docker compose up -d --wait db
docker compose run --rm migrate
docker compose up -d --remove-orphans
# Caddy reads its Caddyfile at start; reload it in case this release changed it.
docker compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile >/dev/null 2>&1 || docker compose restart caddy

echo "== Health check through Caddy"
# The first deploy waits here while Caddy gets its certificate (a minute or two).
for _ in $(seq 1 36); do
  if curl -fsS --max-time 5 --resolve "$ORIGIN_DOMAIN:443:127.0.0.1" \
      -H "X-Origin-Verify: $ORIGIN_SECRET" "https://$ORIGIN_DOMAIN/health"; then
    echo
    echo "== Backup timer"
    cat > /etc/systemd/system/budget-backup.service <<EOF
[Unit]
Description=Back up the budget database to S3

[Service]
Type=oneshot
ExecStart=$APP_DIR/backup.sh
EOF
    cat > /etc/systemd/system/budget-backup.timer <<EOF
[Unit]
Description=Nightly budget database backup

[Timer]
OnCalendar=*-*-* 07:00:00 UTC
RandomizedDelaySec=15min
Persistent=true

[Install]
WantedBy=timers.target
EOF
    systemctl daemon-reload
    systemctl enable --now budget-backup.timer >/dev/null
    docker image prune -af --filter "until=168h" >/dev/null || true # old images, after a week
    echo "== Deployed $SHA: healthy"
    exit 0
  fi
  sleep 5
done

echo "== Health check failed. Last logs:"
docker compose ps
docker compose logs --tail 40 api caddy
exit 1
