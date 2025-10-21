# Lambda Kafka Consumer Architecture

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      AWS Cloud Environment                       │
│                                                                  │
│  ┌────────────────┐         ┌──────────────────────────────┐   │
│  │  EventBridge   │         │      Lambda Function         │   │
│  │  (CloudWatch   │────────▶│  kafka-consumer-lambda       │   │
│  │  Events)       │  every  │                              │   │
│  │                │  minute │  ┌────────────────────────┐  │   │
│  │  Cron: * * * * │         │  │  Lambda Layer          │  │   │
│  └────────────────┘         │  │  - confluent-kafka     │  │   │
│                              │  │  - Python 3.11         │  │   │
│                              │  └────────────────────────┘  │   │
│                              │                              │   │
│                              │  Runtime: Python 3.11        │   │
│                              │  Memory: 512 MB              │   │
│                              │  Timeout: 5 minutes          │   │
│                              └───────┬──────────────────────┘   │
│                                      │                          │
│                          ┌───────────┼───────────┐              │
│                          ▼           ▼           ▼              │
│                  ┌───────────┐  ┌─────────┐  ┌──────────┐      │
│                  │ DynamoDB  │  │  Kafka  │  │CloudWatch│      │
│                  │  Table    │  │ Cluster │  │   Logs   │      │
│                  │           │  │ (MSK or │  │          │      │
│                  │ Offsets:  │  │  self-  │  │ 1-week   │      │
│                  │ - consumer│  │ hosted) │  │retention │      │
│                  │ - partition│ │         │  │          │      │
│                  │ - offset  │  │         │  │          │      │
│                  └───────────┘  └─────────┘  └──────────┘      │
│                       ▲             │                           │
│                       │             │                           │
│                       └─────────────┘                           │
│                    Read offset,                                 │
│                    Process messages,                            │
│                    Save new offset                              │
└─────────────────────────────────────────────────────────────────┘

                    ▲                      ▲
                    │                      │
             Kafka Broker            Kafka Broker
          (External or MSK)       (External or MSK)
```

## Data Flow

1. **Trigger (Every Minute)**
   ```
   EventBridge Rule → Invokes Lambda
   ```

2. **Read Last Offset**
   ```
   Lambda → Query DynamoDB for partition offsets
   Key: {consumer_id: "lambda-consumer-group_test-topic", partition: 0}
   Response: {offset: 12345}
   ```

3. **Consume Messages**
   ```
   Lambda → Connect to Kafka
   Lambda → Seek to offset 12346 (last + 1)
   Lambda → Poll up to 1000 messages
   Lambda → Process each message
   ```

4. **Save New Offset**
   ```
   Lambda → Put item to DynamoDB
   {
     consumer_id: "lambda-consumer-group_test-topic",
     partition: 0,
     offset: 13345,
     topic: "test-topic",
     group_id: "lambda-consumer-group"
   }
   ```

5. **Logging**
   ```
   All operations → CloudWatch Logs
   Log Group: /aws/lambda/kafka-consumer-lambda
   ```

## Message Processing Flow

```
┌─────────────┐
│   Start     │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ Query DynamoDB for  │
│ last offset         │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Connect to Kafka    │
│ Seek to offset+1    │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Poll messages       │
│ (max 1000)          │
└──────┬──────────────┘
       │
       ▼
     ┌─┴─┐
     │ ? │ Messages available?
     └─┬─┘
       │
  Yes  │  No
   ┌───┴───┐
   │       │
   ▼       ▼
┌──────┐  ┌──────────────┐
│Loop: │  │  End         │
│      │  └──────────────┘
│ For  │
│each  │
│msg   │
└──┬───┘
   │
   ▼
┌──────────────────┐
│ Decode message   │
│ Parse JSON       │
└────┬─────────────┘
     │
     ▼
┌──────────────────┐
│ Process message  │
│ Log content      │
└────┬─────────────┘
     │
     ▼
┌──────────────────┐
│ Track offset     │
└────┬─────────────┘
     │
     │ More messages?
     └──────┐
            │
            ▼
     ┌──────────────┐
     │Save offsets  │
     │to DynamoDB   │
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │ End          │
     └──────────────┘
```

## DynamoDB Schema

### Table: kafka-consumer-offsets

| Attribute    | Type   | Key          | Description                           |
|--------------|--------|--------------|---------------------------------------|
| consumer_id  | String | PARTITION    | Format: {group_id}_{topic}            |
| partition    | Number | SORT         | Kafka partition number                |
| offset       | Number |              | Last successfully processed offset    |
| topic        | String |              | Kafka topic name                      |
| group_id     | String |              | Consumer group ID                     |

### Example Item

```json
{
  "consumer_id": "lambda-consumer-group_test-topic",
  "partition": 0,
  "offset": 12345,
  "topic": "test-topic",
  "group_id": "lambda-consumer-group"
}
```

## Lambda Layer Structure

```
layer/
└── python/
    ├── confluent_kafka/
    │   ├── __init__.py
    │   ├── _cimpl.cpython-311-x86_64-linux-gnu.so
    │   └── [other files]
    └── [dependencies]
```

The layer follows Lambda's required structure:
- `python/` directory contains all packages
- Compatible with Python 3.11 runtime
- Built for `manylinux2014_x86_64` architecture

## IAM Permissions

### Lambda Execution Role

```yaml
Permissions:
  - logs:CreateLogGroup
  - logs:CreateLogStream
  - logs:PutLogEvents
  - dynamodb:GetItem
  - dynamodb:PutItem
  - dynamodb:Query
  - dynamodb:Scan

Resources:
  - arn:aws:logs:*:*:*
  - arn:aws:dynamodb:*:*:table/kafka-consumer-offsets
```

### EventBridge Rule Permissions

```yaml
Permissions:
  - lambda:InvokeFunction

Resource:
  - arn:aws:lambda:*:*:function:kafka-consumer-lambda
```

## Cost Breakdown

| Service       | Usage                  | Estimated Cost |
|---------------|------------------------|----------------|
| Lambda        | 43,200 invokes/month   | $0.20 - $2.00  |
|               | @ ~10s per invoke      |                |
| DynamoDB      | Pay-per-request        | $0.01 - $0.10  |
|               | ~2 ops per invoke      |                |
| EventBridge   | 43,200 events/month    | Free           |
| CloudWatch    | 1-week retention       | $0.50 - $1.00  |
| **Total**     |                        | **$1-3/month** |

## Performance Considerations

- **Cold Start**: ~2-3 seconds (includes Kafka connection)
- **Warm Invoke**: ~100-500ms overhead
- **Message Processing**: Depends on message size and complexity
- **Max Messages**: 1000 per execution (configurable)
- **Timeout**: 5 minutes (allows ~3ms per message)

## Security Best Practices

✅ **Implemented:**
- IAM roles (no hardcoded credentials)
- Least privilege permissions
- CloudWatch logging enabled
- DynamoDB encryption at rest (default)

⚠️ **Consider adding:**
- VPC configuration for private Kafka access
- AWS Secrets Manager for Kafka credentials
- KMS encryption for DynamoDB
- Lambda reserved concurrency to prevent throttling
- Dead letter queue for failed invocations
