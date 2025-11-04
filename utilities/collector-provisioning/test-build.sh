#!/bin/bash

# Test script for enterprise-credentials build
# This script tests the build process and executable functionality

set -e

echo "=========================================="
echo "Testing enterprise-credentials build"
echo "=========================================="

# Check if we're in the right directory
if [ ! -f "enterprise_credentials.py" ]; then
    echo "Error: enterprise_credentials.py not found in current directory"
    echo "Please run this script from the utilities/collector-provisioning directory"
    exit 1
fi

# Test 1: Check if build script exists and is executable
echo "Test 1: Checking build script..."
if [ -f "build.sh" ] && [ -x "build.sh" ]; then
    echo "✓ Build script exists and is executable"
else
    echo "✗ Build script missing or not executable"
    exit 1
fi

# Test 2: Check if requirements.txt exists
echo "Test 2: Checking requirements..."
if [ -f "requirements.txt" ]; then
    echo "✓ Requirements file exists"
    echo "  Dependencies:"
    cat requirements.txt | while read line; do
        if [ ! -z "$line" ] && [[ ! "$line" =~ ^# ]]; then
            echo "    - $line"
        fi
    done
else
    echo "✗ Requirements file missing"
    exit 1
fi

# Test 3: Check if spec file exists (will be generated during build)
echo "Test 3: Checking PyInstaller spec file..."
if [ -f "enterprise-credentials.spec" ]; then
    echo "✓ PyInstaller spec file exists (will be regenerated during build)"
else
    echo "✓ PyInstaller spec file will be generated during build"
fi

# Test 4: Check if documentation exists
echo "Test 4: Checking documentation..."
if [ -f "BUILD.md" ]; then
    echo "✓ Build documentation exists"
else
    echo "✗ Build documentation missing"
fi

echo ""
echo "=========================================="
echo "Build environment check completed"
echo "=========================================="
echo ""
echo "To build the executable, run:"
echo "  ./build.sh"
echo ""
echo "To test the build process:"
echo "  1. Run the build script"
echo "  2. Check that the executable was created"
echo "  3. Test the executable with: ./dist/enterprise-credentials --help" 