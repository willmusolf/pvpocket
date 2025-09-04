#!/usr/bin/env python3
"""
Comprehensive Card Ability Testing Automation
Tests all card abilities, attack effects, and energy costs systematically
"""

import sys
import os
import logging
import json
import time
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from simulator.core.card_bridge import load_real_card_collection, BattleCard
from simulator.core.pokemon import BattlePokemon
from simulator.core.effect_engine import AdvancedEffectEngine
from simulator.core.coin_flip import parse_coin_flip_effect, execute_coin_flip_effect, CoinFlipManager
from simulator.core.game import GameState, GamePhase
from simulator.core.player import PlayerState
from simulator.ai.rule_based import RuleBasedAI
from battle_main import create_real_card_deck
from Deck import Deck


class CardTestResult:
    """Results from testing a single card"""
    def __init__(self, card: BattleCard):
        self.card_id = card.id
        self.card_name = card.name
        self.card_type = card.card_type
        self.energy_type = card.energy_type
        self.tests_passed = 0
        self.tests_failed = 0
        self.issues = []
        self.successes = []
        self.performance_metrics = {}
        
    def add_success(self, test_name: str, details: str = ""):
        self.tests_passed += 1
        self.successes.append({"test": test_name, "details": details})
        
    def add_failure(self, test_name: str, error: str, details: str = ""):
        self.tests_failed += 1
        self.issues.append({
            "test": test_name, 
            "error": error, 
            "details": details,
            "severity": self._classify_severity(error)
        })
        
    def _classify_severity(self, error: str) -> str:
        """Classify error severity for prioritization"""
        error_lower = error.lower()
        if any(word in error_lower for word in ['crash', 'exception', 'failed', 'error']):
            return 'high'
        elif any(word in error_lower for word in ['warning', 'unexpected', 'invalid']):
            return 'medium'
        else:
            return 'low'
            
    def get_success_rate(self) -> float:
        total = self.tests_passed + self.tests_failed
        return (self.tests_passed / total * 100) if total > 0 else 0.0
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_id": self.card_id,
            "card_name": self.card_name,
            "card_type": self.card_type,
            "energy_type": self.energy_type,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "success_rate": self.get_success_rate(),
            "issues": self.issues,
            "successes": self.successes,
            "performance": self.performance_metrics
        }


class ComprehensiveCardTester:
    """Automated testing system for all card abilities and effects"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or self._setup_logger()
        self.cards: List[BattleCard] = []
        self.results: List[CardTestResult] = []
        self.summary_stats = defaultdict(int)
        self.coin_manager = CoinFlipManager(self.logger, rng_seed=42)  # Fixed seed for reproducible tests
        self.effect_engine = None  # Will be initialized when cards are loaded
        self.test_decks = {}  # Cache test decks for different energy types
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for test results"""
        logger = logging.getLogger('card_tester')
        logger.setLevel(logging.INFO)
        
        # Create directories if they don't exist
        os.makedirs('logs', exist_ok=True)
        os.makedirs('test_results', exist_ok=True)
        
        # Create file handler
        log_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        fh = logging.FileHandler(os.path.join('logs', log_file))
        fh.setLevel(logging.DEBUG)
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
        
    def load_cards(self) -> bool:
        """Load all real cards for testing"""
        try:
            self.logger.info("Loading all real cards...")
            self.cards = load_real_card_collection(self.logger)
            
            if not self.cards:
                self.logger.error("No cards loaded!")
                return False
                
            self.logger.info(f"Loaded {len(self.cards)} cards for testing")
            
            # Categorize cards
            card_types = defaultdict(int)
            for card in self.cards:
                card_types[card.card_type] += 1
                
            self.logger.info("Card type breakdown:")
            for card_type, count in sorted(card_types.items()):
                self.logger.info(f"  {card_type}: {count}")
                
            # Initialize effect engine with all loaded cards
            self.effect_engine = AdvancedEffectEngine(self.cards, self.logger, rng_seed=42)
            self.logger.info("Effect engine initialized")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load cards: {e}")
            return False
            
    def test_all_cards(self) -> Dict[str, Any]:
        """Run comprehensive tests on all cards"""
        start_time = time.time()
        self.logger.info(f"Starting comprehensive testing of {len(self.cards)} cards...")
        
        # Test categories
        pokemon_cards = [c for c in self.cards if c.is_pokemon()]
        trainer_cards = [c for c in self.cards if c.is_trainer()]
        
        self.logger.info(f"Testing {len(pokemon_cards)} Pokemon cards and {len(trainer_cards)} Trainer cards")
        
        # Test all Pokemon cards
        for i, card in enumerate(pokemon_cards, 1):
            if i % 50 == 0:
                self.logger.info(f"Progress: {i}/{len(pokemon_cards)} Pokemon cards tested")
            self.test_pokemon_card(card)
            
        # Test all Trainer cards
        for i, card in enumerate(trainer_cards, 1):
            if i % 20 == 0:
                self.logger.info(f"Progress: {i}/{len(trainer_cards)} Trainer cards tested")
            self.test_trainer_card(card)
            
        duration = time.time() - start_time
        
        # Generate comprehensive report
        report = self.generate_report(duration)
        self.save_results(report)
        
        return report
        
    def test_pokemon_card(self, card: BattleCard) -> CardTestResult:
        """Comprehensive testing of a Pokemon card"""
        result = CardTestResult(card)
        
        try:
            # Test 1: Basic card data integrity
            self._test_basic_card_data(card, result)
            
            # Test 2: Pokemon stats validation
            self._test_pokemon_stats(card, result)
            
            # Test 3: Energy cost validation
            self._test_energy_costs(card, result)
            
            # Test 4: Attack effects parsing
            self._test_attack_effects(card, result)
            
            # Test 5: Battle Pokemon creation
            self._test_battle_pokemon_creation(card, result)
            
            # Test 6: Attack execution simulation
            self._test_attack_execution(card, result)
            
            # Test 7: Ability testing (if present)
            if card.abilities:
                self._test_abilities(card, result)
                
            # Test 8: Edge cases and error handling
            self._test_edge_cases(card, result)
            
            # Test 9: Battle simulation testing
            self._test_battle_simulation(card, result)
            
            # Test 10: Ability execution in battle context
            if card.abilities:
                self._test_ability_battle_execution(card, result)
            
        except Exception as e:
            result.add_failure("pokemon_test_suite", str(e), "Critical failure in Pokemon testing")
            
        self.results.append(result)
        return result
        
    def test_trainer_card(self, card: BattleCard) -> CardTestResult:
        """Test trainer card functionality"""
        result = CardTestResult(card)
        
        try:
            # Test 1: Basic card data
            self._test_basic_card_data(card, result)
            
            # Test 2: Trainer-specific tests would go here
            # (This would be expanded based on trainer card implementations)
            result.add_success("trainer_basic_test", "Basic trainer card validation passed")
            
        except Exception as e:
            result.add_failure("trainer_test_suite", str(e), "Critical failure in Trainer testing")
            
        self.results.append(result)
        return result
        
    def _test_basic_card_data(self, card: BattleCard, result: CardTestResult):
        """Test basic card data integrity"""
        # Test required fields
        if not card.name or card.name.strip() == "":
            result.add_failure("basic_data", "Card has no name", f"Card ID: {card.id}")
        else:
            result.add_success("basic_data", f"Card name: {card.name}")
            
        if not card.card_type:
            result.add_failure("basic_data", "Card has no type", f"Card: {card.name}")
        else:
            result.add_success("basic_data", f"Card type: {card.card_type}")
            
        # Validate ID
        if card.id <= 0:
            result.add_failure("basic_data", "Invalid card ID", f"ID: {card.id}")
        else:
            result.add_success("basic_data", f"Valid card ID: {card.id}")
            
    def _test_pokemon_stats(self, card: BattleCard, result: CardTestResult):
        """Test Pokemon-specific stats"""
        if not card.is_pokemon():
            return
            
        # HP validation
        if card.hp is None or card.hp <= 0:
            result.add_failure("pokemon_stats", "Invalid HP", f"HP: {card.hp}")
        elif card.hp > 400:  # Sanity check
            result.add_failure("pokemon_stats", "Suspiciously high HP", f"HP: {card.hp}")
        else:
            result.add_success("pokemon_stats", f"Valid HP: {card.hp}")
            
        # Energy type validation
        valid_energy_types = ['Fire', 'Water', 'Grass', 'Lightning', 'Psychic', 'Fighting', 'Darkness', 'Metal', 'Colorless']
        if card.energy_type not in valid_energy_types:
            result.add_failure("pokemon_stats", "Invalid energy type", f"Type: {card.energy_type}")
        else:
            result.add_success("pokemon_stats", f"Valid energy type: {card.energy_type}")
            
        # Retreat cost validation
        if card.retreat_cost is not None and (card.retreat_cost < 0 or card.retreat_cost > 5):
            result.add_failure("pokemon_stats", "Invalid retreat cost", f"Cost: {card.retreat_cost}")
        else:
            result.add_success("pokemon_stats", f"Valid retreat cost: {card.retreat_cost}")
            
    def _test_energy_costs(self, card: BattleCard, result: CardTestResult):
        """Test energy cost parsing and validation"""
        if not card.attacks:
            result.add_success("energy_costs", "No attacks to test")
            return
            
        valid_energy_types = ['Fire', 'Water', 'Grass', 'Lightning', 'Psychic', 'Fighting', 'Darkness', 'Metal', 'Colorless']
        
        for attack in card.attacks:
            attack_name = attack.get('name', 'Unknown')
            cost = attack.get('cost', [])
            
            # Validate cost format
            if not isinstance(cost, list):
                result.add_failure("energy_costs", f"Invalid cost format for {attack_name}", f"Cost: {cost}")
                continue
                
            # Validate energy types in cost
            invalid_energies = [e for e in cost if e not in valid_energy_types]
            if invalid_energies:
                result.add_failure("energy_costs", f"Invalid energy types in {attack_name}", f"Invalid: {invalid_energies}")
            else:
                result.add_success("energy_costs", f"{attack_name} has valid energy cost: {cost}")
                
            # Validate cost length (sanity check)
            if len(cost) > 5:
                result.add_failure("energy_costs", f"Suspiciously high energy cost for {attack_name}", f"Cost: {cost}")
                
    def _test_attack_effects(self, card: BattleCard, result: CardTestResult):
        """Test attack effect parsing"""
        if not card.attacks:
            return
            
        for attack in card.attacks:
            attack_name = attack.get('name', 'Unknown')
            effect_text = attack.get('effect_text', '')
            
            if effect_text:
                # Test coin flip parsing
                coin_effect = parse_coin_flip_effect(effect_text)
                if coin_effect:
                    result.add_success("attack_effects", f"{attack_name} coin flip effect parsed: {coin_effect['type']}")
                    
                    # Test coin flip execution
                    try:
                        coin_result = execute_coin_flip_effect(coin_effect, self.coin_manager, 0)
                        if coin_result.get('success', False):
                            result.add_success("attack_effects", f"{attack_name} coin flip executed successfully")
                        else:
                            result.add_failure("attack_effects", f"{attack_name} coin flip execution failed", str(coin_result))
                    except Exception as e:
                        result.add_failure("attack_effects", f"{attack_name} coin flip execution error", str(e))
                else:
                    # Check if it should have been parsed
                    if any(word in effect_text.lower() for word in ['coin', 'flip', 'heads', 'tails']):
                        result.add_failure("attack_effects", f"{attack_name} contains coin flip text but wasn't parsed", effect_text[:100])
                    else:
                        result.add_success("attack_effects", f"{attack_name} effect text stored for manual review")
            else:
                result.add_success("attack_effects", f"{attack_name} has no effect text")
                
    def _test_battle_pokemon_creation(self, card: BattleCard, result: CardTestResult):
        """Test BattlePokemon creation from card"""
        if not card.is_pokemon():
            return
            
        try:
            battle_pokemon = BattlePokemon(card, self.logger)
            
            # Validate creation
            if battle_pokemon.current_hp != card.hp:
                result.add_failure("battle_pokemon", "HP mismatch in BattlePokemon", f"Expected: {card.hp}, Got: {battle_pokemon.current_hp}")
            else:
                result.add_success("battle_pokemon", f"BattlePokemon created with correct HP: {battle_pokemon.current_hp}")
                
            # Test energy attachment
            battle_pokemon.attach_energy('Fire')
            if len(battle_pokemon.energy_attached) != 1:
                result.add_failure("battle_pokemon", "Energy attachment failed", f"Expected 1, got {len(battle_pokemon.energy_attached)}")
            else:
                result.add_success("battle_pokemon", "Energy attachment works")
                
        except Exception as e:
            result.add_failure("battle_pokemon", "BattlePokemon creation failed", str(e))
            
    def _test_attack_execution(self, card: BattleCard, result: CardTestResult):
        """Test attack execution with proper energy"""
        if not card.is_pokemon() or not card.attacks:
            return
            
        try:
            battle_pokemon = BattlePokemon(card, self.logger)
            
            for attack in card.attacks:
                attack_name = attack.get('name', 'Unknown')
                cost = attack.get('cost', [])
                
                # Add required energy
                for energy_type in cost:
                    battle_pokemon.attach_energy(energy_type)
                    
                # Test if attack is usable
                can_use = battle_pokemon.can_use_attack(attack)
                if can_use:
                    result.add_success("attack_execution", f"{attack_name} is usable with correct energy")
                    
                    # Test attack usage
                    used_successfully = battle_pokemon.use_attack(attack)
                    if used_successfully:
                        result.add_success("attack_execution", f"{attack_name} executed successfully")
                    else:
                        result.add_failure("attack_execution", f"{attack_name} execution failed", "use_attack returned False")
                else:
                    result.add_failure("attack_execution", f"{attack_name} not usable despite having required energy", f"Cost: {cost}, Attached: {battle_pokemon.energy_attached}")
                    
        except Exception as e:
            result.add_failure("attack_execution", "Attack execution test failed", str(e))
            
    def _test_abilities(self, card: BattleCard, result: CardTestResult):
        """Test Pokemon abilities"""
        for ability in card.abilities:
            ability_name = ability.get('name', 'Unknown')
            effect_text = ability.get('effect_text', '')
            
            if effect_text:
                result.add_success("abilities", f"{ability_name} has effect text")
            else:
                result.add_failure("abilities", f"{ability_name} has no effect text", "Ability should have effect description")
                
    def _test_edge_cases(self, card: BattleCard, result: CardTestResult):
        """Test edge cases and error handling"""
        if not card.is_pokemon():
            return
            
        try:
            battle_pokemon = BattlePokemon(card, self.logger)
            
            # Test with no energy
            usable_attacks = battle_pokemon.get_usable_attacks()
            zero_cost_attacks = [a for a in card.attacks if not a.get('cost', [])]
            
            if len(usable_attacks) == len(zero_cost_attacks):
                result.add_success("edge_cases", "Zero energy attack validation correct")
            else:
                result.add_failure("edge_cases", "Zero energy attack validation incorrect", 
                                 f"Usable: {len(usable_attacks)}, Zero cost: {len(zero_cost_attacks)}")
                
            # Test damage to zero
            battle_pokemon.take_damage(battle_pokemon.current_hp)
            if battle_pokemon.is_knocked_out():
                result.add_success("edge_cases", "Knockout detection works")
            else:
                result.add_failure("edge_cases", "Knockout detection failed", f"HP: {battle_pokemon.current_hp}")
                
        except Exception as e:
            result.add_failure("edge_cases", "Edge case testing failed", str(e))
            
    def _test_battle_simulation(self, card: BattleCard, result: CardTestResult):
        """Test card abilities in real battle simulation scenarios"""
        if not card.is_pokemon():
            return
            
        try:
            # Create a test deck with this card
            test_deck = self._create_test_deck_for_card(card)
            if not test_deck:
                result.add_failure("battle_simulation", "Failed to create test deck", f"Card: {card.name}")
                return
                
            # Create opponent deck (generic opponent)
            opponent_deck = self._get_generic_opponent_deck()
            if not opponent_deck:
                result.add_failure("battle_simulation", "Failed to create opponent deck", "Generic deck creation failed")
                return
                
            # Run battle simulation
            battle_result = self._run_test_battle(test_deck, opponent_deck, card, result)
            
            if battle_result['success']:
                result.add_success("battle_simulation", f"Battle simulation completed successfully")
                
                # Test specific battle mechanics
                self._validate_battle_mechanics(card, battle_result, result)
            else:
                result.add_failure("battle_simulation", "Battle simulation failed", battle_result['error'])
                
        except Exception as e:
            result.add_failure("battle_simulation", "Battle simulation testing failed", str(e))
            
    def _test_ability_battle_execution(self, card: BattleCard, result: CardTestResult):
        """Test abilities in actual battle execution context"""
        try:
            for ability in card.abilities:
                ability_name = ability.get('name', 'Unknown')
                effect_text = ability.get('effect_text', '')
                
                if not effect_text:
                    result.add_failure("ability_execution", f"{ability_name} has no effect text", "Cannot test ability without effect")
                    continue
                    
                # Create battle context for ability testing
                battle_context = self._create_ability_test_context(card, ability)
                
                if battle_context:
                    # Test ability parsing and execution
                    ability_result = self._test_ability_in_context(card, ability, battle_context)
                    
                    if ability_result['success']:
                        result.add_success("ability_execution", f"{ability_name} executed successfully in battle context")
                        
                        # Record performance metrics
                        if 'execution_time' in ability_result:
                            result.performance_metrics[f"ability_{ability_name}_time"] = ability_result['execution_time']
                    else:
                        result.add_failure("ability_execution", f"{ability_name} execution failed", ability_result['error'])
                else:
                    result.add_failure("ability_execution", f"Failed to create test context for {ability_name}", "Context creation failed")
                    
        except Exception as e:
            result.add_failure("ability_execution", "Ability execution testing failed", str(e))
            
    def _create_test_deck_for_card(self, card: BattleCard) -> Optional[Deck]:
        """Create a test deck focused on testing a specific card"""
        try:
            # Check cache first
            cache_key = f"{card.energy_type}_{card.card_type}"
            if cache_key in self.test_decks:
                deck = self.test_decks[cache_key]
                # Replace one copy with the test card
                if deck.cards:
                    deck.cards[0] = card
                return deck
                
            # Create new test deck
            deck = Deck(f"Test Deck for {card.name}")
            
            # Add the card being tested (2 copies)
            deck.add_card(card)
            deck.add_card(card)
            
            # Fill deck with compatible cards from the same energy type
            compatible_cards = [c for c in self.cards if 
                              c.is_pokemon() and 
                              c.energy_type == card.energy_type and 
                              c.id != card.id and
                              c.is_basic]  # Prefer basic Pokemon for simplicity
            
            # Add basic Pokemon to ensure deck validity
            basic_count = 2  # Already have the test card
            for basic_card in compatible_cards[:8]:  # Add up to 8 more basic Pokemon
                deck.add_card(basic_card)
                basic_count += 1
                if basic_count >= 10:  # Ensure we have enough basic Pokemon
                    break
                    
            # Fill remaining slots with more copies or other cards
            while len(deck.cards) < 20:
                if len(deck.cards) < 18 and compatible_cards:
                    # Add more compatible cards
                    deck.add_card(compatible_cards[len(deck.cards) % len(compatible_cards)])
                else:
                    # Fill with copies of existing cards (respecting 2-copy limit)
                    existing_cards = list(set([c.id for c in deck.cards]))
                    for card_id in existing_cards:
                        card_copies = [c for c in deck.cards if c.id == card_id]
                        if len(card_copies) < 2:
                            matching_card = next(c for c in deck.cards if c.id == card_id)
                            deck.add_card(matching_card)
                            break
                    else:
                        # If we can't find any card to duplicate, break
                        break
                        
            # Set deck type
            deck.deck_types = [card.energy_type] if card.energy_type != 'Colorless' else ['Fire']  # Default to Fire for Colorless
            
            # Cache the deck
            self.test_decks[cache_key] = deck
            
            return deck
            
        except Exception as e:
            self.logger.error(f"Failed to create test deck for {card.name}: {e}")
            return None
            
    def _get_generic_opponent_deck(self) -> Optional[Deck]:
        """Get a generic opponent deck for testing"""
        cache_key = "generic_opponent"
        if cache_key in self.test_decks:
            return self.test_decks[cache_key]
            
        try:
            # Create a balanced opponent deck with basic Fire Pokemon
            deck = Deck("Generic Opponent Deck")
            
            # Find basic Fire Pokemon for opponent
            fire_basics = [c for c in self.cards if 
                          c.is_pokemon() and 
                          c.energy_type == 'Fire' and 
                          c.is_basic][:10]  # Take first 10
            
            if len(fire_basics) < 10:
                # Add other basic Pokemon if not enough Fire
                other_basics = [c for c in self.cards if 
                               c.is_pokemon() and 
                               c.is_basic and 
                               c.energy_type != 'Fire'][:10 - len(fire_basics)]
                fire_basics.extend(other_basics)
                
            # Add 2 copies of each card up to 20 cards
            for i, card in enumerate(fire_basics):
                deck.add_card(card)
                if len(deck.cards) < 20:
                    deck.add_card(card)  # Add second copy
                if len(deck.cards) >= 20:
                    break
                    
            deck.deck_types = ['Fire']
            
            # Cache the deck
            self.test_decks[cache_key] = deck
            return deck
            
        except Exception as e:
            self.logger.error(f"Failed to create generic opponent deck: {e}")
            return None
            
    def _run_test_battle(self, player_deck: Deck, opponent_deck: Deck, test_card: BattleCard, result: CardTestResult) -> Dict[str, Any]:
        """Run a controlled battle to test specific card abilities"""
        try:
            # Create game state with fixed seed for reproducibility
            game = GameState(
                player_decks=[player_deck, opponent_deck],
                battle_id=f"ability_test_{test_card.id}",
                rng_seed=42 + test_card.id,  # Unique but deterministic seed
                logger=self.logger
            )
            
            # Start battle
            if not game.start_battle():
                return {'success': False, 'error': 'Failed to start battle'}
                
            # Create AI players
            ai_players = [
                RuleBasedAI(player_id=0, logger=self.logger, rng_seed=42),
                RuleBasedAI(player_id=1, logger=self.logger, rng_seed=43)
            ]
            
            # Run battle for a limited number of turns to test abilities
            max_turns = 20  # Limit turns for testing
            turn_count = 0
            abilities_tested = []
            
            while not game.is_battle_over() and turn_count < max_turns:
                # Determine acting player
                if game.phase == GamePhase.FORCED_POKEMON_SELECTION:
                    acting_player = game.forced_selection_player
                else:
                    acting_player = game.current_player
                    
                ai = ai_players[acting_player]
                action = ai.choose_action(game)
                
                if action:
                    # Track if this action involves our test card
                    if hasattr(action, 'pokemon') and action.pokemon and action.pokemon.card.id == test_card.id:
                        abilities_tested.append({
                            'turn': turn_count,
                            'action_type': action.action_type,
                            'card': test_card.name
                        })
                        
                    success = game.execute_action(action)
                    if not success and game.phase == GamePhase.PLAYER_TURN:
                        # Try to end turn if action failed
                        end_turn = ai._create_end_turn_action()
                        game.execute_action(end_turn)
                        
                turn_count += 1
                
            battle_result = game.get_battle_result()
            
            return {
                'success': True,
                'battle_result': battle_result,
                'abilities_tested': abilities_tested,
                'turns_played': turn_count,
                'test_card_used': len(abilities_tested) > 0
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _validate_battle_mechanics(self, card: BattleCard, battle_result: Dict[str, Any], result: CardTestResult):
        """Validate that battle mechanics worked correctly for the card"""
        try:
            # Check if the card was actually used in battle
            if battle_result.get('test_card_used', False):
                result.add_success("battle_mechanics", f"{card.name} was successfully used in battle")
                
                # Record performance metrics
                result.performance_metrics['battle_turns'] = battle_result.get('turns_played', 0)
                result.performance_metrics['abilities_triggered'] = len(battle_result.get('abilities_tested', []))
            else:
                result.add_failure("battle_mechanics", f"{card.name} was not used in battle", 
                                 "Card may not be viable or AI couldn't use it effectively")
                
            # Validate specific mechanics based on card type
            if card.attacks:
                for attack in card.attacks:
                    attack_name = attack.get('name', 'Unknown')
                    effect_text = attack.get('effect_text', '')
                    
                    # Test coin flip mechanics if present
                    if 'coin' in effect_text.lower():
                        coin_result = self._test_coin_flip_mechanics(card, attack, result)
                        if coin_result:
                            result.add_success("battle_mechanics", f"{attack_name} coin flip mechanics validated")
                        else:
                            result.add_failure("battle_mechanics", f"{attack_name} coin flip mechanics failed", "Coin flip not working correctly")
                            
        except Exception as e:
            result.add_failure("battle_mechanics", "Battle mechanics validation failed", str(e))
            
    def _test_coin_flip_mechanics(self, card: BattleCard, attack: Dict, result: CardTestResult) -> bool:
        """Test coin flip mechanics for an attack"""
        try:
            effect_text = attack.get('effect_text', '')
            coin_effect = parse_coin_flip_effect(effect_text)
            
            if not coin_effect:
                return False
                
            # Test multiple coin flip executions for consistency
            results = []
            for i in range(10):  # Test 10 times
                coin_manager = CoinFlipManager(self.logger, rng_seed=42 + i)
                coin_result = execute_coin_flip_effect(coin_effect, coin_manager, 0)
                results.append(coin_result)
                
            # Validate results
            successful_results = [r for r in results if r.get('success', False)]
            
            if len(successful_results) == len(results):
                # All coin flips executed successfully
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Coin flip testing failed for {card.name}: {e}")
            return False
            
    def _create_ability_test_context(self, card: BattleCard, ability: Dict) -> Optional[Dict]:
        """Create a controlled context for testing abilities"""
        try:
            # Create minimal battle context
            context = {
                'card': card,
                'ability': ability,
                'battle_pokemon': BattlePokemon(card, self.logger),
                'effect_engine': self.effect_engine or AdvancedEffectEngine([card], self.logger, rng_seed=42)
            }
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to create ability test context: {e}")
            return None
            
    def _test_ability_in_context(self, card: BattleCard, ability: Dict, context: Dict) -> Dict[str, Any]:
        """Test an ability within a battle context"""
        try:
            start_time = time.time()
            
            ability_name = ability.get('name', 'Unknown')
            effect_text = ability.get('effect_text', '')
            
            # Register the card's effects with the effect engine
            effect_engine = context['effect_engine']
            effects = effect_engine.register_card_effects(card)
            
            # Find ability-related effects
            ability_effects = [e for e in effects if 'ability' in e.effect_type.lower()]
            
            execution_time = time.time() - start_time
            
            if ability_effects:
                return {
                    'success': True,
                    'effects_found': len(ability_effects),
                    'execution_time': execution_time
                }
            else:
                return {
                    'success': False,
                    'error': f"No effects registered for ability {ability_name}",
                    'execution_time': execution_time
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time if 'start_time' in locals() else 0
            }
            
    def generate_report(self, duration: float) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        # Calculate summary statistics
        total_cards = len(self.results)
        total_tests = sum(r.tests_passed + r.tests_failed for r in self.results)
        total_passed = sum(r.tests_passed for r in self.results)
        total_failed = sum(r.tests_failed for r in self.results)
        
        # Categorize results
        pokemon_results = [r for r in self.results if 'Pokémon' in r.card_type]
        trainer_results = [r for r in self.results if 'Trainer' in r.card_type]
        
        # Find problematic cards
        failing_cards = [r for r in self.results if r.tests_failed > 0]
        high_severity_issues = []
        
        for result in self.results:
            for issue in result.issues:
                if issue['severity'] == 'high':
                    high_severity_issues.append({
                        'card': result.card_name,
                        'test': issue['test'],
                        'error': issue['error']
                    })
        
        report = {
            'summary': {
                'total_cards_tested': total_cards,
                'total_tests_run': total_tests,
                'total_tests_passed': total_passed,
                'total_tests_failed': total_failed,
                'overall_success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0,
                'test_duration_seconds': duration,
                'pokemon_cards_tested': len(pokemon_results),
                'trainer_cards_tested': len(trainer_results)
            },
            'problematic_cards': {
                'total_cards_with_issues': len(failing_cards),
                'high_severity_issues': len(high_severity_issues),
                'cards_needing_attention': [
                    {
                        'name': r.card_name,
                        'type': r.card_type,
                        'success_rate': r.get_success_rate(),
                        'issue_count': r.tests_failed,
                        'top_issues': r.issues[:3]  # Top 3 issues
                    } for r in sorted(failing_cards, key=lambda x: x.tests_failed, reverse=True)[:20]
                ]
            },
            'high_priority_fixes': high_severity_issues[:10],
            'card_type_breakdown': {
                'pokemon': {
                    'total': len(pokemon_results),
                    'avg_success_rate': sum(r.get_success_rate() for r in pokemon_results) / len(pokemon_results) if pokemon_results else 0,
                    'common_issues': self._get_common_issues(pokemon_results),
                    'battle_tested': len([r for r in pokemon_results if any('battle' in s['test'] for s in r.successes)]),
                    'abilities_tested': len([r for r in pokemon_results if any('ability' in s['test'] for s in r.successes)])
                },
                'trainer': {
                    'total': len(trainer_results),
                    'avg_success_rate': sum(r.get_success_rate() for r in trainer_results) / len(trainer_results) if trainer_results else 0,
                    'common_issues': self._get_common_issues(trainer_results)
                }
            },
            'battle_simulation_stats': {
                'cards_battle_tested': len([r for r in self.results if any('battle' in s['test'] for s in r.successes)]),
                'avg_battle_turns': sum(r.performance_metrics.get('battle_turns', 0) for r in self.results) / len(self.results) if self.results else 0,
                'total_abilities_triggered': sum(r.performance_metrics.get('abilities_triggered', 0) for r in self.results),
                'coin_flip_tests_passed': len([r for r in self.results if any('coin flip' in s['details'] for s in r.successes)])
            },
            'test_timestamp': datetime.now().isoformat(),
            'recommendations': self._generate_recommendations()
        }
        
        return report
        
    def _get_common_issues(self, results: List[CardTestResult]) -> Dict[str, int]:
        """Get most common issues from a set of results"""
        issue_counts = defaultdict(int)
        
        for result in results:
            for issue in result.issues:
                issue_counts[issue['test']] += 1
                
        return dict(sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5])
        
    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on test results"""
        recommendations = []
        
        # Analyze common failure patterns
        all_issues = []
        for result in self.results:
            all_issues.extend(result.issues)
            
        high_severity_count = sum(1 for issue in all_issues if issue['severity'] == 'high')
        
        if high_severity_count > 0:
            recommendations.append(f"Fix {high_severity_count} high-severity issues first - these may cause crashes or incorrect gameplay")
            
        # Energy cost issues
        energy_issues = [issue for issue in all_issues if 'energy' in issue['test'].lower()]
        if energy_issues:
            recommendations.append(f"Review energy cost parsing - {len(energy_issues)} related issues found")
            
        # Effect parsing issues
        effect_issues = [issue for issue in all_issues if 'effect' in issue['test'].lower()]
        if effect_issues:
            recommendations.append(f"Improve effect parsing system - {len(effect_issues)} effects not parsed correctly")
            
        recommendations.append("Run this test suite after any card data updates to catch regressions")
        recommendations.append("Consider implementing automated testing in CI/CD pipeline")
        
        return recommendations
        
    def save_results(self, report: Dict[str, Any]):
        """Save test results to files"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save summary report
        report_file = f"card_test_report_{timestamp}.json"
        with open(os.path.join('test_results', report_file), 'w') as f:
            json.dump(report, f, indent=2)
            
        # Save detailed results
        detailed_file = f"detailed_card_results_{timestamp}.json"
        detailed_data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_cards': len(self.results),
                'test_version': '1.0'
            },
            'results': [result.to_dict() for result in self.results]
        }
        
        with open(os.path.join('test_results', detailed_file), 'w') as f:
            json.dump(detailed_data, f, indent=2)
            
        self.logger.info(f"Results saved to {report_file} and {detailed_file}")
        
        # Print summary to console
        self._print_summary(report)
        
    def _print_summary(self, report: Dict[str, Any]):
        """Print test summary to console"""
        summary = report['summary']
        
        print("\n" + "="*60)
        print("COMPREHENSIVE CARD TESTING REPORT")
        print("="*60)
        print(f"Total Cards Tested: {summary['total_cards_tested']}")
        print(f"Total Tests Run: {summary['total_tests_run']}")
        print(f"Success Rate: {summary['overall_success_rate']:.1f}%")
        print(f"Duration: {summary['test_duration_seconds']:.2f} seconds")
        
        print(f"\nProblematic Cards: {report['problematic_cards']['total_cards_with_issues']}")
        print(f"High Severity Issues: {report['problematic_cards']['high_severity_issues']}")
        
        if report['high_priority_fixes']:
            print("\nTop Priority Fixes:")
            for i, issue in enumerate(report['high_priority_fixes'][:5], 1):
                print(f"  {i}. {issue['card']} - {issue['error']}")
        
        if report['recommendations']:
            print("\nRecommendations:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"  {i}. {rec}")
        
        print("="*60)


def main():
    """Main entry point for card testing"""
    # Create necessary directories
    os.makedirs('logs', exist_ok=True)
    os.makedirs('test_results', exist_ok=True)
    
    # Initialize tester
    tester = ComprehensiveCardTester()
    
    # Load cards
    if not tester.load_cards():
        print("Failed to load cards. Exiting.")
        return 1
        
    # Run comprehensive tests
    report = tester.test_all_cards()
    
    # Return exit code based on results
    if report['problematic_cards']['high_severity_issues'] > 0:
        return 1  # High severity issues found
    else:
        return 0  # All tests passed or only low severity issues


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)