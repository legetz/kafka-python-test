#!/usr/bin/env python3

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_logs as logs,
    CfnOutput,
)
from constructs import Construct


class KafkaConsumerLambdaStack(Stack):
    """CDK Stack for Kafka Consumer Lambda with DynamoDB offset storage."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        kafka_bootstrap_servers: str,
        kafka_topic: str,
        environment: str = "dev",
        **kwargs,
    ) -> None:
        """
        Initialize the Kafka Consumer Lambda Stack.

        Args:
            scope: CDK scope
            construct_id: Stack identifier
            kafka_bootstrap_servers: Kafka broker addresses
            kafka_topic: Kafka topic to consume from
            environment: Environment name (dev/test/prod)
            **kwargs: Additional stack properties
        """
        super().__init__(scope, construct_id, **kwargs)

        # Lambda layer for Kafka dependencies
        kafka_layer = lambda_.LayerVersion(
            self,
            "KafkaLibrariesLayer",
            layer_version_name=f"kafka-libraries-{environment}",
            code=lambda_.Code.from_asset("layer/python"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description=f"Confluent Kafka library for Python 3.11 ({environment})",
        )

        # DynamoDB table for storing Kafka offsets
        offset_table = dynamodb.Table(
            self,
            "KafkaConsumerOffsets",
            table_name=f"kafka-consumer-offsets-{environment}",
            partition_key=dynamodb.Attribute(
                name="consumer_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="partition", type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,  # Keep data on stack deletion
            point_in_time_recovery=True,
        )

        # Lambda function for Kafka consumer
        kafka_consumer_lambda = lambda_.Function(
            self,
            "KafkaConsumerFunction",
            function_name=f"kafka-consumer-lambda-{environment}",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("lambda_function"),
            layers=[kafka_layer],  # Attach the Kafka libraries layer
            timeout=Duration.minutes(5),  # Max time for processing
            memory_size=512,
            environment={
                "KAFKA_BOOTSTRAP_SERVERS": kafka_bootstrap_servers,
                "KAFKA_TOPIC": kafka_topic,
                "KAFKA_GROUP_ID": f"lambda-consumer-group-{environment}",
                "DYNAMODB_TABLE": offset_table.table_name,
                "MAX_MESSAGES": "1000",
                "POLL_TIMEOUT": "5.0",
                "ENVIRONMENT": environment,
            },
            log_retention=logs.RetentionDays.ONE_WEEK,
            retry_attempts=0,  # Disable automatic retries for scheduled events
        )

        # Grant Lambda permission to read/write DynamoDB table
        offset_table.grant_read_write_data(kafka_consumer_lambda)

        # Optional: Add VPC configuration if Kafka is in a VPC
        # Uncomment and configure if needed:
        # kafka_consumer_lambda.add_to_role_policy(
        #     iam.PolicyStatement(
        #         actions=[
        #             "ec2:CreateNetworkInterface",
        #             "ec2:DescribeNetworkInterfaces",
        #             "ec2:DeleteNetworkInterface"
        #         ],
        #         resources=["*"]
        #     )
        # )

        # CloudWatch Events rule to trigger Lambda every minute
        schedule_rule = events.Rule(
            self,
            "KafkaConsumerScheduleRule",
            rule_name=f"kafka-consumer-schedule-{environment}",
            description=f"Triggers Kafka consumer Lambda every minute ({environment})",
            schedule=events.Schedule.cron(
                minute="*", hour="*", month="*", week_day="*", year="*"  # Every minute
            ),
            enabled=True,
        )

        # Add Lambda as target for the EventBridge rule
        schedule_rule.add_target(
            targets.LambdaFunction(
                kafka_consumer_lambda,
                retry_attempts=0,  # Don't retry if Lambda fails
            )
        )

        # Grant EventBridge permission to invoke Lambda
        kafka_consumer_lambda.add_permission(
            "AllowEventBridgeInvoke",
            principal=iam.ServicePrincipal("events.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=schedule_rule.rule_arn,
        )

        # CloudWatch Log Group (created automatically, but we can reference it)
        log_group = logs.LogGroup(
            self,
            "KafkaConsumerLogs",
            log_group_name=f"/aws/lambda/{kafka_consumer_lambda.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Outputs
        CfnOutput(
            self,
            "LayerVersionArn",
            value=kafka_layer.layer_version_arn,
            description="Kafka libraries Lambda layer ARN",
        )

        CfnOutput(
            self,
            "LambdaFunctionName",
            value=kafka_consumer_lambda.function_name,
            description="Kafka consumer Lambda function name",
        )

        CfnOutput(
            self,
            "DynamoDBTableName",
            value=offset_table.table_name,
            description="DynamoDB table for offset storage",
        )

        CfnOutput(
            self,
            "ScheduleRuleName",
            value=schedule_rule.rule_name,
            description="EventBridge schedule rule name",
        )

        CfnOutput(
            self,
            "LogGroupName",
            value=log_group.log_group_name,
            description="CloudWatch Log Group name",
        )
