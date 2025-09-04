#!/bin/bash

# Comprehensive Card Testing Runner
# Usage: ./scripts/run_card_tests.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default options
QUICK_TEST=false
VERBOSE=false
CARD_LIMIT=0

# Parse command line options
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_TEST=true
            CARD_LIMIT=50
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --limit)
            CARD_LIMIT="$2"
            shift 2
            ;;
        --help)
            echo "Comprehensive Card Testing Suite"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --quick       Run quick test on first 50 cards"
            echo "  --verbose     Enable verbose logging"
            echo "  --limit N     Test only first N cards"
            echo "  --help        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Test all cards"
            echo "  $0 --quick           # Quick test (50 cards)"
            echo "  $0 --limit 100       # Test first 100 cards"
            echo "  $0 --quick --verbose # Quick test with verbose output"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}🃏 Comprehensive Pokemon TCG Pocket Card Testing Suite${NC}"
echo "================================================="

# Check if Flask app is running
echo -e "${YELLOW}Checking if Flask app is running...${NC}"
if curl -s http://localhost:5002/api/cards?limit=1 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Flask app is running and accessible${NC}"
else
    echo -e "${RED}✗ Flask app is not running or not accessible${NC}"
    echo "Please start the Flask app with: python run.py"
    exit 1
fi

# Create required directories
mkdir -p logs test_results

# Set Python path
export PYTHONPATH="${PWD}:${PYTHONPATH}"

# Build command
CMD="python scripts/test_all_cards.py"

if [ "$QUICK_TEST" = true ]; then
    echo -e "${YELLOW}Running quick test mode (first $CARD_LIMIT cards)...${NC}"
fi

if [ "$VERBOSE" = true ]; then
    echo -e "${YELLOW}Verbose logging enabled${NC}"
fi

if [ "$CARD_LIMIT" -gt 0 ]; then
    echo -e "${YELLOW}Testing limited to first $CARD_LIMIT cards${NC}"
fi

echo ""
echo -e "${GREEN}Starting card testing...${NC}"
echo "This may take several minutes depending on the number of cards."
echo ""

# Run the tests
start_time=$(date +%s)

if python scripts/test_all_cards.py; then
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    echo ""
    echo -e "${GREEN}✓ Card testing completed successfully!${NC}"
    echo "Total time: ${duration} seconds"
    
    # Show recent results
    if [ -d "test_results" ] && [ "$(ls -A test_results)" ]; then
        latest_report=$(ls -t test_results/card_test_report_*.json | head -1)
        if [ -f "$latest_report" ]; then
            echo ""
            echo -e "${GREEN}Latest test report: $latest_report${NC}"
            echo "View with: cat $latest_report | jq '.summary'"
        fi
    fi
    
    echo ""
    echo "Next steps:"
    echo "1. Review the test report in test_results/"
    echo "2. Address any high-priority issues found"
    echo "3. Re-run tests after making fixes"
    
else
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    echo ""
    echo -e "${RED}✗ Card testing failed or found critical issues${NC}"
    echo "Total time: ${duration} seconds"
    echo ""
    echo "Check the logs and test results for details:"
    echo "  - Logs: logs/"
    echo "  - Results: test_results/"
    
    exit 1
fi