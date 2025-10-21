#!/usr/bin/env python3

"""
AWS CDK Application for Kafka Consumer Lambda

This CDK app deploys a Lambda function that:
- Consumes messages from a Kafka topic
- Processes up to 1000 messages per execution
- Stores offset information in DynamoDB
- Runs on a schedule (every minute via EventBridge)
"""

import os
from aws_cdk import App, Environment
from cdk_app.kafka_consumer_stack import KafkaConsumerLambdaStack

# Configuration - Update these values for your environment
KAFKA_BOOTSTRAP_SERVERS = os.environ.get(
    'KAFKA_BOOTSTRAP_SERVERS',
    'localhost:9092'  # Default for local testing
)
KAFKA_TOPIC = os.environ.get('KAFKA_TOPIC', 'test-topic')

# AWS Account and Region
AWS_ACCOUNT = os.environ.get('CDK_DEFAULT_ACCOUNT')
AWS_REGION = os.environ.get('CDK_DEFAULT_REGION', 'us-east-1')

app = App()

# Create the stack
KafkaConsumerLambdaStack(
    app,
    "KafkaConsumerLambdaStack",
    kafka_bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    kafka_topic=KAFKA_TOPIC,
    env=Environment(
        account=AWS_ACCOUNT,
        region=AWS_REGION
    ),
    description="Kafka consumer Lambda with DynamoDB offset storage and EventBridge scheduling"
)

app.synth()
