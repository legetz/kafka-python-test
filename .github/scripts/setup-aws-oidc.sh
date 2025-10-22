#!/bin/bash

# Setup AWS OIDC Provider and IAM Role for GitHub Actions
# Usage: ./setup-aws-oidc.sh <github-org> <repo-name> <aws-account-id>

set -e

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <github-org> <repo-name> <aws-account-id>"
    echo "Example: $0 myorg kafka-python-test 123456789012"
    exit 1
fi

GITHUB_ORG=$1
REPO_NAME=$2
ACCOUNT_ID=$3
ROLE_NAME="GitHubActionsDeployRole"

echo "🔧 Setting up AWS OIDC for GitHub Actions"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "AWS Account: $ACCOUNT_ID"
echo "Repository: $GITHUB_ORG/$REPO_NAME"
echo "Role Name: $ROLE_NAME"
echo ""

# Check if OIDC provider already exists
echo "📝 Checking for existing OIDC provider..."
PROVIDER_ARN="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"

if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$PROVIDER_ARN" 2>/dev/null; then
    echo "✅ OIDC provider already exists"
else
    echo "🔨 Creating OIDC provider..."
    aws iam create-open-id-connect-provider \
        --url https://token.actions.githubusercontent.com \
        --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
        --client-id-list sts.amazonaws.com
    echo "✅ OIDC provider created"
fi

# Create trust policy
echo "📝 Creating trust policy..."
TRUST_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG}/${REPO_NAME}:*"
        }
      }
    }
  ]
}
EOF
)

echo "$TRUST_POLICY" > /tmp/trust-policy.json

# Check if role already exists
echo "📝 Checking for existing IAM role..."
if aws iam get-role --role-name "$ROLE_NAME" 2>/dev/null; then
    echo "⚠️  Role already exists. Updating trust policy..."
    aws iam update-assume-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-document file:///tmp/trust-policy.json
    echo "✅ Trust policy updated"
else
    echo "🔨 Creating IAM role..."
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --description "Role for GitHub Actions to deploy CDK stacks for ${GITHUB_ORG}/${REPO_NAME}"
    echo "✅ IAM role created"
    
    # Attach policies
    echo "🔨 Attaching IAM policies..."
    
    # For CDK deployments (use least privilege in production!)
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn arn:aws:iam::aws:policy/PowerUserAccess
    
    # For IAM operations (needed by CDK)
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn arn:aws:iam::aws:policy/IAMFullAccess
    
    echo "✅ Policies attached"
    
    echo ""
    echo "⚠️  WARNING: PowerUserAccess and IAMFullAccess are used for convenience."
    echo "    For production, create a custom policy with least privilege."
fi

# Clean up
rm /tmp/trust-policy.json

echo ""
echo "✅ Setup complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Next steps:"
echo "1. Run this script in TEST and PROD accounts too"
echo "2. Set GitHub secrets:"
echo "   gh secret set AWS_ACCOUNT_DEV --body '$ACCOUNT_ID'"
echo "   gh secret set AWS_DEPLOY_ROLE_NAME --body '$ROLE_NAME'"
echo "3. Bootstrap CDK:"
echo "   cdk bootstrap aws://$ACCOUNT_ID/us-east-1"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
