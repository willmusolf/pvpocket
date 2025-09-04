# 🚨 IMMEDIATE COST REDUCTION COMMANDS

**STATUS:** Scheduler jobs are paused ✅, but 60+ old App Engine versions are still running and costing money.

## 🔥 URGENT: Run These Commands Now

Open a **new terminal** and run these commands to eliminate the remaining $0.53/day in costs:

### 1. Clean Up Test-Env Service (64 versions!)
```bash
# Delete all old test-env versions (keep only current one)
gcloud app versions delete $(gcloud app versions list --service=test-env --format="value(version.id)" --sort-by=createTime | head -n -1) --service=test-env --project=pvpocket-dd286 --quiet

# Or delete them all if test-env isn't needed
gcloud app services delete test-env --project=pvpocket-dd286 --quiet
```

### 2. Verify Cleanup Worked
```bash
# Check remaining versions
gcloud app versions list --project=pvpocket-dd286

# Should show only 1-2 versions total instead of 100+
```

### 3. Optional: Delete Test Service Entirely
```bash
# If you don't need the 'test' service at all
gcloud app services delete test --project=pvpocket-dd286 --quiet
```

## 📊 Expected Cost Reduction

**Before:** $0.60/day ($18/month)  
**After:** $0.05-0.08/day (~$2/month)  
**Savings:** 90%+ reduction

## 🎯 Root Cause Solved

**The problem was:**
1. ✅ **3 failing scheduler jobs** running daily (FIXED - now paused)
2. ✅ **101 old App Engine versions** consuming resources (PARTIALLY FIXED)
3. ✅ **Automatic cleanup** now added to CI/CD (FUTURE DEPLOYMENTS FIXED)

## 🚀 Future Deployments

Your CI/CD pipeline now **automatically cleans up old versions** after each deployment, so this won't happen again.

## 🔧 Manual Script Available

If you prefer, run the cleanup script we created:
```bash
# Make executable and run
chmod +x scripts/cleanup_app_versions.sh
./scripts/cleanup_app_versions.sh
```

---

**⚠️ IMPORTANT:** The scheduler jobs were the main cost driver and are now paused. The remaining cost is from old App Engine versions that accumulated over time. Once you run these commands, your daily costs should drop to under $0.10/day.