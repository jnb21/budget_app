# Deploying on AWS

Phase 1 of [`docs/aws-architecture.html`](../docs/aws-architecture.html): Route 53 →
CloudFront, which serves the React app from a private S3 bucket and sends `/api/*`
to one EC2 server running Caddy, the API and Postgres in Docker Compose.

Three files do it all:

| File | Run | Does |
|---|---|---|
| `setup.sh` | once, and after changing `cloudformation.yml` | creates the secrets, then creates or updates the stack |
| `cloudformation.yml` | (by `setup.sh`) | every AWS resource: network, server, buckets, CloudFront, DNS, certificate, alarms, budget |
| `deploy.sh` | every release | API image → ECR → server (migrations, restart, health check); React app → S3 |

`server/` holds what runs on the server: `compose.yml`, `Caddyfile`, `update.sh`
(each deploy) and `backup.sh` (nightly).

## Before you start (once)

1. **An AWS account**, and the **AWS CLI v2** signed in with an admin user or role:
   `aws sts get-caller-identity` should print your account.
2. **A domain in Route 53.** Register one in Route 53 (a hosted zone is created for
   you), or create a hosted zone for a domain you own elsewhere and set the
   registrar's name servers to the four the zone lists. Then copy the zone's
   **Hosted zone ID** (Route 53 → Hosted zones).
3. **Docker Desktop** running (deploy builds the API image) and Node, as for local
   development.

Everything goes in **us-east-1** (N. Virginia): CloudFront's certificate must be
there, and Bedrock offers the most models there.

## First deploy

```bash
DOMAIN=budget.example.com HOSTED_ZONE_ID=Z0123456789ABC ALERT_EMAIL=you@example.com deploy/setup.sh
```

Takes 15–25 minutes, mostly CloudFront. Then:

```bash
deploy/deploy.sh
```

The first one waits a minute or two on the server while Caddy gets its certificate
from Let's Encrypt. Then open `https://budget.example.com` and sign up. There is no
demo data in production: never run the seed script there.

## Every change after that

Commit, then:

```bash
deploy/deploy.sh
```

It ships the last commit (it refuses to run with uncommitted changes), in this order:
API image, server update (migrations run before the new API starts), then the React
app. If the server update fails, the React app isn't deployed and the server keeps
the old API running.

Changed `cloudformation.yml`? Run `setup.sh` again with the same three variables.

## Looking at the server

No SSH: port 22 isn't open. Use Session Manager (install the
[Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) once):

```bash
aws ssm start-session --region us-east-1 --target "$(aws cloudformation describe-stacks --region us-east-1 --stack-name budget-app --query "Stacks[0].Outputs[?OutputKey=='InstanceId'].OutputValue" --output text)"
```

On the server: `sudo -i`, `cd /opt/budget`, then `docker compose ps` or
`docker compose logs --tail 100 api`.

Logs also go to CloudWatch, from your laptop:

```bash
aws logs tail /budget-app/server --region us-east-1 --follow
```

## Backups and restoring

- **Nightly `pg_dump`** to the ops bucket, `backups/`, kept 35 days (`server/backup.sh`).
- **Daily snapshots** of the data volume, kept 7 days.
- **Deleting the stack** keeps a final snapshot of the data volume and the ops bucket.

Restore a dump, on the server (Session Manager, then `sudo -i`):

```bash
cd /opt/budget && source /etc/budget.env
aws s3 ls "s3://$OPS_BUCKET/backups/"                     # pick one
aws s3 cp "s3://$OPS_BUCKET/backups/budget-2026-11-20T0700Z.dump" /tmp/restore.dump
docker compose stop api
docker compose exec -T db pg_restore -U budget -d budget --clean --if-exists < /tmp/restore.dump
docker compose start api
```

Try it once before you need it.

## What it costs

Roughly **$20 a month** in us-east-1 with little traffic: the t4g.small server (~$12),
two 20 GB disks (~$3), the public IPv4 address (~$3.60), the hosted zone ($0.50), and
cents for S3, snapshots, logs and ECR. CloudFront's free tier covers a small app.
These are estimates; check the [AWS Pricing Calculator](https://calculator.aws/).
The stack sets a $30 monthly budget that emails `ALERT_EMAIL` at 80% (change it with
`MONTHLY_BUDGET_USD=50 deploy/setup.sh ...`). Bedrock adds per-token charges once
the AI is built.

## Security, in short

- Only CloudFront can reach the server: port 443 is limited to CloudFront's addresses,
  and Caddy also requires a secret header CloudFront adds (403 without it). Port 80
  only serves Let's Encrypt and redirects.
- The API and Postgres have no public ports at all; only Caddy does.
- Passwords live in SSM Parameter Store (`/budget/*`, encrypted), are read by the
  server's IAM role at deploy time, and are never in git or on your laptop's disk.
  The running API only gets the app login; the owner password only reaches the
  migration step.
- The visitor's IP: a CloudFront Function puts it in `X-Viewer-Ip` (overwriting
  anything the visitor sent), Caddy passes it on as `X-Forwarded-For`, so the rate
  limits count each visitor separately.
- The S3 bucket is private; only this CloudFront distribution can read it.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `setup.sh` fails on the server: instance type not supported in the zone | Run it again with `AVAILABILITY_ZONE=us-east-1b` (only before the first success: moving zones replaces the data disk) |
| Stack stuck on the certificate | The hosted zone isn't the one the internet uses: check the registrar's name servers |
| First `deploy.sh` fails its health check | Caddy couldn't get a certificate: `origin.<domain>` must point at the server and port 80 must be open; see `docker compose logs caddy` |
| The site loads but every action fails (502) | The API or Caddy is down: `docker compose ps` on the server |
| `/api/...` answers 403 "Forbidden" | The secret header doesn't match: run `setup.sh` again, then `deploy.sh` |

## Not here yet

- **The AI worker**: it joins `server/compose.yml` when the AI phase builds it. The
  server's IAM role can already call Bedrock.
- **Deploys from GitHub Actions**: the same steps as `deploy.sh`, with an OIDC role
  instead of your laptop's credentials.

## Tearing it down

```bash
aws cloudformation delete-stack --region us-east-1 --stack-name budget-app
```

Kept on purpose: the ops bucket (backups) and a final snapshot of the data disk.
Delete those and the `/budget/*` parameters by hand if you really want everything gone.
