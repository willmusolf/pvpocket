#!/bin/bash
# Test runner script with different profiles

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 Pokemon TCG Pocket Test Runner${NC}"
echo "=================================="

# Parse command line arguments
TEST_MODE=${1:-fast}

case $TEST_MODE in
  "fast")
    echo -e "${YELLOW}Running fast development tests (mocked data)...${NC}"
    echo "This includes essential tests for quick development feedback."
    python3 -m pytest tests/test_fast_development.py -v --tb=short --cov-fail-under=0
    ;;
    
  "dev")
    echo -e "${YELLOW}Running all fast tests (mocked data)...${NC}"
    echo "This includes unit, integration, security, and performance tests with mocks."
    python3 -m pytest -m "not real_data" -v
    ;;
    
  "full")
    echo -e "${YELLOW}Running full test suite (including real data tests)...${NC}"
    echo "Starting Firebase emulator and seeding data..."
    
    # Start Firebase emulator
    firebase emulators:start --only firestore,storage --project demo-test-project &
    EMULATOR_PID=$!
    
    # Wait for emulator to start
    echo "Waiting for emulator to start..."
    sleep 10
    
    # Seed test data
    echo "Seeding test data..."
    python scripts/seed_test_data.py
    
    # Run all tests including real data tests
    RUN_INTEGRATION_TESTS=1 python3 -m pytest -v
    
    # Stop emulator
    echo "Stopping Firebase emulator..."
    kill $EMULATOR_PID || true
    ;;
    
  "unit")
    echo -e "${YELLOW}Running unit tests only...${NC}"
    python3 -m pytest -m "unit" -v
    ;;
    
  "security")
    echo -e "${YELLOW}Running security tests only...${NC}"
    python3 -m pytest -m "security" -v
    ;;
    
  "performance")
    echo -e "${YELLOW}Running performance tests only...${NC}"
    python3 -m pytest -m "performance" -v
    ;;
    
  "ci")
    echo -e "${YELLOW}Running CI test suite (no real data)...${NC}"
    python3 -m pytest -m "not real_data" --cov=app --cov-report=json -v
    ;;
    
  "pre-prod")
    echo -e "${YELLOW}Running pre-production test suite (like main branch)...${NC}"
    echo "This runs the same comprehensive tests as production deployment."
    echo "Starting Firebase emulator and seeding data..."
    
    # Start Firebase emulator
    firebase emulators:start --only firestore,storage --project demo-test-project &
    EMULATOR_PID=$!
    
    # Wait for emulator to start
    echo "Waiting for emulator to start..."
    sleep 10
    
    # Seed test data
    echo "Seeding test data..."
    python scripts/seed_test_data.py
    
    # Run all tests including real data tests with coverage
    RUN_INTEGRATION_TESTS=1 python3 -m pytest -v --cov=app --cov-report=html --cov-fail-under=30
    
    # Stop emulator
    echo "Stopping Firebase emulator..."
    kill $EMULATOR_PID || true
    ;;
    
  *)
    echo -e "${RED}Unknown test mode: $TEST_MODE${NC}"
    echo "Usage: $0 [fast|dev|full|unit|security|performance|ci|pre-prod]"
    echo "  fast       - Run essential fast tests (default, like development branch)"
    echo "  dev        - Run all fast tests with mocked data"
    echo "  full       - Run all tests including real Firebase data"
    echo "  pre-prod   - Run comprehensive tests like production deployment"
    echo "  unit       - Run only unit tests"
    echo "  security   - Run only security tests"
    echo "  performance - Run only performance tests"
    echo "  ci         - Run tests for CI/CD pipeline"
    exit 1
    ;;
esac

echo -e "${GREEN}✅ Tests completed!${NC}"