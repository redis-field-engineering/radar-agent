#!/bin/bash

# Build script for enterprise-credentials executable
# This script creates a standalone Linux executable using PyInstaller

set -e

echo "=========================================="
echo "Building enterprise-credentials executable"
echo "=========================================="

# Check if we're in the right directory
if [ ! -f "enterprise_credentials.py" ]; then
    echo "Error: enterprise_credentials.py not found in current directory"
    echo "Please run this script from the utilities/collector-provisioning directory"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed or not in PATH"
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed or not in PATH"
    exit 1
fi

echo "Installing dependencies..."
pip3 install -r requirements.txt

echo "Cleaning previous builds..."
rm -rf build/ dist/ __pycache__/ *.spec

echo "Building executable with PyInstaller..."
pyinstaller --onefile \
    --name enterprise-credentials \
    --add-data "*.yaml:." \
    --hidden-import yaml \
    --hidden-import requests \
    --hidden-import urllib3 \
    --hidden-import argparse \
    --hidden-import json \
    --hidden-import sys \
    --hidden-import warnings \
    --hidden-import re \
    --hidden-import time \
    --hidden-import typing \
    --hidden-import urllib.parse \
    enterprise_credentials.py

echo "Build completed successfully!"
echo ""
echo "Executable location: dist/enterprise-credentials"
echo ""
echo "You can now run the executable with:"
echo "  ./dist/enterprise-credentials --help"
echo ""
echo "To test the executable:"
echo "  ./dist/enterprise-credentials --version" 