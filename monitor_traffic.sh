#!/bin/bash
echo "=== CDN PERFORMANCE & COST MONITORING ==="
echo "Tracking CDN optimization results and cost reduction"
echo ""

PROJECT_ID="pvpocket-dd286"
BACKEND_BUCKET="pvpocket-images-backend"

echo "🎯 1. CDN Cache Hit Rate (Target: >95%):"
gcloud monitoring metrics list --filter="metric.type=loadbalancing.googleapis.com/https/backend_request_count" --project=$PROJECT_ID

echo ""
echo "📊 2. Data Transfer Volume (Should decrease significantly):"
gcloud monitoring metrics list --filter="metric.type=loadbalancing.googleapis.com/https/response_bytes_count" --project=$PROJECT_ID

echo ""
echo "⚙️ 3. Current CDN Configuration:"
gcloud compute backend-buckets describe $BACKEND_BUCKET --project=$PROJECT_ID --format="value(cdnPolicy.defaultTtl,cdnPolicy.clientTtl,cdnPolicy.negativeCaching)"

echo ""
echo "🧪 4. Cache Behavior Test:"
echo "Testing multiple requests to same image..."

TEST_URLS=(
    "https://cdn.pvpocket.xyz/energy_icons/grass.png"
    "https://cdn.pvpocket.xyz/energy_icons/fire.png"
    "https://cdn.pvpocket.xyz/energy_icons/water.png"
)

for url in "${TEST_URLS[@]}"; do
    echo ""
    echo "Testing: $url"
    echo "First request (should be MISS):"
    curl -s -I "$url" 2>/dev/null | grep -E "(HTTP|cache-control|age|x-cache|etag)" | head -4

    sleep 1

    echo "Second request (should be HIT):"
    curl -s -I "$url" 2>/dev/null | grep -E "(HTTP|cache-control|age|x-cache|etag)" | head -4
done

echo ""
echo "💰 5. Cost Impact Analysis:"
echo "Expected improvements:"
echo "  ✅ Cache Hit Rate: 95%+ (was 0% due to 403s)"
echo "  ✅ Origin Requests: 90% reduction"
echo "  ✅ Egress Costs: 80-90% reduction"
echo "  ✅ Monthly Cost: <$1/month (was $8/month)"

echo ""
echo "📈 6. Next Steps:"
echo "  - Monitor billing for 24-48 hours"
echo "  - Check ./check_billing.sh for cost trends"
echo "  - Validate service worker cache stats in browser DevTools"

