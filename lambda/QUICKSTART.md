# Quick Start Guide

## Prerequisites
```bash
# Install CDK CLI
npm install -g aws-cdk

# Configure AWS credentials
aws configure
```

## Deploy in 3 Steps

### 1. Install Dependencies
```bash
cd lambda
make install
```

### 2. Set Environment Variables
```bash
export KAFKA_BOOTSTRAP_SERVERS="your-kafka-broker:9092"
export KAFKA_TOPIC="test-topic"
export CDK_DEFAULT_ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
export CDK_DEFAULT_REGION="us-east-1"
```

### 3. Build and Deploy
```bash
make all
```

That's it! Your Lambda will start running every minute.

## Useful Commands

```bash
# View logs in real-time
make logs

# Check stored offsets
make list-offsets

# View stack differences before deploying
make diff

# Destroy everything
make destroy

# Clean build artifacts
make clean
```

## Makefile Targets

```bash
make help              # Show all available commands
make install           # Install CDK dependencies
make build-layer       # Build Lambda layer
make deploy            # Deploy stack
make diff              # Show changes
make destroy           # Delete stack
make logs              # Tail Lambda logs
make list-offsets      # Show DynamoDB offsets
make clean             # Clean artifacts
```

## Architecture

```
EventBridge (every minute)
    ↓
Lambda Function (with Layer)
    ↓
Kafka Cluster ← DynamoDB (offsets)
    ↓
Process up to 1000 messages
```

## What Gets Deployed

- ✅ Lambda Layer with confluent-kafka
- ✅ Lambda Function (512MB, 5min timeout)
- ✅ DynamoDB Table for offsets
- ✅ EventBridge Rule (cron: every minute)
- ✅ CloudWatch Logs (1-week retention)
- ✅ IAM Roles & Permissions

## Costs

Estimated ~$1-3/month:
- Lambda: ~43,200 invocations/month
- DynamoDB: Pay-per-request
- CloudWatch: Logs storage
- EventBridge: Free tier covers it

## Troubleshooting

**Layer too large?**
```bash
make clean-layer
make build-layer
```

**Need to update dependencies?**
Edit `layer/requirements.txt`, then:
```bash
make build-layer
make deploy
```

**Lambda timeout?**
Reduce `MAX_MESSAGES` in `cdk_app/kafka_consumer_stack.py`

## Monitoring

```bash
# CloudWatch Console
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=kafka-consumer-lambda \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum

# DynamoDB items
aws dynamodb scan --table-name kafka-consumer-offsets --output table
```
