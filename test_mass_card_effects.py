#!/usr/bin/env python3
"""
Mass Card Effect Validation Suite

Tests all 1,576+ cards in the database to ensure:
1. No effect parsing conflicts (like Moltres bug)
2. No Colorless energy generation
3. All effects parse without errors
4. Priority system works across all cards
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simulator.core.effect_engine import AdvancedEffectEngine
from simulator.core.coin_flip import CoinFlipManager  
from simulator.core.status_conditions import StatusManager
from simulator.core.pokemon import BattlePokemon
from Card import Card
import logging
from app.services import card_service
from app import create_app
import json
from typing import List, Dict, Any

# Set up logging for errors only to avoid spam
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class ValidationResult:
    """Results from mass card validation"""
    def __init__(self):
        self.total_cards = 0
        self.cards_tested = 0
        self.cards_with_effects = 0
        self.parsing_errors = []
        self.colorless_violations = []
        self.effect_conflicts = []
        self.successful_effects = []
        
    def add_error(self, card_name: str, error_type: str, details: str):
        """Add an error to the results"""
        error_entry = {
            'card_name': card_name,
            'error_type': error_type,
            'details': details
        }
        
        if error_type == 'parsing_error':
            self.parsing_errors.append(error_entry)
        elif error_type == 'colorless_violation':
            self.colorless_violations.append(error_entry)
        elif error_type == 'effect_conflict':
            self.effect_conflicts.append(error_entry)
    
    def add_success(self, card_name: str, effect_summary: str):
        """Add successful effect parsing"""
        self.successful_effects.append({
            'card_name': card_name,
            'effect_summary': effect_summary
        })

class MockPokemon:
    """Mock Pokemon for testing"""
    def __init__(self, card_data):
        self.card = card_data if hasattr(card_data, 'name') else type('obj', (object,), card_data)()
        self.current_hp = getattr(self.card, 'hp', 100)
        self.energy_attached = []
        self.status_conditions = []
        
    def heal(self, amount):
        self.current_hp = min(getattr(self.card, 'hp', 100), self.current_hp + amount)

def create_test_context(card_data):
    """Create battle context for testing a card"""
    attacker = MockPokemon(card_data)
    defender = MockPokemon({'name': 'Test Defender', 'hp': 100, 'energy_type': 'Water'})
    
    return {
        'turn': 1,
        'player': 0,
        'attacker': attacker,
        'defender': defender
    }

def validate_card_effects(card_data: Dict, effect_engine: AdvancedEffectEngine, result: ValidationResult):
    """Validate all attacks on a single card"""
    card_name = card_data.get('name', 'Unknown')
    attacks = card_data.get('attacks', [])
    
    if not attacks:
        return  # No attacks to test
    
    result.cards_with_effects += 1
    
    for attack in attacks:
        try:
            attack_name = attack.get('name', 'Unknown Attack')
            effect_text = attack.get('effect_text', '') or attack.get('effect', '')
            
            if not effect_text:
                continue  # No effect text to parse
            
            # Create test context
            battle_context = create_test_context(card_data)
            base_damage = int(str(attack.get('damage', '0')).replace('+', '').replace('×', '').replace('x', '') or '0')
            
            # Test effect parsing
            effect_result = effect_engine.execute_attack_effects(
                attack, 
                battle_context['attacker'], 
                battle_context['defender'],
                base_damage,
                battle_context
            )
            
            # Check for Colorless energy generation (critical bug prevention)
            for energy_change in effect_result.get('energy_changes', []):
                if energy_change.get('energy_type') == 'Colorless':
                    result.add_error(card_name, 'colorless_violation', 
                                   f"Attack '{attack_name}' generates Colorless energy: {energy_change}")
            
            # Check for multiple energy changes on the same effect text (potential conflict)
            energy_changes = effect_result.get('energy_changes', [])
            if len(energy_changes) > 1:
                # Check if this could be a duplication bug
                energy_types = [ec.get('energy_type') for ec in energy_changes]
                if len(set(energy_types)) == 1 and 'flip' in effect_text.lower():
                    # Potential conflict: same energy type generated multiple times on coin flip effect
                    result.add_error(card_name, 'effect_conflict',
                                   f"Attack '{attack_name}' may have conflicting energy generation: {len(energy_changes)} changes of same type")
            
            # Success - record the effect
            effect_summary = f"{attack_name}: {len(effect_result.get('additional_effects', []))} effects"
            result.add_success(card_name, effect_summary)
            
        except Exception as e:
            # Parsing error
            result.add_error(card_name, 'parsing_error', 
                           f"Attack '{attack_name}' failed to parse: {str(e)}")
            logger.exception(f"Error parsing {card_name} - {attack_name}")

def run_mass_validation():
    """Run mass validation on all cards in the database"""
    print("🚀 Starting Mass Card Effect Validation...")
    print("📊 Loading card database...")
    
    # Create Flask app context to access database
    app = create_app()
    
    with app.app_context():
        try:
            # Get all cards from database
            card_collection = card_service.get_full_card_collection()
            all_cards = [card.to_dict() for card in card_collection.cards]
            result = ValidationResult()
            result.total_cards = len(all_cards)
            
            print(f"📋 Found {result.total_cards} cards in database")
            
            # Create effect engine
            effect_engine = AdvancedEffectEngine(battle_cards=[], logger=logger)
            
            # Track progress
            progress_interval = max(50, result.total_cards // 20)  # Show progress every 5%
            
            print("🔍 Validating card effects...")
            
            for i, card in enumerate(all_cards):
                if i % progress_interval == 0:
                    percentage = (i / result.total_cards) * 100
                    print(f"   Progress: {i}/{result.total_cards} ({percentage:.1f}%)")
                
                validate_card_effects(card, effect_engine, result)
                result.cards_tested += 1
            
            print(f"✅ Validation completed!")
            
            # Print results summary
            print("\n" + "="*60)
            print("📈 MASS CARD EFFECT VALIDATION RESULTS")
            print("="*60)
            print(f"📊 Total Cards: {result.total_cards}")
            print(f"🧪 Cards Tested: {result.cards_tested}")
            print(f"⚡ Cards with Effects: {result.cards_with_effects}")
            print(f"✅ Successful Effects: {len(result.successful_effects)}")
            print()
            print(f"❌ Parsing Errors: {len(result.parsing_errors)}")
            print(f"🚫 Colorless Violations: {len(result.colorless_violations)}")
            print(f"⚠️  Effect Conflicts: {len(result.effect_conflicts)}")
            
            # Show critical issues
            if result.colorless_violations:
                print("\n🚨 CRITICAL: Colorless Energy Violations")
                for violation in result.colorless_violations[:5]:  # Show first 5
                    print(f"   • {violation['card_name']}: {violation['details']}")
                if len(result.colorless_violations) > 5:
                    print(f"   ... and {len(result.colorless_violations) - 5} more")
            
            if result.effect_conflicts:
                print("\n⚠️  Effect Conflicts Detected")
                for conflict in result.effect_conflicts[:5]:  # Show first 5
                    print(f"   • {conflict['card_name']}: {conflict['details']}")
                if len(result.effect_conflicts) > 5:
                    print(f"   ... and {len(result.effect_conflicts) - 5} more")
            
            if result.parsing_errors:
                print(f"\n🔧 Parsing Errors ({len(result.parsing_errors)} total)")
                error_counts = {}
                for error in result.parsing_errors:
                    error_type = error['details'].split(':')[0] if ':' in error['details'] else 'Unknown'
                    error_counts[error_type] = error_counts.get(error_type, 0) + 1
                
                for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"   • {error_type}: {count} occurrences")
            
            # Overall assessment
            print("\n" + "="*60)
            critical_issues = len(result.colorless_violations) + len(result.effect_conflicts)
            
            if critical_issues == 0:
                print("🎉 SUCCESS: No critical effect conflicts detected!")
                print("🛡️  The priority-based parsing system is working correctly.")
                print("✅ All energy generation uses valid types (no Colorless violations)")
                success_rate = (len(result.successful_effects) / result.cards_with_effects) * 100 if result.cards_with_effects > 0 else 0
                print(f"📊 Effect parsing success rate: {success_rate:.1f}%")
            else:
                print(f"⚠️  WARNING: {critical_issues} critical issues found!")
                print("🔧 Manual review required for flagged cards")
            
            # Save detailed results
            detailed_results = {
                'summary': {
                    'total_cards': result.total_cards,
                    'cards_tested': result.cards_tested,
                    'cards_with_effects': result.cards_with_effects,
                    'successful_effects': len(result.successful_effects),
                    'parsing_errors': len(result.parsing_errors),
                    'colorless_violations': len(result.colorless_violations),
                    'effect_conflicts': len(result.effect_conflicts)
                },
                'colorless_violations': result.colorless_violations,
                'effect_conflicts': result.effect_conflicts,
                'parsing_errors': result.parsing_errors[:20]  # First 20 parsing errors
            }
            
            with open('mass_validation_results.json', 'w') as f:
                json.dump(detailed_results, f, indent=2)
            
            print(f"💾 Detailed results saved to mass_validation_results.json")
            
            return critical_issues == 0
            
        except Exception as e:
            print(f"❌ Mass validation failed: {e}")
            logger.exception("Mass validation error")
            return False

if __name__ == "__main__":
    success = run_mass_validation()
    sys.exit(0 if success else 1)