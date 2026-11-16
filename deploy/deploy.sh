#!/usr/bin/env bash
# Ships the last commit: the API to the server, then the React app to S3.
# Run from the repository root after deploy/setup.sh, with Docker running:
#
#   deploy/deploy.sh
#
# Takes about 3-5 minutes. The server keeps running the old version until the
# new one is pulled and migrated.
set -euo pipefail

export AWS_REGION=us-east-1
export AWS_PAGER=""
STACK=${STACK:-budget-app}

cd "$(git rev-parse --show-toplevel)"
if [ -n "$(git status --porcelain)" ]; then
  echo "Commit or stash your changes first: deploy ships the last commit, not your working files." >&2
  exit 1
fi
SHA=$(git rev-parse --short=12 HEAD)

output() {
  aws cloudformation describe-stacks --stack-name "$STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}
SITE_BUCKET=$(output SiteBucket)
OPS_BUCKET=$(output OpsBucket)
REPO=$(output RepositoryUri)
DISTRIBUTION=$(output DistributionId)
INSTANCE=$(output InstanceId)
echo "Deploying $SHA ($(git log -1 --format=%s))"

echo "== 1/4 API image → ECR"
aws ecr get-login-password | docker login --username AWS --password-stdin "${REPO%%/*}"
docker build --platform linux/arm64 -t "$REPO:$SHA" backend # the server is ARM (t4g)
docker push "$REPO:$SHA"

echo "== 2/4 Server: config files → S3, then update through SSM (no SSH)"
aws s3 cp --recursive --quiet deploy/server "s3://$OPS_BUCKET/releases/$SHA/"
# A brand-new server needs a minute or two before SSM can reach it.
for _ in $(seq 1 60); do
  PING=$(aws ssm describe-instance-information --filters "Key=InstanceIds,Values=$INSTANCE" \
    --query 'InstanceInformationList[0].PingStatus' --output text)
  [ "$PING" = "Online" ] && break
  echo "   waiting for the server to come online in SSM ($PING)"
  sleep 10
done
PARAMS=$(printf '{"commands": ["set -e", "aws s3 cp --recursive --quiet s3://%s/releases/%s/ /opt/budget/releases/%s/", "bash /opt/budget/releases/%s/update.sh %s %s"]}' \
  "$OPS_BUCKET" "$SHA" "$SHA" "$SHA" "$SHA" "$REPO")
COMMAND_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE" \
  --document-name AWS-RunShellScript \
  --comment "deploy $SHA" \
  --timeout-seconds 900 \
  --parameters "$PARAMS" \
  --query Command.CommandId --output text)
# Wait for the command to finish (up to 15 minutes), then show what it printed.
for _ in $(seq 1 180); do
  STATUS=$(aws ssm get-command-invocation --command-id "$COMMAND_ID" --instance-id "$INSTANCE" \
    --query Status --output text 2>/dev/null || echo Pending)
  case "$STATUS" in Pending | InProgress | Delayed) sleep 5 ;; *) break ;; esac
done
aws ssm get-command-invocation --command-id "$COMMAND_ID" --instance-id "$INSTANCE" \
  --query '[StandardOutputContent, StandardErrorContent]' --output text | tail -n 40
if [ "$STATUS" != "Success" ]; then
  echo "Server update failed ($STATUS). The React app was NOT deployed. Logs: deploy/README.md" >&2
  exit 1
fi

echo "== 3/4 React app → S3"
(cd frontend && npm ci --no-audit --no-fund && npm run build)
# File names in assets/ change with their content: cache them for a year.
aws s3 sync frontend/dist/assets "s3://$SITE_BUCKET/assets" --cache-control "public,max-age=31536000,immutable"
# index.html and friends: always check for a new version.
aws s3 sync frontend/dist "s3://$SITE_BUCKET" --exclude "assets/*" --cache-control "no-cache" --delete

echo "== 4/4 CloudFront: drop the cached index.html"
aws cloudfront create-invalidation --distribution-id "$DISTRIBUTION" --paths "/index.html" "/" \
  --query Invalidation.Id --output text

echo "Deployed $SHA: $(output Url)"
