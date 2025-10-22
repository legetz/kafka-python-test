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
from aws_cdk import App, Environment, Tags
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

# Environment (dev/test/prod)
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

app = App()

# Create the stack
stack = KafkaConsumerLambdaStack(
    app,
    f"KafkaConsumerLambdaStack-{ENVIRONMENT}",
    kafka_bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    kafka_topic=KAFKA_TOPIC,
    environment=ENVIRONMENT,
    env=Environment(
        account=AWS_ACCOUNT,
        region=AWS_REGION
    ),
    description=f"Kafka consumer Lambda with DynamoDB offset storage and EventBridge scheduling ({ENVIRONMENT})"
)

# Add tags for all resources
Tags.of(stack).add("Environment", ENVIRONMENT)
Tags.of(stack).add("Project", "KafkaConsumer")
Tags.of(stack).add("ManagedBy", "CDK")

app.synth()
