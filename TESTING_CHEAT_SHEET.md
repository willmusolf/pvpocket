# Testing Cheat Sheet

## Quick Reference: When Do Tests Run?

| Action | Test Type | Duration | What It Tests |
|--------|-----------|----------|---------------|
| **Create PR** → `main` or `development` | Fast | ~2-3 sec | Mocked data, quick feedback |
| **Push to** `development` | Fast | ~2-3 sec | Staging validation |
| **Push to** `main` | Full | ~20-30 sec | Real Firebase + integration |
| **Manual trigger** | Your choice | Varies | Any test type you select |

## Manual Testing Options

### Via GitHub Actions Web UI
1. Go to your repo → **Actions** tab
2. Click **CI/CD Pipeline** 
3. Click **Run workflow** (top right)
4. Select test type:
   - `fast` - Quick tests (default)
   - `full` - Complete suite with Firebase
   - `unit` - Unit tests only
   - `security` - Security tests only
   - `performance` - Performance tests only

### Via Command Line (Local)
```bash
# Fast tests (like PRs/development)
pytest -m "not real_data" -v

# Full tests (like main branch)
./scripts/run_tests.sh full

# Specific categories
pytest -m "unit" -v
pytest -m "security" -v  
pytest -m "performance" -v

# All tests with coverage
pytest --cov=app
```

## Workflow Summary

```
📝 Write Code
    ↓
🔀 Create PR → Fast Tests (2-3 sec)
    ↓
✅ Merge to development → Fast Tests (2-3 sec)
    ↓  
🚀 Push to main → Full Tests (20-30 sec)
    ↓
🌍 Deploy to Production
```

## Test Results Explanation

### "0 cards, 0 sets" = Normal ✅
- **Fast tests** use mocked data
- This prevents external dependencies
- Each test provides its own test data

### Real Card Data = Integration Tests ✅  
- **Full tests** load actual data into Firebase emulator
- Tests real database operations
- Only runs on main branch pushes

## Common Commands

```bash
# What developers usually need:
pytest -m "not real_data" -v          # Quick feedback
./scripts/run_tests.sh full           # Before important merges
pytest -m "security" -v               # Security checks only
pytest --tb=short                     # Less verbose output
```

## Troubleshooting

❓ **Tests failing on PR but passing locally?**
- Run: `pytest -m "not real_data" -v` locally to match PR tests

❓ **Need to test Firebase operations?** 
- Use manual trigger with "full" option or push to main

❓ **Want faster feedback during development?**
- Use fast tests and mock any external data in your test

## Pro Tips

- **Development workflow**: Use fast tests 90% of the time
- **Before major releases**: Run full tests manually
- **Debugging specific areas**: Use category-specific tests (`unit`, `security`, etc.)
- **CI/CD confidence**: Main branch = fully tested, development = quick validation