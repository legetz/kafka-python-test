.PHONY: help build-layer clean-layer install deploy synth destroy test

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install CDK dependencies
	@echo "📦 Installing CDK dependencies..."
	pip install -r requirements.txt

build-layer: ## Build Lambda layer with dependencies
	@echo "🔨 Building Lambda layer..."
	./build_layer.sh

clean-layer: ## Clean Lambda layer build artifacts
	@echo "🧹 Cleaning Lambda layer..."
	rm -rf layer/python

synth: build-layer ## Synthesize CloudFormation template
	@echo "🔄 Synthesizing CDK stack..."
	cdk synth

deploy: build-layer ## Deploy the CDK stack
	@echo "🚀 Deploying CDK stack..."
	cdk deploy --require-approval never

deploy-with-approval: build-layer ## Deploy the CDK stack with approval
	@echo "🚀 Deploying CDK stack..."
	cdk deploy

diff: build-layer ## Show differences between deployed and local stack
	@echo "📊 Showing stack differences..."
	cdk diff

destroy: ## Destroy the CDK stack
	@echo "💥 Destroying CDK stack..."
	cdk destroy

bootstrap: ## Bootstrap CDK (run once per account/region)
	@echo "🎯 Bootstrapping CDK..."
	cdk bootstrap

test: ## Test Lambda function locally (requires Docker)
	@echo "🧪 Testing Lambda function locally..."
	@echo "Note: Ensure Kafka is accessible from localhost"
	cd lambda_function && python3 -c "from handler import lambda_handler; import json; print(json.dumps(lambda_handler({}, None), indent=2))"

logs: ## Tail CloudWatch logs for Lambda function
	@echo "📋 Tailing CloudWatch logs..."
	aws logs tail /aws/lambda/kafka-consumer-lambda --follow

list-offsets: ## List stored offsets in DynamoDB
	@echo "📊 Listing stored offsets..."
	aws dynamodb scan --table-name kafka-consumer-offsets --output table

clean: clean-layer ## Clean all build artifacts
	@echo "🧹 Cleaning all artifacts..."
	rm -rf cdk.out
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

all: install build-layer deploy ## Install, build layer, and deploy
