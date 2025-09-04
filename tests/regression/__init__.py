"""
Regression testing module for Pokemon TCG Pocket cards.

This module provides automated regression testing frameworks to catch when
code updates break existing card functionality by comparing against
established baselines.

Features:
- Baseline generation and storage
- Comprehensive card comparison
- Severity-based issue classification
- Automated regression detection

Usage:
    from tests.regression.test_card_regression import CardRegressionTester
    
    tester = CardRegressionTester()
    tester.load_cards()
    tester.generate_baseline()  # First time only
    report = tester.run_regression_tests()
"""