#!/usr/bin/env python3

import json
import logging
import os
from typing import Dict, Any, Optional
import boto3
from confluent_kafka import (
    Consumer,
    KafkaError,
    KafkaException,
    Message,
    TopicPartition,
)
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.environ.get("KAFKA_TOPIC", "test-topic")
GROUP_ID = os.environ.get("KAFKA_GROUP_ID", "lambda-consumer-group")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "kafka-consumer-offsets")
MAX_MESSAGES = int(os.environ.get("MAX_MESSAGES", "1000"))
POLL_TIMEOUT = float(os.environ.get("POLL_TIMEOUT", "5.0"))

# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb")


class DynamoDBOffsetStore:
    """Manages Kafka consumer offsets in DynamoDB."""

    def __init__(self, table_name: str):
        """
        Initialize the offset store.

        Args:
            table_name: DynamoDB table name
        """
        self.table = dynamodb.Table(table_name)
        self.consumer_id = f"{GROUP_ID}_{TOPIC}"

    def get_last_offset(self, partition: int) -> Optional[int]:
        """
        Retrieve the last committed offset for a partition.

        Args:
            partition: Kafka partition number

        Returns:
            Last committed offset or None if not found
        """
        try:
            response = self.table.get_item(
                Key={"consumer_id": self.consumer_id, "partition": partition}
            )
            item = response.get("Item")
            if item:
                logger.info(
                    f"Retrieved offset {item['offset']} for partition {partition}"
                )
                return item["offset"]
            logger.info(f"No stored offset found for partition {partition}")
            return None
        except ClientError as e:
            logger.error(f"Error retrieving offset from DynamoDB: {e}")
            return None

    def save_offset(self, partition: int, offset: int) -> bool:
        """
        Save the last successfully processed offset for a partition.

        Args:
            partition: Kafka partition number
            offset: Message offset to save

        Returns:
            True if successful, False otherwise
        """
        try:
            self.table.put_item(
                Item={
                    "consumer_id": self.consumer_id,
                    "partition": partition,
                    "offset": offset,
                    "topic": TOPIC,
                    "group_id": GROUP_ID,
                }
            )
            logger.info(f"Saved offset {offset} for partition {partition}")
            return True
        except ClientError as e:
            logger.error(f"Error saving offset to DynamoDB: {e}")
            return False


class KafkaMessageProcessor:
    """Processes messages from Kafka topic."""

    def __init__(self, offset_store: DynamoDBOffsetStore):
        """
        Initialize the Kafka message processor.

        Args:
            offset_store: DynamoDB offset store instance
        """
        self.offset_store = offset_store
        self.consumer = None
        self.messages_processed = 0
        self.last_offsets = {}

    def _create_consumer(self) -> Consumer:
        """
        Create and configure Kafka consumer.

        Returns:
            Configured Kafka consumer
        """
        consumer_config = {
            "bootstrap.servers": BOOTSTRAP_SERVERS,
            "group.id": GROUP_ID,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,  # Manual commit for better control
            "max.poll.interval.ms": 300000,  # 5 minutes
        }

        consumer = Consumer(consumer_config)
        logger.info(f"Created Kafka consumer for topic '{TOPIC}'")
        return consumer

    def _set_partition_offset(self, consumer: Consumer, partition: int) -> None:
        """
        Set the consumer to start from the last stored offset.

        Args:
            consumer: Kafka consumer instance
            partition: Partition number
        """
        last_offset = self.offset_store.get_last_offset(partition)
        if last_offset is not None:
            # Start from next message after the last processed one
            tp = TopicPartition(TOPIC, partition, last_offset + 1)
            consumer.assign([tp])
            logger.info(
                f"Starting from offset {last_offset + 1} for partition {partition}"
            )
        else:
            # Let auto.offset.reset handle it
            logger.info(
                f"No stored offset, using auto.offset.reset for partition {partition}"
            )

    def _process_message(self, msg: Message) -> bool:
        """
        Process a single Kafka message.

        Args:
            msg: Kafka message

        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            key = msg.key().decode("utf-8") if msg.key() else None
            value = msg.value().decode("utf-8")
            json_data = json.loads(value)

            logger.info(
                f"Processed message - Key: {key}, "
                f"Partition: {msg.partition()}, "
                f"Offset: {msg.offset()}"
            )
            logger.debug(f"Message content: {json.dumps(json_data, indent=2)}")

            # Track last offset per partition
            self.last_offsets[msg.partition()] = msg.offset()
            self.messages_processed += 1

            return True

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return False

    def process_messages(self) -> Dict[str, Any]:
        """
        Main method to consume and process messages from Kafka.

        Returns:
            Processing results summary
        """
        self.consumer = self._create_consumer()

        try:
            # Subscribe to topic
            self.consumer.subscribe([TOPIC])
            logger.info(f"Subscribed to topic '{TOPIC}'")

            # Get partition assignment (may need to poll first)
            self.consumer.poll(0)
            assignment = self.consumer.assignment()

            if assignment:
                logger.info(
                    f"Assigned partitions: {[tp.partition for tp in assignment]}"
                )
                # Set offsets for assigned partitions
                for tp in assignment:
                    self._set_partition_offset(self.consumer, tp.partition)

            # Process messages up to MAX_MESSAGES
            remaining = MAX_MESSAGES
            while remaining > 0:
                msg = self.consumer.poll(timeout=POLL_TIMEOUT)

                if msg is None:
                    logger.info("No more messages available")
                    break

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.info(f"Reached end of partition {msg.partition()}")
                        continue
                    else:
                        logger.error(f"Kafka error: {msg.error()}")
                        raise KafkaException(msg.error())

                self._process_message(msg)
                remaining -= 1

            # Save last offsets to DynamoDB
            for partition, offset in self.last_offsets.items():
                self.offset_store.save_offset(partition, offset)

            return {
                "messages_processed": self.messages_processed,
                "last_offsets": self.last_offsets,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error in message processing: {e}", exc_info=True)
            return {
                "messages_processed": self.messages_processed,
                "error": str(e),
                "status": "error",
            }

        finally:
            if self.consumer:
                self.consumer.close()
                logger.info("Kafka consumer closed")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function.

    Args:
        event: Lambda event object
        context: Lambda context object

    Returns:
        Response with processing results
    """
    logger.info(f"Lambda function invoked. Event: {json.dumps(event)}")
    logger.info(f"Environment - Bootstrap Servers: {BOOTSTRAP_SERVERS}, Topic: {TOPIC}")

    try:
        offset_store = DynamoDBOffsetStore(DYNAMODB_TABLE)
        processor = KafkaMessageProcessor(offset_store)
        result = processor.process_messages()

        logger.info(f"Processing completed: {result}")

        return {"statusCode": 200, "body": json.dumps(result)}

    except Exception as e:
        logger.error(f"Lambda execution failed: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"status": "error", "error": str(e)}),
        }
