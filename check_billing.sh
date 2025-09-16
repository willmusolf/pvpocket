#!/bin/bash
echo "=== DEFINITIVE BILLING BREAKDOWN ==="

echo "1. Navigate to: https://console.cloud.google.com/billing/01EB3D-5F6952-67889F/reports"
echo "2. Set filters:"
echo "   - Project: pvpocket-dd286"
echo "   - Service: Compute Engine (includes CDN/Load Balancing)"
echo "   - Time range: Last 7 days"
echo "   - Group by: SKU"
echo ""

echo "3. Look for these specific SKUs causing networking costs:"
echo "   - 'Network Load Balancing - Data Processing'"
echo "   - 'Network Load Balancing - Forwarding Rule'"
echo "   - 'Compute Engine - Network Egress'"
echo "   - 'Cloud CDN - Cache Fill'"
echo "   - 'Cloud CDN - Cache Lookup'"
echo ""

echo "4. Export detailed report as CSV for exact cost attribution"
echo ""

echo "CURRENT PROJECT BILLING LINK:"
echo "https://console.cloud.google.com/billing/01EB3D-5F6952-67889F/reports?project=pvpocket-dd286"

