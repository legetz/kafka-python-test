# GitHub Secrets Quick Reference

Copy and paste these commands to set up your secrets using GitHub CLI (`gh`).

## Installation

```bash
# Install GitHub CLI
brew install gh  # macOS
# or visit: https://cli.github.com/

# Login
gh auth login
```

## Set All Secrets

```bash
#!/bin/bash
# Run this script to set all required secrets at once

# AWS Account IDs (replace with your actual account IDs)
gh secret set AWS_ACCOUNT_DEV --body "111111111111"
gh secret set AWS_ACCOUNT_TEST --body "222222222222"
gh secret set AWS_ACCOUNT_PROD --body "333333333333"

# IAM Role Name (same across all accounts)
gh secret set AWS_DEPLOY_ROLE_NAME --body "GitHubActionsDeployRole"

# Dev Environment
gh secret set KAFKA_BOOTSTRAP_SERVERS_DEV --body "dev-kafka-broker:9092"
gh secret set KAFKA_TOPIC_DEV --body "test-topic-dev"

# Test Environment
gh secret set KAFKA_BOOTSTRAP_SERVERS_TEST --body "test-kafka-broker:9092"
gh secret set KAFKA_TOPIC_TEST --body "test-topic-test"

# Prod Environment
gh secret set KAFKA_BOOTSTRAP_SERVERS_PROD --body "prod-kafka-broker:9092"
gh secret set KAFKA_TOPIC_PROD --body "test-topic-prod"

echo "✅ All secrets configured!"
```

## List All Secrets
- `gh secret list`

## Secrets Mapping

| Secret Name | Used In | Example Value |
|------------|---------|---------------|
| `AWS_ACCOUNT_DEV` | dev branch deployments | `111111111111` |
| `AWS_ACCOUNT_TEST` | test branch deployments | `222222222222` |
| `AWS_ACCOUNT_PROD` | main branch deployments | `333333333333` |
| `AWS_DEPLOY_ROLE_NAME` | All deployments | `GitHubActionsDeployRole` |
| `KAFKA_BOOTSTRAP_SERVERS_DEV` | Lambda env var (dev) | `kafka-dev:9092` |
| `KAFKA_BOOTSTRAP_SERVERS_TEST` | Lambda env var (test) | `kafka-test:9092` |
| `KAFKA_BOOTSTRAP_SERVERS_PROD` | Lambda env var (prod) | `kafka-prod:9092` |
| `KAFKA_TOPIC_DEV` | Lambda env var (dev) | `events-dev` |
| `KAFKA_TOPIC_TEST` | Lambda env var (test) | `events-test` |
| `KAFKA_TOPIC_PROD` | Lambda env var (prod) | `events-prod` |

## Update Individual Secret

```bash
# Update a specific secret
gh secret set KAFKA_TOPIC_PROD --body "new-topic-name"

# Set from file
gh secret set KAFKA_BOOTSTRAP_SERVERS_DEV < kafka-servers-dev.txt
```

## Environment Variables in Workflow

The workflow automatically sets these environment variables for Lambda:

```yaml
# Dev deployment
KAFKA_BOOTSTRAP_SERVERS: ${{ secrets.KAFKA_BOOTSTRAP_SERVERS_DEV }}
KAFKA_TOPIC: ${{ secrets.KAFKA_TOPIC_DEV }}

# Test deployment
KAFKA_BOOTSTRAP_SERVERS: ${{ secrets.KAFKA_BOOTSTRAP_SERVERS_TEST }}
KAFKA_TOPIC: ${{ secrets.KAFKA_TOPIC_TEST }}

# Prod deployment
KAFKA_BOOTSTRAP_SERVERS: ${{ secrets.KAFKA_BOOTSTRAP_SERVERS_PROD }}
KAFKA_TOPIC: ${{ secrets.KAFKA_TOPIC_PROD }}
```

## Security Notes

- ✅ Secrets are encrypted at rest
- ✅ Only accessible during workflow execution
- ✅ Not visible in logs
- ✅ Can be rotated without code changes
- ⚠️ Use AWS OIDC (no long-lived credentials needed)
- ⚠️ Limit repository access to trusted collaborators

## Troubleshooting

### Secret not found

```bash
# Check if secret exists
gh secret list | grep SECRET_NAME

# If missing, set it
gh secret set SECRET_NAME --body "value"
```

### Wrong secret value

```bash
# Delete and recreate
gh secret remove SECRET_NAME
gh secret set SECRET_NAME --body "correct-value"
```

### Test secrets locally (DO NOT commit!)

```bash
# Create .env file (gitignored)
cat > .env <<EOF
AWS_ACCOUNT_DEV=111111111111
AWS_ACCOUNT_TEST=222222222222
AWS_ACCOUNT_PROD=333333333333
KAFKA_BOOTSTRAP_SERVERS_DEV=dev-kafka:9092
KAFKA_TOPIC_DEV=test-topic-dev
EOF

# Source in your shell
source .env
```
