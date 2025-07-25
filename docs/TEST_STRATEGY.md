# Test Strategy for Pokemon TCG Pocket App

## Overview

We use a **dual testing strategy** that balances speed and thoroughness:

1. **Fast Tests (Default)** - Mock-based tests that run quickly on every PR
2. **Integration Tests** - Real Firebase emulator tests that run on merges

## Test Categories

### 🚀 Fast Tests (Mock-Based)
- **When**: Every pull request, every push
- **Duration**: ~2-3 seconds
- **Coverage**: Code logic, API responses, security, performance
- **Data**: Mocked Firebase responses

### 🔍 Integration Tests (Real Data)
- **When**: Merges to main/development branches
- **Duration**: ~10-30 seconds
- **Coverage**: Real Firebase operations, data persistence
- **Data**: Seeded test data in Firebase emulator

## Running Tests Locally

### Quick Start (Fast Tests)
```bash
# Run all fast tests
pytest -m "not real_data"

# Or use the test runner
./scripts/run_tests.sh fast
```

### Full Integration Tests
```bash
# Start Firebase emulator and run all tests
./scripts/run_tests.sh full
```

### Specific Test Categories
```bash
# Unit tests only
pytest -m "unit"

# Security tests only
pytest -m "security"

# Performance tests only
pytest -m "performance"
```

## CI/CD Strategy

### Pull Requests
- Runs **fast tests** only
- Must pass before merge
- ~2-3 seconds execution time

### Main/Development Branches
- Runs **full test suite** including integration tests
- Tests real Firebase operations
- ~30 seconds execution time

### Test Workflow
```
Developer Push → Fast Tests (PR) → Review → Merge → Full Tests → Deploy
     ↑                                                    ↓
     └──────────── Fix if tests fail ←───────────────────┘
```

## Test Data

### Mock Data (Fast Tests)
- Defined in test fixtures
- Returns empty collections by default
- Individual tests mock specific data needs

### Seed Data (Integration Tests)
- Located in `tests/test_seed_data.json`
- Contains sample cards, users, and decks
- Automatically loaded by `scripts/seed_test_data.py`

## Best Practices

1. **Write Fast Tests First** - Most bugs can be caught with mocked tests
2. **Add Integration Tests for Critical Paths** - Database operations, authentication
3. **Keep Tests Independent** - Each test should set up its own data
4. **Use Appropriate Markers** - Tag tests with `@pytest.mark.unit`, etc.

## Example Test Structure

### Fast Test (Mocked)
```python
@pytest.mark.unit
def test_api_response_format(client, mock_card_data):
    """Fast test with mocked data."""
    with patch('app.services.get_cards') as mock:
        mock.return_value = mock_card_data
        response = client.get('/api/cards')
        assert response.status_code == 200
```

### Integration Test (Real Data)
```python
@pytest.mark.integration
@pytest.mark.real_data
def test_real_card_loading(client):
    """Integration test with real Firebase data."""
    # Requires RUN_INTEGRATION_TESTS=1 and Firebase emulator
    response = client.get('/api/cards')
    data = json.loads(response.data)
    assert len(data['cards']) >= 2  # Seeded data
```

## Troubleshooting

### Tests Pass Locally but Fail in CI
- Check environment variables
- Ensure Firebase emulator is running (for integration tests)
- Verify seed data is loaded

### "0 cards loaded" Messages
- **Normal for fast tests** - Using mocked data
- **Problem for integration tests** - Check Firebase emulator and seed data

### Slow Test Execution
- Use fast tests for development
- Run integration tests only before merge
- Use `pytest -m "not slow"` to skip slow tests

## Summary

### Refined Test Strategy (Updated)

**Automatic Testing**:
- **Pull Requests**: Fast tests (~2-3 seconds) with mocked data
- **Push to development**: Fast tests for quick staging validation  
- **Push to main**: Full test suite (~20-30 seconds) with Firebase emulator

**Manual Testing via GitHub Actions**:
1. Go to **Actions** tab in GitHub
2. Select **CI/CD Pipeline** workflow  
3. Click **Run workflow**
4. Choose test type:
   - `fast` - Quick tests with mocked data
   - `full` - Complete test suite with Firebase emulator
   - `unit` - Unit tests only
   - `security` - Security tests only
   - `performance` - Performance tests only

**Test Flow**:
```
Feature Branch → PR (Fast) → Development (Fast) → Main (Full) → Deploy
```

**Local Development**:
```bash
# Quick feedback (like PRs and development pushes)
pytest -m "not real_data" -v

# Full validation (like main pushes) 
./scripts/run_tests.sh full

# Specific categories
pytest -m "unit" -v      # Unit tests
pytest -m "security" -v  # Security tests
```