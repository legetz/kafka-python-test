#!/usr/bin/env python3

import json
import logging
from confluent_kafka import Consumer, KafkaError, KafkaException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

BOOTSTRAP_SERVERS = 'localhost:9092'
TOPIC = 'test-topic'


class CustomerEventConsumer:
    def __init__(self, bootstrap_servers, topic, group_id):
        """Initialize Kafka consumer for the specified topic."""
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.consumer = Consumer({
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest'  # Start from the beginning of the topic
        })

    def consume_events(self):
        """Consume messages from the topic and pretty-print them as JSON."""
        logger.info(f"Starting consumer for topic '{self.topic}' with group ID '{self.group_id}'")
        try:
            # Subscribe to the topic
            self.consumer.subscribe([self.topic])

            while True:
                msg = self.consumer.poll(timeout=1.0)  # Poll for messages
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.info(f"Reached end of partition {msg.partition()}")
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        raise KafkaException(msg.error())

                # Decode and parse the message
                try:
                    key = msg.key().decode('utf-8') if msg.key() else None
                    value = msg.value().decode('utf-8')
                    json_data = json.loads(value)  # Parse JSON
                    pretty_json = json.dumps(json_data, indent=2)  # Pretty-print JSON
                    logger.info(f"Received message (key={key}):\n{pretty_json}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON: {e} (message: {value})")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self.consumer.close()
            logger.info("Consumer closed")


def main():
    # Configuration
    group_id = 'customer-consumer-group'

    # Create and run the consumer
    consumer = CustomerEventConsumer(BOOTSTRAP_SERVERS, TOPIC, group_id)
    consumer.consume_events()


if __name__ == '__main__':
    main()
