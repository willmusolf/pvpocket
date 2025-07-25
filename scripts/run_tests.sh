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
    echo -e "${YELLOW}Running fast tests (mocked data)...${NC}"
    echo "This includes unit, integration, security, and performance tests with mocks."
    pytest -m "not real_data" -v
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
    RUN_INTEGRATION_TESTS=1 pytest -v
    
    # Stop emulator
    echo "Stopping Firebase emulator..."
    kill $EMULATOR_PID || true
    ;;
    
  "unit")
    echo -e "${YELLOW}Running unit tests only...${NC}"
    pytest -m "unit" -v
    ;;
    
  "security")
    echo -e "${YELLOW}Running security tests only...${NC}"
    pytest -m "security" -v
    ;;
    
  "performance")
    echo -e "${YELLOW}Running performance tests only...${NC}"
    pytest -m "performance" -v
    ;;
    
  "ci")
    echo -e "${YELLOW}Running CI test suite (no real data)...${NC}"
    pytest -m "not real_data" --cov=app --cov-report=json -v
    ;;
    
  *)
    echo -e "${RED}Unknown test mode: $TEST_MODE${NC}"
    echo "Usage: $0 [fast|full|unit|security|performance|ci]"
    echo "  fast       - Run all tests with mocked data (default)"
    echo "  full       - Run all tests including real Firebase data"
    echo "  unit       - Run only unit tests"
    echo "  security   - Run only security tests"
    echo "  performance - Run only performance tests"
    echo "  ci         - Run tests for CI/CD pipeline"
    exit 1
    ;;
esac

echo -e "${GREEN}✅ Tests completed!${NC}"