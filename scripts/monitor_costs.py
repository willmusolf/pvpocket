#!/usr/bin/env python3
"""
Cost Monitoring Script for Pokemon TCG Pocket Automation
Tracks Firestore usage and sends alerts when thresholds are exceeded.
"""

import os
import sys
from datetime import datetime, timedelta
import json

# Add parent directory to path to import shared utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared_utils import initialize_firebase
from firebase_admin import firestore

# Cost thresholds (in USD)
DAILY_COST_WARNING = 2.00
DAILY_COST_CRITICAL = 5.00
MONTHLY_COST_BUDGET = 50.00

# Firestore pricing (as of 2024)
FIRESTORE_READ_COST_PER_100K = 0.06
FIRESTORE_WRITE_COST_PER_100K = 0.18
FIRESTORE_DELETE_COST_PER_100K = 0.02

def estimate_daily_cost(reads: int, writes: int, deletes: int = 0) -> float:
    """Estimate daily Firestore cost based on operation counts."""
    read_cost = (reads / 100000) * FIRESTORE_READ_COST_PER_100K
    write_cost = (writes / 100000) * FIRESTORE_WRITE_COST_PER_100K
    delete_cost = (deletes / 100000) * FIRESTORE_DELETE_COST_PER_100K
    return read_cost + write_cost + delete_cost

def get_operation_estimates() -> dict:
    """Estimate operation counts for typical automation scenarios."""
    return {
        "daily_change_detection": {
            "reads": 50,  # Check hash tracker + a few set documents
            "writes": 5,  # Update trackers
            "description": "Daily change detection (4 runs per day)"
        },
        "new_set_scraping": {
            "reads": 200,  # Check existing sets/cards
            "writes": 500,  # Write new cards (assuming 100-card set)
            "description": "Scraping a new 100-card set (once per month)"
        },
        "cache_refresh": {
            "reads": 2000,  # Read all cards for cache
            "writes": 1,    # Update cache metadata
            "description": "Production cache refresh (daily)"
        }
    }

def calculate_estimated_monthly_cost() -> dict:
    """Calculate estimated monthly costs for all automation scenarios."""
    scenarios = get_operation_estimates()
    
    monthly_totals = {
        "reads": 0,
        "writes": 0,
        "cost": 0.0,
        "breakdown": {}
    }
    
    for scenario_name, ops in scenarios.items():
        # Estimate frequency
        if "change_detection" in scenario_name:
            monthly_multiplier = 30 * 4  # 4 times per day for 30 days
        elif "new_set_scraping" in scenario_name:
            monthly_multiplier = 1  # Once per month typically
        elif "cache_refresh" in scenario_name:
            monthly_multiplier = 30  # Daily
        else:
            monthly_multiplier = 1
            
        monthly_reads = ops["reads"] * monthly_multiplier
        monthly_writes = ops["writes"] * monthly_multiplier
        scenario_cost = estimate_daily_cost(monthly_reads, monthly_writes)
        
        monthly_totals["reads"] += monthly_reads
        monthly_totals["writes"] += monthly_writes
        monthly_totals["cost"] += scenario_cost
        
        monthly_totals["breakdown"][scenario_name] = {
            "reads": monthly_reads,
            "writes": monthly_writes,
            "cost": scenario_cost,
            "frequency": f"{monthly_multiplier}x per month",
            "description": ops["description"]
        }
    
    return monthly_totals

def create_cost_monitoring_dashboard() -> dict:
    """Create a comprehensive cost monitoring dashboard."""
    monthly_estimate = calculate_estimated_monthly_cost()
    
    dashboard = {
        "timestamp": datetime.utcnow().isoformat(),
        "cost_estimates": {
            "monthly_total": round(monthly_estimate["cost"], 2),
            "monthly_reads": monthly_estimate["reads"],
            "monthly_writes": monthly_estimate["writes"],
            "within_budget": monthly_estimate["cost"] <= MONTHLY_COST_BUDGET
        },
        "thresholds": {
            "daily_warning": DAILY_COST_WARNING,
            "daily_critical": DAILY_COST_CRITICAL,
            "monthly_budget": MONTHLY_COST_BUDGET
        },
        "optimization_tips": [
            "Use hash-based change detection to minimize unnecessary reads",
            "Cache set completion status to avoid repeated queries", 
            "Batch operations when possible to reduce write costs",
            "Use collection group queries efficiently with proper indexing",
            "Monitor and limit promo set processing frequency"
        ],
        "scenario_breakdown": monthly_estimate["breakdown"]
    }
    
    return dashboard

def save_cost_monitoring_report():
    """Save cost monitoring report to Firestore and local file."""
    try:
        initialize_firebase()
        db = firestore.client()
        
        dashboard = create_cost_monitoring_dashboard()
        
        # Save to Firestore for monitoring dashboard
        cost_doc_ref = db.collection("internal_config").document("cost_monitoring")
        cost_doc_ref.set(dashboard)
        print("✅ Cost monitoring report saved to Firestore")
        
        # Save local copy for development reference
        with open("cost_monitoring_report.json", "w") as f:
            json.dump(dashboard, f, indent=2)
        print("✅ Cost monitoring report saved locally")
        
        # Print summary
        cost = dashboard["cost_estimates"]["monthly_total"]
        budget = dashboard["thresholds"]["monthly_budget"]
        
        print(f"\n📊 Cost Monitoring Summary:")
        print(f"   Estimated monthly cost: ${cost}")
        print(f"   Monthly budget: ${budget}")
        print(f"   Status: {'✅ Within budget' if cost <= budget else '⚠️ Over budget'}")
        print(f"   Monthly reads: {dashboard['cost_estimates']['monthly_reads']:,}")
        print(f"   Monthly writes: {dashboard['cost_estimates']['monthly_writes']:,}")
        
        return dashboard
        
    except Exception as e:
        print(f"❌ Error creating cost monitoring report: {e}")
        return None

if __name__ == "__main__":
    print("🔍 Pokemon TCG Pocket - Cost Monitoring")
    print("=" * 50)
    
    # Generate and save cost monitoring report
    dashboard = save_cost_monitoring_report()
    
    if dashboard:
        print("\n💡 Optimization recommendations:")
        for tip in dashboard["optimization_tips"]:
            print(f"   • {tip}")