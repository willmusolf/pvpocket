#!/bin/bash
echo "=== POKEMON TCG POCKET - CDN COST OPTIMIZATION ==="
echo "This script configures the CDN backend for optimal caching and cost reduction"
echo ""

PROJECT_ID="pvpocket-dd286"
BACKEND_BUCKET="pvpocket-images-backend"
BUCKET_NAME="pvpocket-dd286.firebasestorage.app"

echo "🔧 Step 1: Configure CDN backend bucket with aggressive caching..."

# Update the CDN backend with optimal cache settings
gcloud compute backend-buckets update $BACKEND_BUCKET \
    --gcs-bucket-name=$BUCKET_NAME \
    --enable-cdn \
    --project=$PROJECT_ID

echo ""
echo "🚀 Step 2: Set CDN cache policy for cost optimization..."

# Configure CDN policy with aggressive caching for images
gcloud compute backend-buckets update $BACKEND_BUCKET \
    --cache-mode=CACHE_ALL_STATIC \
    --default-ttl=31536000 \
    --max-ttl=31536000 \
    --client-ttl=31536000 \
    --negative-caching \
    --negative-caching-policy="404=300,403=300" \
    --project=$PROJECT_ID

echo ""
echo "📊 Step 3: Verify current CDN configuration..."
gcloud compute backend-buckets describe $BACKEND_BUCKET \
    --project=$PROJECT_ID \
    --format="value(cdnPolicy.defaultTtl,cdnPolicy.clientTtl,cdnPolicy.negativeCaching)"

echo ""
echo "🧪 Step 4: Test cache behavior..."
echo "Testing CDN URL: https://cdn.pvpocket.xyz/energy_icons/grass.png"
curl -I "https://cdn.pvpocket.xyz/energy_icons/grass.png" 2>/dev/null | grep -E "(cache-control|age|x-cache|etag|status)"

echo ""
echo "✅ CDN optimization complete!"
echo ""
echo "💡 Expected results:"
echo "   - Cache TTL: 1 year (31536000 seconds)"
echo "   - Negative caching: 5 minutes for 404/403 errors"
echo "   - Cost reduction: 80-90% due to edge caching"
echo ""
echo "🔍 Monitor results with:"
echo "   ./monitor_traffic.sh"
echo "   ./check_billing.sh"