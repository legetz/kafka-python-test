# GitHub Actions Setup Guide

This guide explains how to configure GitHub Actions for automated deployment of the Kafka Lambda Consumer across multiple environments.

## Architecture

```
Branch Strategy:
├── dev    → AWS Account (Dev)
├── test   → AWS Account (Test)
└── main   → AWS Account (Prod)
```

## Prerequisites

1. **Three AWS Accounts** (or one account with IAM role separation):
   - Development
   - Test
   - Production

2. **AWS IAM Roles** configured for GitHub Actions OIDC

3. **GitHub Repository** with admin access

## AWS Setup

### Step 1: Configure AWS IAM OIDC Provider

Run this **once per AWS account**:

```bash
# Set your AWS account ID
ACCOUNT_ID="123456789012"

# Create OIDC provider for GitHub Actions
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
  --client-id-list sts.amazonaws.com
```

### Step 2: Create IAM Role for GitHub Actions

Create a role in **each AWS account** (dev/test/prod):

```bash
# Save this as trust-policy.json
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_ORG/YOUR_REPO:*"
        }
      }
    }
  ]
}
EOF

# Replace ACCOUNT_ID and YOUR_GITHUB_ORG/YOUR_REPO
sed -i '' "s/ACCOUNT_ID/$ACCOUNT_ID/g" trust-policy.json
sed -i '' "s/YOUR_GITHUB_ORG\/YOUR_REPO/myorg\/kafka-python-test/g" trust-policy.json

# Create the role
aws iam create-role \
  --role-name GitHubActionsDeployRole \
  --assume-role-policy-document file://trust-policy.json \
  --description "Role for GitHub Actions to deploy CDK stacks"

# Attach policies (adjust as needed for your security requirements)
aws iam attach-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-arn arn:aws:iam::aws:policy/PowerUserAccess

# For CDK Bootstrap permissions
aws iam attach-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-arn arn:aws:iam::aws:policy/IAMFullAccess
```

**Note**: For production, use least-privilege policies instead of PowerUserAccess.

### Step 3: Bootstrap CDK in Each Account

```bash
# For each environment
cdk bootstrap aws://ACCOUNT_ID/us-east-1
```

## GitHub Secrets Configuration

### Required Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

#### AWS Account IDs

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `AWS_ACCOUNT_DEV` | AWS Account ID for dev environment | `111111111111` |
| `AWS_ACCOUNT_TEST` | AWS Account ID for test environment | `222222222222` |
| `AWS_ACCOUNT_PROD` | AWS Account ID for prod environment | `333333333333` |
| `AWS_DEPLOY_ROLE_NAME` | IAM role name for deployment | `GitHubActionsDeployRole` |

#### Kafka Configuration - Dev

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `KAFKA_BOOTSTRAP_SERVERS_DEV` | Kafka brokers for dev | `dev-kafka-1:9092,dev-kafka-2:9092` |
| `KAFKA_TOPIC_DEV` | Kafka topic for dev | `test-topic-dev` |

#### Kafka Configuration - Test

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `KAFKA_BOOTSTRAP_SERVERS_TEST` | Kafka brokers for test | `test-kafka-1:9092,test-kafka-2:9092` |
| `KAFKA_TOPIC_TEST` | Kafka topic for test | `test-topic-test` |

#### Kafka Configuration - Prod

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `KAFKA_BOOTSTRAP_SERVERS_PROD` | Kafka brokers for prod | `prod-kafka-1:9092,prod-kafka-2:9092` |
| `KAFKA_TOPIC_PROD` | Kafka topic for prod | `test-topic-prod` |

### Quick Setup Script

```bash
#!/bin/bash
# Add secrets to GitHub repository using gh CLI

# Install gh CLI: https://cli.github.com/

# AWS Account IDs
gh secret set AWS_ACCOUNT_DEV -b "111111111111"
gh secret set AWS_ACCOUNT_TEST -b "222222222222"
gh secret set AWS_ACCOUNT_PROD -b "333333333333"
gh secret set AWS_DEPLOY_ROLE_NAME -b "GitHubActionsDeployRole"

# Dev environment
gh secret set KAFKA_BOOTSTRAP_SERVERS_DEV -b "dev-kafka:9092"
gh secret set KAFKA_TOPIC_DEV -b "test-topic-dev"

# Test environment
gh secret set KAFKA_BOOTSTRAP_SERVERS_TEST -b "test-kafka:9092"
gh secret set KAFKA_TOPIC_TEST -b "test-topic-test"

# Prod environment
gh secret set KAFKA_BOOTSTRAP_SERVERS_PROD -b "prod-kafka:9092"
gh secret set KAFKA_TOPIC_PROD -b "test-topic-prod"
```

## GitHub Environments (Optional but Recommended)

Configure environments for deployment protection:

1. Go to Settings → Environments
2. Create three environments:
   - `dev` - No protection rules
   - `test` - Require reviewers (1 reviewer)
   - `prod` - Require reviewers (2 reviewers) + wait timer (5 min)

## Workflow Triggers

### Automatic Deployment

Push to any of these branches triggers automatic deployment:

```bash
# Deploy to dev
git push origin dev

# Deploy to test
git push origin test

# Deploy to prod
git push origin main
```

### Manual Deployment

Trigger manual deployment via GitHub UI:
1. Actions → Deploy Kafka Lambda Consumer
2. Run workflow → Select environment
3. Run workflow button

### Pull Request Validation

PRs to dev/test/main will:
- ✅ Run linting
- ✅ Build Lambda layer
- ✅ Synthesize CDK
- ❌ Skip deployment

## Workflow Jobs

The workflow consists of 6 jobs:

```
1. Setup         → Determine environment based on branch
2. Lint          → Run flake8, black, validate Python code
3. Build Layer   → Build Lambda layer, check size limits
4. Synth         → CDK synthesize CloudFormation template
5. Deploy        → Deploy to AWS (push events only)
6. Smoke Test    → Verify deployment, invoke Lambda
```

## Monitoring Deployments

### View Workflow Runs

```
GitHub → Actions → Deploy Kafka Lambda Consumer
```

### Check Job Summaries

Each deployment creates a summary with:
- Environment details
- Stack outputs
- Resource ARNs
- Deployment status

### View CloudWatch Logs

The smoke test job shows recent Lambda logs.

## Troubleshooting

### Error: "No valid credentials"

**Solution**: Ensure IAM role is created and trust policy allows your repository

```bash
# Check if role exists
aws iam get-role --role-name GitHubActionsDeployRole

# Update trust policy if needed
aws iam update-assume-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-document file://trust-policy.json
```

### Error: "Layer size exceeds limit"

**Solution**: Layer must be < 250MB unzipped

```bash
# Check layer size locally
cd lambda && ./build_layer.sh
du -sh layer/python
```

### Error: "Stack already exists"

**Solution**: Stack names are environment-specific. Check if stack exists:

```bash
aws cloudformation describe-stacks \
  --stack-name KafkaConsumerLambdaStack-dev
```

### Deployment Stuck on "Waiting"

**Solution**: Check GitHub Environment protection rules - may need approval

## Security Best Practices

1. **Use OIDC** instead of long-lived AWS credentials
2. **Least privilege** - Create custom IAM policies instead of PowerUserAccess
3. **Environment protection** - Require approvals for production
4. **Rotate secrets** - Update Kafka credentials regularly
5. **Audit logs** - Enable CloudTrail in all AWS accounts
6. **Branch protection** - Protect main/test branches
7. **Review PRs** - Require code reviews before merging

## Advanced Configuration

### Custom Stack Names

Edit `.github/workflows/deploy-lambda.yml`:

```yaml
echo "stack-name=MyCustomStack-$ENV" >> $GITHUB_OUTPUT
```

### Different AWS Regions

Update workflow:

```yaml
env:
  AWS_REGION: 'us-west-2'  # Change as needed
```

### Add More Environments

1. Create new branch (e.g., `staging`)
2. Add to workflow triggers
3. Add mapping in setup job
4. Create new secrets for the environment

### Notification Integration

Add notification steps to workflow:

```yaml
- name: Notify Slack
  if: success()
  run: |
    curl -X POST -H 'Content-type: application/json' \
      --data '{"text":"Deployment to ${{ env.ENVIRONMENT }} succeeded!"}' \
      ${{ secrets.SLACK_WEBHOOK_URL }}
```

## Cost Optimization

GitHub Actions minutes usage:
- Free tier: 2,000 minutes/month (public repos unlimited)
- Typical deployment: ~5 minutes
- Monthly cost: $0 (within free tier)

## Support

For issues with:
- **Workflow**: Check Actions logs and workflow YAML
- **AWS**: Verify IAM roles and permissions
- **CDK**: Check `cdk synth` output locally
- **Lambda**: Check CloudWatch Logs

## Rollback Procedure

If deployment fails:

```bash
# Revert to previous version
git revert HEAD
git push origin <branch>

# Or manually rollback via AWS Console
aws cloudformation update-stack \
  --stack-name KafkaConsumerLambdaStack-prod \
  --use-previous-template
```
