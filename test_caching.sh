#!/bin/bash
echo "=== LIVE CACHE TESTING FOR DEFINITIVE PROOF ==="

# Test a sample image URL multiple times
TEST_URL="https://storage.googleapis.com/pvpocket-dd286.firebasestorage.app/high_res_cards/A1-001.png"

echo "Testing image caching behavior..."
echo "URL: $TEST_URL"
echo ""

echo "=== FIRST REQUEST (should be cache MISS) ==="
curl -I "$TEST_URL" 2>/dev/null | grep -E "(cache-control|age|x-cache|etag)"
echo ""

echo "=== SECOND REQUEST (should be cache HIT) ==="
sleep 2
curl -I "$TEST_URL" 2>/dev/null | grep -E "(cache-control|age|x-cache|etag)"
echo ""

echo "=== Browser Cache Test ==="
echo "Open DevTools → Network → Load your React app"
echo "1. First load: Images should show 200 status"
echo "2. Refresh: Images should show '(memory cache)' or 304"
echo "3. Hard refresh (Cmd+Shift+R): Forces new requests"

