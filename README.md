# Setup Python environment for the first time
- `poetry install --no-root`
- `source .venv/bin/activate`
- `make dev`

# Activate Python environment
- `source .venv/bin/activate`

# Docker compose
- `docker-compose up -d`
 - Run `brew install docker-compose` if `docker-compose` is missing

# Create test-topic
- `docker exec -it kafka-python-test-kafka-1 bash`
- `kafka-topics --create --topic test-topic --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1`

# Produce messages into topic
- `./producer.py`

# Consume messages from topic
- `./consumer.py`

# Remove setup
- `docker-compose down`