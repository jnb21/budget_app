#!/usr/bin/env bash
# Creates the AWS side of the app, or updates it after deploy/cloudformation.yml
# changes. Run from the repository root, signed in to AWS (aws sts get-caller-identity):
#
#   DOMAIN=budget.example.com HOSTED_ZONE_ID=Z0123456789ABC ALERT_EMAIL=you@example.com deploy/setup.sh
#
# Safe to run again: secrets are only created when missing, and the stack is
# updated in place. The first run takes 15-25 minutes, mostly CloudFront.
set -euo pipefail

export AWS_REGION=us-east-1 # CloudFront's certificate must live here; so does everything else
export AWS_PAGER=""
STACK=${STACK:-budget-app}
PARAM_PREFIX=/budget # the server's role may read /budget/* and nothing else

: "${DOMAIN:?Set DOMAIN, e.g. DOMAIN=budget.example.com}"
: "${HOSTED_ZONE_ID:?Set HOSTED_ZONE_ID: Route 53 > Hosted zones > your domain > Hosted zone ID}"
: "${ALERT_EMAIL:?Set ALERT_EMAIL: budget alerts and certificate notices go there}"

cd "$(git rev-parse --show-toplevel)"
echo "AWS account: $(aws sts get-caller-identity --query Account --output text), region $AWS_REGION, stack $STACK"

echo "== 1/3 Secrets in SSM Parameter Store (encrypted, created once)"
ensure_secret() {
  if aws ssm get-parameter --name "$PARAM_PREFIX/$1" >/dev/null 2>&1; then
    echo "   $PARAM_PREFIX/$1: exists"
  else
    # hex: safe inside database URLs and HTTP headers without escaping
    aws ssm put-parameter --name "$PARAM_PREFIX/$1" --type SecureString \
      --value "$(openssl rand -hex 24)" >/dev/null
    echo "   $PARAM_PREFIX/$1: created"
  fi
}
ensure_secret db-owner-password # Postgres owner: migrations only
ensure_secret db-app-password   # the app's login (row-level security applies)
ensure_secret origin-secret     # header CloudFront sends so the server knows it's CloudFront
ORIGIN_SECRET=$(aws ssm get-parameter --name "$PARAM_PREFIX/origin-secret" --with-decryption \
  --query Parameter.Value --output text)

echo "== 2/3 Values the stack needs"
PREFIX_LIST=$(aws ec2 describe-managed-prefix-lists \
  --filters Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing \
  --query 'PrefixLists[0].PrefixListId' --output text)
echo "   CloudFront prefix list: $PREFIX_LIST"
overrides=(
  "DomainName=$DOMAIN"
  "HostedZoneId=$HOSTED_ZONE_ID"
  "AlertEmail=$ALERT_EMAIL"
  "CloudFrontPrefixListId=$PREFIX_LIST"
  "OriginSecret=$ORIGIN_SECRET"
)
if ! aws cloudformation describe-stacks --stack-name "$STACK" >/dev/null 2>&1; then
  # Chosen once. Later runs keep this image: a new one would replace the server.
  AMI=$(aws ssm get-parameter --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64 \
    --query Parameter.Value --output text)
  echo "   server image (first run): $AMI"
  overrides+=("ImageId=$AMI")
fi
[ -n "${INSTANCE_TYPE:-}" ] && overrides+=("InstanceType=$INSTANCE_TYPE")
[ -n "${AVAILABILITY_ZONE:-}" ] && overrides+=("AvailabilityZone=$AVAILABILITY_ZONE")
[ -n "${MONTHLY_BUDGET_USD:-}" ] && overrides+=("MonthlyBudgetUsd=$MONTHLY_BUDGET_USD")

echo "== 3/3 CloudFormation stack (watch it in the console: CloudFormation > $STACK)"
aws cloudformation deploy \
  --stack-name "$STACK" \
  --template-file deploy/cloudformation.yml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides "${overrides[@]}" \
  --no-fail-on-empty-changeset

aws cloudformation describe-stacks --stack-name "$STACK" \
  --query 'Stacks[0].Outputs[].[OutputKey,OutputValue]' --output table
echo "Done. Next: deploy/deploy.sh"
