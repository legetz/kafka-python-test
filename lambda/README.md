# Lambda Kafka Consumer with CDK

AWS CDK infrastructure for deploying a serverless Kafka consumer Lambda function with DynamoDB offset persistence and a custom Lambda layer for dependencies.

## Architecture

This solution deploys:

- **Lambda Layer**: Contains confluent-kafka library and dependencies (optimized for size)
- **Lambda Function**: Python-based Kafka consumer that processes up to 1000 messages per execution
- **DynamoDB Table**: Stores Kafka partition offsets for reliable message processing
- **EventBridge Rule**: Triggers the Lambda function every minute via CloudWatch cron schedule
- **CloudWatch Logs**: Captures Lambda execution logs for monitoring and debugging

## Features

- ✅ Serverless Kafka consumer with automatic scaling
- ✅ Lambda Layer for efficient dependency management
- ✅ Offset persistence in DynamoDB for exactly-once processing semantics
- ✅ Scheduled execution every minute via EventBridge
- ✅ Configurable message batch size (default: 1000 messages)
- ✅ Comprehensive error handling and logging
- ✅ Production-ready IAM permissions

## Prerequisites

- Python 3.11 or higher
- Node.js 14.x or higher (for AWS CDK CLI)
- AWS CLI configured with appropriate credentials
- Access to a Kafka cluster (broker addresses)
- AWS CDK CLI installed: `npm install -g aws-cdk`

## Project Structure

```
lambda/
├── app.py                      # CDK app entry point
├── cdk.json                    # CDK configuration
├── requirements.txt            # CDK dependencies
├── Makefile                    # Build and deployment automation
├── build_layer.sh              # Script to build Lambda layer
├── cdk_app/
│   ├── __init__.py
│   └── kafka_consumer_stack.py # CDK stack definition
├── layer/
│   ├── requirements.txt        # Layer dependencies
│   └── python/                 # Built layer (created by build script)
└── lambda_function/
    ├── handler.py              # Lambda handler code
    └── requirements.txt        # Lambda runtime dependencies (empty - uses layer)
```

## Configuration

### Environment Variables

Set these before deploying:

```bash
export KAFKA_BOOTSTRAP_SERVERS="your-kafka-broker:9092"
export KAFKA_TOPIC="your-topic-name"
export CDK_DEFAULT_ACCOUNT="your-aws-account-id"
export CDK_DEFAULT_REGION="us-east-1"
```

### Lambda Configuration (in stack)

- **Timeout**: 5 minutes
- **Memory**: 512 MB
- **Max Messages**: 1000 per execution
- **Poll Timeout**: 5 seconds
- **Runtime**: Python 3.11

## Installation

1. **Install CDK dependencies**:
   ```bash
   cd lambda
   pip install -r requirements.txt
   ```

2. **Build the Lambda layer**:
   ```bash
   make build-layer
   # Or manually:
   ./build_layer.sh
   ```

   This will install confluent-kafka and its dependencies in the correct format for Lambda layers.

## Deployment

### Using Makefile (Recommended)

1. **Build and deploy in one command**:
   ```bash
   make all
   ```

   Or step by step:

2. **Build Lambda layer**:
   ```bash
   make build-layer
   ```

3. **Deploy the stack**:
   ```bash
   make deploy
   ```

### Using CDK CLI

1. **Bootstrap CDK** (first time only):
   ```bash
   cdk bootstrap aws://ACCOUNT-ID/REGION
   ```

2. **Build the layer first**:
   ```bash
   ./build_layer.sh
   ```

3. **Synthesize CloudFormation template**:
   ```bash
   cdk synth
   ```

4. **Deploy the stack**:
   ```bash
   cdk deploy
   ```

5. **View outputs**:
   After deployment, note the outputs:
   - Lambda layer ARN
   - Lambda function name
   - DynamoDB table name
   - EventBridge rule name
   - CloudWatch Log Group name

## Monitoring

### CloudWatch Logs

View Lambda execution logs:
```bash
make logs
# Or manually:
aws logs tail /aws/lambda/kafka-consumer-lambda --follow
```

### DynamoDB Offsets

Query stored offsets:
```bash
make list-offsets
# Or manually:
aws dynamodb scan --table-name kafka-consumer-offsets
```

### Lambda Metrics

Monitor in CloudWatch:
- Invocations
- Duration
- Errors
- Throttles

## Customization

### Change Schedule

Edit `kafka_consumer_stack.py` to modify the cron schedule:

```python
schedule=events.Schedule.cron(
    minute="*/5",  # Every 5 minutes
    # ... other parameters
)
```

### Adjust Message Processing Limit

Update the `MAX_MESSAGES` environment variable in the stack:

```python
"MAX_MESSAGES": "2000",  # Process up to 2000 messages
```

### Add VPC Configuration

If your Kafka cluster is in a VPC, uncomment and configure the VPC settings in `kafka_consumer_stack.py`.

### Update Layer Dependencies

To add or update dependencies in the Lambda layer:

1. Edit `layer/requirements.txt`
2. Rebuild the layer:
   ```bash
   make build-layer
   ```
3. Redeploy:
   ```bash
   make deploy
   ```

## Testing Locally

You can test the Lambda function locally by invoking the handler:

```python
from lambda_function.handler import lambda_handler

event = {}
context = None
result = lambda_handler(event, context)
print(result)
```

## Cleanup

To destroy all resources:

```bash
make destroy
# Or manually:
cdk destroy
```

To clean build artifacts:

```bash
make clean
```

**Note**: The DynamoDB table has `RETAIN` removal policy to prevent accidental data loss. You'll need to manually delete it if desired.

## Cost Considerations

- **Lambda**: Pay per invocation and execution time
  - ~43,200 invocations/month (every minute)
  - ~$0.50-$2/month depending on execution time
- **DynamoDB**: Pay-per-request pricing
  - Minimal cost for offset storage
- **EventBridge**: Free (first 1M events/month)
- **CloudWatch Logs**: Pay for storage and ingestion
  - 1-week retention configured

## Troubleshooting

### Lambda Timeout

If processing takes longer than 5 minutes, reduce `MAX_MESSAGES` or increase timeout.

### Connection Issues

Ensure:
- Lambda has network access to Kafka brokers
- Security groups allow traffic
- VPC configuration is correct (if applicable)

### Layer Build Issues

If layer build fails:
```bash
# Clean and rebuild
make clean-layer
make build-layer
```

For macOS users: The build script uses `--platform manylinux2014_x86_64` to ensure compatibility with Lambda's Linux environment.

### Layer Size Limit

Lambda layers have a 250MB unzipped size limit. The confluent-kafka library is large (~50MB). If you exceed limits:
- Remove unused dependencies
- Use the build script's cleanup steps
- Consider splitting into multiple layers

### Offset Issues

Check DynamoDB table for stored offsets:
```bash
aws dynamodb get-item \
  --table-name kafka-consumer-offsets \
  --key '{"consumer_id":{"S":"lambda-consumer-group_test-topic"},"partition":{"N":"0"}}'
```

## Security Best Practices

- ✅ Lambda uses IAM roles (no hardcoded credentials)
- ✅ DynamoDB uses fine-grained IAM permissions
- ✅ CloudWatch Logs enabled for audit trail
- ✅ No publicly exposed resources
- ⚠️ Consider encrypting DynamoDB table at rest
- ⚠️ Use AWS Secrets Manager for sensitive Kafka credentials

## License

This project is provided as-is for demonstration purposes.
