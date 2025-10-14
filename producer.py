#!/usr/bin/env python3

import json
import random
import time
from confluent_kafka import Producer
from faker import Faker
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

BOOTSTRAP_SERVERS = 'localhost:9092'
TOPIC = 'test-topic'
NUMBER_OF_EVENTS = 10000
DELAY_AFTER_EVENTS = 100  # Flush after every 100 events
DELAY_BETWEEN_EVENTS = 0.02  # seconds


class CustomerEventProducer:
    def __init__(self, bootstrap_servers, topic, num_events=NUMBER_OF_EVENTS):
        """Initialize Kafka producer for customer events."""
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.num_events = num_events
        self.faker = Faker()
        self.producer = Producer({
            'bootstrap.servers': bootstrap_servers,
            'client.id': 'customer-event-producer'
        })

    def delivery_report(self, err, msg):
        """Callback for delivery reports."""
        if err is not None:
            logger.error(f'Message delivery failed: {err}')

    def generate_customer_event(self):
        """Generate a single customer event with random data."""
        operation = random.choice(['INSERT', 'UPDATE'])
        customer_id = self.faker.uuid4()
        event = {
            'id': customer_id,
            'name': self.faker.name(),
            'email': self.faker.email(),
            'phone': self.faker.phone_number(),
            'operation': operation,
            'timestamp': int(time.time() * 1000)  # Current time in milliseconds
        }
        return customer_id, json.dumps(event)

    def produce_events(self):
        """Produce the specified number of customer events to Kafka."""
        logger.info(f"Starting to produce {self.num_events} events to topic '{self.topic}'")
        start_time = time.time()

        for i in range(self.num_events):
            key, value = self.generate_customer_event()
            try:
                self.producer.produce(
                    topic=self.topic,
                    key=key.encode('utf-8'),
                    value=value.encode('utf-8'),
                    callback=self.delivery_report
                )
                # Poll to trigger delivery callbacks
                self.producer.poll(0)
                if (i + 1) % 1000 == 0:
                    logger.info(f"Produced {i + 1} events")
            except Exception as e:
                logger.error(f"Error producing event {i + 1}: {e}")

            # Small delay to avoid overwhelming the broker
            if (i + 1) % DELAY_AFTER_EVENTS == 0:
                self.producer.flush()
                time.sleep(DELAY_BETWEEN_EVENTS)

        # Ensure all messages are sent
        self.producer.flush()
        elapsed_time = time.time() - start_time
        logger.info(f"Finished producing {self.num_events} events in {elapsed_time:.2f} seconds")


def main():
    # Create and run the producer
    producer = CustomerEventProducer(BOOTSTRAP_SERVERS, TOPIC, NUMBER_OF_EVENTS)
    producer.produce_events()


if __name__ == '__main__':
    main()
