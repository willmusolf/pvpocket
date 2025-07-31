# Testing Cheat Sheet

## Quick Reference: When Do Tests Run?

| Action | Test Type | Duration | What It Tests |
|--------|-----------|----------|---------------|
| **Create PR** | Super Fast | ~5 sec | Essential tests, mocked data |
| **Push to** `development` | Super Fast | ~5 sec | Essential tests, mocked data |
| **Push to** `main` | Full | ~20-30 sec | Real Firebase + comprehensive |
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
# ⚡ Super fast tests (RECOMMENDED for daily development)
./scripts/run_tests.sh fast

# All mocked tests  
./scripts/run_tests.sh dev

# 🚀 Pre-production validation (before pushing to main)
./scripts/run_tests.sh pre-prod

# Full tests (if emulator already running)
./scripts/run_tests.sh full

# Specific categories
pytest -m "unit" -v
pytest -m "security" -v  
pytest -m "performance" -v
```

## Optimized Development Workflow

```
📝 Write Code
    ↓
⚡ Run ./scripts/run_tests.sh fast (5 sec)
    ↓
🔀 Create PR → Super Fast Tests (5 sec)
    ↓
✅ Merge to development → Super Fast Tests (5 sec)
    ↓
🚀 Before pushing to main → Run ./scripts/run_tests.sh pre-prod locally
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
# ⭐ What developers usually need:
./scripts/run_tests.sh fast           # Daily development (5 seconds)
./scripts/run_tests.sh pre-prod       # Before pushing to main
pytest -m "security" -v               # Security checks only
pytest --tb=short                     # Less verbose output

# Legacy commands (still work):
pytest -m "not real_data" -v          # All mocked tests
./scripts/run_tests.sh full           # Full suite with emulator
```

## Troubleshooting

❓ **Tests failing on PR but passing locally?**
- Run: `./scripts/run_tests.sh fast` locally to match PR tests

❓ **Need to test Firebase operations?** 
- Use: `./scripts/run_tests.sh pre-prod` or push to main

❓ **Want faster feedback during development?**
- Use: `./scripts/run_tests.sh fast` (5 seconds) instead of full suite

❓ **Pushing to main but tests might fail?**
- Run: `./scripts/run_tests.sh pre-prod` locally first to avoid CI failures

## Pro Tips 🚀

- **Daily development**: Use `./scripts/run_tests.sh fast` exclusively (5 seconds)
- **Before production**: Always run `./scripts/run_tests.sh pre-prod` locally first
- **Debugging specific areas**: Use category-specific tests (`unit`, `security`, etc.)
- **CI/CD confidence**: Only main branch runs expensive Firebase tests
- **Speed matters**: Development branch optimized for maximum speed (<5 sec feedback)