#!/bin/bash

# Build script for Lambda layer containing Python dependencies
# This script packages dependencies in the format required by Lambda layers:
# python/lib/python3.11/site-packages/

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LAYER_DIR="${SCRIPT_DIR}/layer"
BUILD_DIR="${LAYER_DIR}/python"

echo "🔨 Building Lambda layer..."

# Clean previous build
if [ -d "$BUILD_DIR" ]; then
    echo "🧹 Cleaning previous build..."
    rm -rf "$BUILD_DIR"
fi

# Create layer directory structure
echo "📁 Creating layer directory structure..."
mkdir -p "$BUILD_DIR"

# Install dependencies
echo "📦 Installing dependencies..."
pip install \
    --platform manylinux2014_x86_64 \
    --target="$BUILD_DIR" \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --upgrade \
    -r "${LAYER_DIR}/requirements.txt"

# Clean up unnecessary files to reduce layer size
echo "🧹 Cleaning up unnecessary files..."
find "$BUILD_DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true
find "$BUILD_DIR" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true

# Calculate size
LAYER_SIZE=$(du -sh "$BUILD_DIR" | cut -f1)
echo "✅ Layer built successfully!"
echo "📊 Layer size: $LAYER_SIZE"
echo "📍 Layer location: $BUILD_DIR"
