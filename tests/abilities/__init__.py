"""
Comprehensive ability testing module for Pokemon TCG Pocket cards.

This module provides automated testing frameworks for validating card abilities
in real battle scenarios, including:
- Coin flip mechanics testing
- Status effect validation  
- Energy manipulation testing
- Damage modification testing
- Battle simulation testing

Usage:
    from tests.abilities.test_ability_automation import ComprehensiveAbilityTester
    
    tester = ComprehensiveAbilityTester()
    tester.load_cards()
    tester.generate_test_scenarios()
    report = tester.run_all_ability_tests()
"""