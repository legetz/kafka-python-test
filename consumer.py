#!/usr/bin/env python3

import json
import logging
import sys
from typing import Optional, Dict, Any
from confluent_kafka import Consumer, KafkaError, KafkaException, Message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration constants
BOOTSTRAP_SERVERS = 'localhost:9092'
TOPIC = 'test-topic'
POLL_MESSAGES = 200  # Number of max messages to fetch per poll
POLL_TIMEOUT = 10.0  # seconds
DEFAULT_GROUP_ID = 'customer-consumer-group'


class MessageProcessingError(Exception):
    """Custom exception for message processing errors."""
    pass


class CustomerEventConsumer:
    """Kafka consumer for processing customer events."""

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        auto_offset_reset: str = 'earliest'
    ):
        """
        Initialize Kafka consumer for the specified topic.

        Args:
            bootstrap_servers: Kafka broker addresses
            topic: Topic to consume from
            group_id: Consumer group ID
            auto_offset_reset: Where to start reading ('earliest' or 'latest')
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.running = False

        consumer_config = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': auto_offset_reset,
            'enable.auto.commit': True,
            'auto.commit.interval.ms': 5000,
        }

        try:
            self.consumer = Consumer(consumer_config)
            logger.info(f"Consumer initialized for topic '{topic}' with group '{group_id}'")
        except Exception as e:
            logger.error(f"Failed to initialize consumer: {e}")
            raise

    def _decode_message_key(self, msg: Message) -> Optional[str]:
        """
        Safely decode message key.

        Args:
            msg: Kafka message

        Returns:
            Decoded key or None
        """
        try:
            return msg.key().decode('utf-8') if msg.key() else None
        except UnicodeDecodeError as e:
            logger.warning(f"Failed to decode message key: {e}")
            return None

    def _decode_message_value(self, msg: Message) -> Dict[str, Any]:
        """
        Safely decode and parse message value as JSON.

        Args:
            msg: Kafka message

        Returns:
            Parsed JSON data

        Raises:
            MessageProcessingError: If decoding or parsing fails
        """
        try:
            value = msg.value().decode('utf-8')
            return json.loads(value)
        except UnicodeDecodeError as e:
            raise MessageProcessingError(f"Failed to decode message value: {e}")
        except json.JSONDecodeError as e:
            raise MessageProcessingError(f"Failed to parse JSON: {e}")

    def _process_message(self, msg: Message) -> None:
        """
        Process a single Kafka message.

        Args:
            msg: Kafka message to process
        """
        if msg.error():
            self._handle_message_error(msg)
            return

        try:
            key = self._decode_message_key(msg)
            json_data = self._decode_message_value(msg)
            pretty_json = json.dumps(json_data, indent=2)

            logger.info(
                f"Received message (key={key}, "
                f"offset={msg.offset()}):\n{pretty_json}"
            )
        except MessageProcessingError as e:
            logger.error(f"Message processing error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error processing message: {e}", exc_info=True)

    def _handle_message_error(self, msg: Message) -> None:
        """
        Handle Kafka message errors.

        Args:
            msg: Kafka message with error
        """
        error = msg.error()
        if error.code() == KafkaError._PARTITION_EOF:
            logger.debug(f"Reached end of partition {msg.partition()}")
        else:
            logger.error(f"Kafka error: {error}")
            raise KafkaException(error)

    def consume_events(self) -> None:
        """Consume messages from the topic and process them."""
        logger.info(f"Starting consumer for topic '{self.topic}'")
        self.running = True

        try:
            self.consumer.subscribe([self.topic])
            logger.info(f"Subscribed to topic '{self.topic}'")

            self._consume_loop()

        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        except KafkaException as e:
            logger.error(f"Kafka exception: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in consumer: {e}", exc_info=True)
            raise
        finally:
            self._cleanup()

    def _consume_loop(self) -> None:
        """Main consumption loop."""
        while self.running:
            messages = self.consumer.consume(
                num_messages=POLL_MESSAGES,
                timeout=POLL_TIMEOUT
            )

            if not messages:
                logger.debug("No messages received in this round")
                continue

            for msg in messages:
                self._process_message(msg)

            logger.info(f"Processed {len(messages)} message(s)")

    def _cleanup(self) -> None:
        """Clean up consumer resources."""
        try:
            if hasattr(self, 'consumer'):
                self.consumer.close()
                logger.info("Consumer closed successfully")
        except Exception as e:
            logger.error(f"Error closing consumer: {e}")

    def stop(self) -> None:
        """Stop the consumer gracefully."""
        logger.info("Stopping consumer...")
        self.running = False


def main() -> None:
    """Main entry point for the consumer application."""
    consumer = CustomerEventConsumer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        topic=TOPIC,
        group_id=DEFAULT_GROUP_ID
    )

    try:
        consumer.consume_events()
    except Exception as e:
        logger.error(f"Consumer failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
