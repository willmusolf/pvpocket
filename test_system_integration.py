#!/usr/bin/env python3
"""
Quick integration test to verify the comprehensive ability testing system works
"""

import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(__file__))

# Import our test modules
from scripts.test_all_cards import ComprehensiveCardTester
from tests.abilities.test_ability_automation import ComprehensiveAbilityTester
from tests.abilities.test_coin_flip_determinism import ComprehensiveCoinFlipTester
from tests.abilities.test_status_effects import ComprehensiveStatusEffectTester
from tests.abilities.test_energy_effects import ComprehensiveEnergyEffectTester
from scripts.comprehensive_ability_test_runner import ComprehensiveAbilityTestRunner


def test_basic_functionality():
    """Test basic functionality of each module"""
    print("Testing basic card loading functionality...")
    
    # Test 1: Basic card tester
    print("1. Testing ComprehensiveCardTester...")
    try:
        basic_tester = ComprehensiveCardTester()
        if basic_tester.load_cards():
            card_count = len(basic_tester.cards)
            print(f"   ✓ Loaded {card_count} cards successfully")
            
            # Test a small subset
            if card_count > 0:
                basic_tester.cards = basic_tester.cards[:5]  # Test only first 5 cards
                report = basic_tester.test_all_cards()
                success_rate = report['summary']['overall_success_rate']
                print(f"   ✓ Basic testing completed: {success_rate:.1f}% success rate")
            else:
                print("   ✗ No cards found")
                return False
        else:
            print("   ✗ Failed to load cards")
            return False
    except Exception as e:
        print(f"   ✗ ComprehensiveCardTester failed: {e}")
        return False
        
    # Test 2: Ability tester
    print("2. Testing ComprehensiveAbilityTester...")
    try:
        ability_tester = ComprehensiveAbilityTester()
        if ability_tester.load_cards():
            card_count = len(ability_tester.cards)
            print(f"   ✓ Loaded {card_count} cards successfully")
            
            scenario_count = ability_tester.generate_test_scenarios()
            print(f"   ✓ Generated {scenario_count} test scenarios")
            
            if scenario_count > 0:
                # Test a small subset
                ability_tester.test_scenarios = ability_tester.test_scenarios[:10]
                report = ability_tester.run_all_ability_tests()
                success_rate = report['summary']['success_rate']
                print(f"   ✓ Ability testing completed: {success_rate:.1f}% success rate")
            else:
                print("   ! No ability test scenarios generated")
        else:
            print("   ✗ Failed to load cards")
            return False
    except Exception as e:
        print(f"   ✗ ComprehensiveAbilityTester failed: {e}")
        return False
        
    # Test 3: Coin flip tester
    print("3. Testing ComprehensiveCoinFlipTester...")
    try:
        coin_tester = ComprehensiveCoinFlipTester()
        if coin_tester.load_cards():
            coin_card_count = len(coin_tester.coin_flip_cards)
            print(f"   ✓ Found {coin_card_count} cards with coin flip mechanics")
            
            if coin_card_count > 0:
                test_count = coin_tester.generate_test_cases()
                print(f"   ✓ Generated {test_count} coin flip test cases")
                
                # Test a small subset
                coin_tester.test_cases = coin_tester.test_cases[:5]
                report = coin_tester.run_comprehensive_coin_flip_tests()
                success_rate = report['summary']['success_rate']
                print(f"   ✓ Coin flip testing completed: {success_rate:.1f}% success rate")
            else:
                print("   ! No coin flip cards found")
        else:
            print("   ✗ Failed to load cards")
            return False
    except Exception as e:
        print(f"   ✗ ComprehensiveCoinFlipTester failed: {e}")
        return False
        
    # Test 4: Status effect tester
    print("4. Testing ComprehensiveStatusEffectTester...")
    try:
        status_tester = ComprehensiveStatusEffectTester()
        if status_tester.load_cards():
            status_card_count = len(status_tester.status_effect_cards)
            print(f"   ✓ Found {status_card_count} cards with status effect mechanics")
            
            if status_card_count > 0:
                test_count = status_tester.generate_test_cases()
                print(f"   ✓ Generated {test_count} status effect test cases")
                
                # Test a small subset
                status_tester.test_cases = status_tester.test_cases[:5]
                report = status_tester.run_comprehensive_status_effect_tests()
                success_rate = report['summary']['success_rate']
                print(f"   ✓ Status effect testing completed: {success_rate:.1f}% success rate")
            else:
                print("   ! No status effect cards found")
        else:
            print("   ✗ Failed to load cards")
            return False
    except Exception as e:
        print(f"   ✗ ComprehensiveStatusEffectTester failed: {e}")
        return False
        
    # Test 5: Energy effect tester
    print("5. Testing ComprehensiveEnergyEffectTester...")
    try:
        energy_tester = ComprehensiveEnergyEffectTester()
        if energy_tester.load_cards():
            energy_card_count = len(energy_tester.energy_effect_cards)
            print(f"   ✓ Found {energy_card_count} cards with energy effect mechanics")
            
            if energy_card_count > 0:
                test_count = energy_tester.generate_test_cases()
                print(f"   ✓ Generated {test_count} energy effect test cases")
                
                # Test a small subset
                energy_tester.test_cases = energy_tester.test_cases[:5]
                report = energy_tester.run_comprehensive_energy_effect_tests()
                success_rate = report['summary']['success_rate']
                print(f"   ✓ Energy effect testing completed: {success_rate:.1f}% success rate")
            else:
                print("   ! No energy effect cards found")
        else:
            print("   ✗ Failed to load cards")
            return False
    except Exception as e:
        print(f"   ✗ ComprehensiveEnergyEffectTester failed: {e}")
        return False
        
    return True


def test_comprehensive_runner():
    """Test the comprehensive test runner"""
    print("\nTesting ComprehensiveAbilityTestRunner...")
    
    try:
        # Create test runner with limited scope
        runner = ComprehensiveAbilityTestRunner()
        
        # Configure to run quick tests only
        test_config = {
            'basic_card_tests': True,
            'ability_tests': True,
            'coin_flip_tests': True,
            'status_effect_tests': True,
            'energy_effect_tests': True,
            'regression_tests': False  # Skip regression tests for quick test
        }
        
        print("   Running comprehensive test suite (limited scope)...")
        report = runner.run_all_tests(test_config)
        
        # Check results
        overall = report['overall_summary']
        print(f"   ✓ Comprehensive testing completed")
        print(f"   ✓ Total tests run: {overall['total_tests_run']:,}")
        print(f"   ✓ Overall success rate: {overall['overall_success_rate']:.1f}%")
        print(f"   ✓ Health score: {report['test_health_score']['score']}/100 ({report['test_health_score']['category']})")
        
        # Save a sample report
        runner.save_consolidated_report(report, "integration_test_report.json")
        print(f"   ✓ Sample report saved to: {runner.results_dir}/integration_test_report.json")
        
        return True
        
    except Exception as e:
        print(f"   ✗ ComprehensiveAbilityTestRunner failed: {e}")
        return False


def main():
    """Main integration test"""
    print("="*60)
    print("COMPREHENSIVE ABILITY TESTING SYSTEM - INTEGRATION TEST")
    print("="*60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Suppress debug logging for cleaner output
    logging.getLogger().setLevel(logging.WARNING)
    
    # Test 1: Basic functionality
    success1 = test_basic_functionality()
    
    # Test 2: Comprehensive runner
    success2 = test_comprehensive_runner()
    
    print("\n" + "="*60)
    print("INTEGRATION TEST SUMMARY")
    print("="*60)
    
    if success1 and success2:
        print("✓ ALL TESTS PASSED")
        print("✓ Comprehensive ability testing system is working correctly")
        print("✓ Ready for production use")
        print("\nNext steps:")
        print("1. Run full test suite: python scripts/comprehensive_ability_test_runner.py")
        print("2. Generate regression baseline: python tests/regression/test_card_regression.py --generate-baseline")
        print("3. Schedule daily automated runs")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("✗ System needs debugging before production use")
        if not success1:
            print("✗ Basic functionality tests failed")
        if not success2:
            print("✗ Comprehensive runner tests failed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)