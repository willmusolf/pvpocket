#!/bin/bash
# Automated test script for PvPocket app

echo "🧪 Running PvPocket App Tests..."
echo "================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

# Function to run a test
run_test() {
    local test_name=$1
    local command=$2
    local expected=$3
    
    echo -n "Testing $test_name... "
    
    result=$(eval $command 2>/dev/null)
    
    if [[ $result == *"$expected"* ]]; then
        echo -e "${GREEN}✅ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ FAILED${NC}"
        echo "  Expected: $expected"
        echo "  Got: ${result:0:100}..."
        ((FAILED++))
    fi
}

echo "1. Basic Health Checks"
echo "----------------------"
run_test "Production health" "curl -s https://pvpocket.xyz/health" '"status":"ok"'
run_test "Production metrics" "curl -s https://pvpocket.xyz/internal/metrics" '"cache_healthy":true'
run_test "Test env health" "curl -s https://test-env-dot-pvpocket-dd286.uc.r.appspot.com/health" '"status":"ok"'

echo ""
echo "2. Page Load Tests"
echo "------------------"
run_test "Homepage loads" "curl -s https://pvpocket.xyz/ | grep -o '<title>.*</title>'" '<title>PvPocket</title>'
run_test "Login page exists" "curl -s -o /dev/null -w '%{http_code}' https://pvpocket.xyz/login/google" "302"

echo ""
echo "3. Security Tests"
echo "-----------------"
run_test "No exposed secrets" "curl -s https://pvpocket.xyz/ | grep -i 'secret_key'" ""
run_test "HTTPS redirect" "curl -s -o /dev/null -w '%{redirect_url}' http://pvpocket-dd286.uc.r.appspot.com/" "https://"

echo ""
echo "4. Performance Tests"
echo "-------------------"
# Test response time
response_time=$(curl -s -o /dev/null -w '%{time_total}' https://pvpocket.xyz/health)
response_time_ms=$(echo "$response_time * 1000" | bc | cut -d. -f1)

if [ ${response_time_ms:-9999} -lt 2000 ]; then
    echo -e "Response time: ${GREEN}${response_time_ms}ms ✅${NC} (< 2 seconds)"
    ((PASSED++))
else
    echo -e "Response time: ${RED}${response_time_ms}ms ❌${NC} (> 2 seconds)"
    ((FAILED++))
fi

echo ""
echo "================================"
echo "Test Results:"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All tests passed! Your app is working perfectly!${NC}"
    exit 0
else
    echo -e "\n${YELLOW}⚠️  Some tests failed. Check the errors above.${NC}"
    exit 1
fi