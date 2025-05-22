import random
from typing import List, Optional, Dict, Tuple, Any
from Card import Card
from Deck import Deck

class EnergyType:
    """Energy type constants used in Pokémon TCG Pocket."""
    FIRE = "R"
    WATER = "W" 
    GRASS = "G"
    LIGHTNING = "L"
    PSYCHIC = "P"
    FIGHTING = "F"
    DARKNESS = "D"
    METAL = "M"
    COLORLESS = "C"

# Map from deck type names to energy symbols
TYPE_TO_ENERGY = {
    "Fire": EnergyType.FIRE,
    "Water": EnergyType.WATER,
    "Grass": EnergyType.GRASS,
    "Lightning": EnergyType.LIGHTNING,
    "Psychic": EnergyType.PSYCHIC,
    "Fighting": EnergyType.FIGHTING,
    "Darkness": EnergyType.DARKNESS,
    "Metal": EnergyType.METAL,
}

class PokemonState:
    """Represents the state of a Pokémon in play."""
    
    def __init__(self, card: Card):
        self.card = card
        self.damage = 0
        self.energies = []  # List of energy symbols attached
        self.status = None  # Status condition (Asleep, Paralyzed, etc.)
        
    @property
    def hp_remaining(self):
        """Calculate remaining HP after damage."""
        return (self.card.hp or 0) - self.damage
    
    @property
    def is_knocked_out(self):
        """Check if Pokémon is knocked out."""
        return self.hp_remaining <= 0
    
    def attach_energy(self, energy_type: str) -> bool:
        """Attach energy to this Pokémon."""
        self.energies.append(energy_type)
        return True
    
    def has_enough_energy(self, attack_index: int) -> bool:
        """Check if Pokémon has enough energy for an attack."""
        if not self.card.attacks or attack_index >= len(self.card.attacks):
            return False
            
        attack = self.card.attacks[attack_index]
        energy_cost = attack.get("cost", [])
        
        # Count available energies by type
        available_energies = {}
        for energy in self.energies:
            available_energies[energy] = available_energies.get(energy, 0) + 1
        
        # Copy for calculation
        temp_energies = available_energies.copy()
        
        # Check if requirements can be met
        for needed_energy in energy_cost:
            if needed_energy == "C":  # Colorless can be any type
                total_energy = sum(temp_energies.values())
                if total_energy <= 0:
                    return False
                
                # Use any energy for colorless (prefer non-specific types first)
                energy_found = False
                for e_type in temp_energies:
                    if temp_energies[e_type] > 0:
                        temp_energies[e_type] -= 1
                        energy_found = True
                        break
                        
                if not energy_found:
                    return False
            elif needed_energy in temp_energies and temp_energies[needed_energy] > 0:
                temp_energies[needed_energy] -= 1
            else:
                return False
        
        return True

class Player:
    """Represents a player in the Pokémon TCG Pocket game."""
    
    def __init__(self, name: str, deck: Deck):
        self.name = name
        self.deck_cards = deck.cards.copy()  # Copy to avoid modifying original
        self.deck_types = deck.deck_types
        self.hand = []
        self.active_pokemon = None  # PokemonState
        self.bench = []  # List of PokemonState, max 5
        self.prizes = []  # 3 in Pocket
        self.discard_pile = []
        self.supporter_played_this_turn = False
        self.retreat_used_this_turn = False
        self.energy_attached_this_turn = False
        
        # Energy Zone
        self.current_energy = None  # Energy available this turn
        self.next_energy = None     # Preview of next turn's energy
    
    def can_play(self) -> bool:
        """Check if player can continue playing (has Pokémon in play)."""
        return self.active_pokemon is not None or len(self.bench) > 0
    
    def setup(self):
        """Initial setup - shuffle deck, draw 5 cards, set 3 prize cards."""
        random.shuffle(self.deck_cards)
        
        # Set prize cards
        self.prizes = self.deck_cards[:3]
        self.deck_cards = self.deck_cards[3:]
        
        # Draw initial hand
        self.draw_cards(5)
        
        # Initialize Energy Zone with first energy type
        self.generate_energy()
    
    def draw_cards(self, count: int = 1) -> bool:
        """Draw specified number of cards. Return False if deck is empty."""
        for _ in range(count):
            if not self.deck_cards:
                return False  # Deck out
            self.hand.append(self.deck_cards.pop(0))
        return True
    
    def has_basic_pokemon(self) -> bool:
        """Check if player has at least one basic Pokémon in hand."""
        return any(card.is_pokemon and card.is_basic for card in self.hand)
    
    def generate_energy(self) -> str:
        """Generate energy for the turn from Energy Zone."""
        # Move next energy to current
        self.current_energy = self.next_energy
        
        # Generate new next energy
        if self.deck_types:
            # Pick a random energy type from deck types
            deck_type = random.choice(self.deck_types)
            self.next_energy = TYPE_TO_ENERGY.get(deck_type, EnergyType.COLORLESS)
        else:
            # Default to colorless if no deck types specified
            self.next_energy = EnergyType.COLORLESS
            
        return self.current_energy
    
    def set_active_pokemon(self, card_index: int) -> bool:
        """Set active Pokémon from hand."""
        if self.active_pokemon is not None:
            return False  # Already have an active Pokémon
            
        if 0 <= card_index < len(self.hand):
            card = self.hand[card_index]
            if card.is_pokemon and card.is_basic:
                self.active_pokemon = PokemonState(card)
                self.hand.pop(card_index)
                return True
        return False
    
    def add_to_bench(self, card_index: int) -> bool:
        """Add a basic Pokémon from hand to bench."""
        if len(self.bench) >= 5:
            return False  # Bench is full
            
        if 0 <= card_index < len(self.hand):
            card = self.hand[card_index]
            if card.is_pokemon and card.is_basic:
                self.bench.append(PokemonState(card))
                self.hand.pop(card_index)
                return True
        return False
    
    def attach_energy(self, pokemon_location: str, pokemon_index: int = 0) -> bool:
        """Attach current energy to a Pokémon."""
        if self.current_energy is None or self.energy_attached_this_turn:
            return False
            
        target = None
        if pokemon_location == "active" and self.active_pokemon is not None:
            target = self.active_pokemon
        elif pokemon_location == "bench" and 0 <= pokemon_index < len(self.bench):
            target = self.bench[pokemon_index]
            
        if target:
            target.attach_energy(self.current_energy)
            self.current_energy = None
            self.energy_attached_this_turn = True
            return True
        return False
    
    def play_trainer(self, card_index: int) -> bool:
        """Play a trainer card from hand."""
        if 0 <= card_index < len(self.hand):
            card = self.hand[card_index]
            if card.is_trainer:
                # Check if it's a supporter and if one has already been played
                if card.trainer_subtype == "Supporter" and self.supporter_played_this_turn:
                    return False
                
                # Apply trainer card effect (this would be more complex in practice)
                # ...
                
                # Move to discard pile
                self.discard_pile.append(card)
                self.hand.pop(card_index)
                
                # Mark supporter as played if applicable
                if card.trainer_subtype == "Supporter":
                    self.supporter_played_this_turn = True
                
                return True
        return False
    
    def evolve_pokemon(self, card_index: int, target_location: str, target_index: int = 0) -> bool:
        """Evolve a Pokémon in play."""
        if 0 <= card_index < len(self.hand):
            card = self.hand[card_index]
            
            # Check if card is an evolution card
            if not (card.is_pokemon and card.is_evolution):
                return False
                
            # Find target Pokémon to evolve
            target = None
            if target_location == "active" and self.active_pokemon is not None:
                target = self.active_pokemon
            elif target_location == "bench" and 0 <= target_index < len(self.bench):
                target = self.bench[target_index]
                
            if target and card.evolves_from == target.card.name:
                # Save energies from pre-evolution
                energies = target.energies
                
                # Evolve the Pokémon
                if target_location == "active":
                    self.active_pokemon = PokemonState(card)
                    self.active_pokemon.energies = energies
                else:
                    self.bench[target_index] = PokemonState(card)
                    self.bench[target_index].energies = energies
                    
                # Move pre-evolution to discard
                self.discard_pile.append(target.card)
                
                # Remove evolution card from hand
                self.hand.pop(card_index)
                return True
        return False
    
    def retreat_pokemon(self, bench_index: int) -> bool:
        """Retreat active Pokémon to bench and bring up a benched Pokémon."""
        if self.retreat_used_this_turn:
            return False
            
        if self.active_pokemon is None or len(self.bench) == 0:
            return False
            
        if 0 <= bench_index < len(self.bench):
            # Check if retreat cost can be paid
            retreat_cost = self.active_pokemon.card.retreat_cost or 0
            if len(self.active_pokemon.energies) < retreat_cost:
                return False
                
            # Swap Pokémon
            new_active = self.bench.pop(bench_index)
            self.bench.append(self.active_pokemon)
            self.active_pokemon = new_active
            
            # Discard energy for retreat cost (in practice, player would choose which ones)
            for _ in range(retreat_cost):
                if self.active_pokemon.energies:
                    self.active_pokemon.energies.pop(0)
            
            self.retreat_used_this_turn = True
            return True
        return False
    
    def can_attack(self) -> bool:
        """Check if active Pokémon can use any attack."""
        if not self.active_pokemon or not self.active_pokemon.card.attacks:
            return False
            
        # Check if any attack's energy requirements can be met
        for i in range(len(self.active_pokemon.card.attacks)):
            if self.active_pokemon.has_enough_energy(i):
                return True
                
        return False
    
    def use_attack(self, attack_index: int, opponent) -> Dict:
        """Use an attack from active Pokémon against opponent."""
        if not self.active_pokemon or not self.can_attack():
            return {"success": False, "message": "Cannot attack"}
            
        if attack_index >= len(self.active_pokemon.card.attacks):
            return {"success": False, "message": "Invalid attack index"}
        
        if not self.active_pokemon.has_enough_energy(attack_index):
            return {"success": False, "message": "Not enough energy for this attack"}
            
        attack = self.active_pokemon.card.attacks[attack_index]
        
        # Calculate damage
        base_damage = 0
        damage_str = attack.get("damage", "0")
        if "+" in damage_str:
            base_damage = int(damage_str.split("+")[0])
            # Handle "+" effects in a more complex implementation
        elif "×" in damage_str:
            base_damage = int(damage_str.split("×")[0])
            # Handle "×" effects in a more complex implementation
        else:
            try:
                base_damage = int(damage_str)
            except ValueError:
                base_damage = 0
        
        damage = base_damage
        
        # Apply weakness if applicable
        if opponent.active_pokemon:
            weakness = opponent.active_pokemon.card.weakness
            if weakness:
                # Extract the type from our active Pokémon
                pokemon_types = []
                for cost in attack.get("cost", []):
                    if cost != "C":  # Skip colorless
                        pokemon_types.append(cost)
                
                # If attack uses energy matching weakness, double damage
                if any(energy == weakness for energy in pokemon_types):
                    damage *= 2
        
        # Apply damage to opponent's active Pokémon
        if opponent.active_pokemon:
            opponent.active_pokemon.damage += damage
            
            # Check if Pokémon is knocked out
            if opponent.active_pokemon.is_knocked_out:
                knocked_out = opponent.active_pokemon
                opponent.discard_pile.append(knocked_out.card)
                opponent.active_pokemon = None
                
                # Take prize card(s)
                prize_count = 2 if "ex" in knocked_out.card.card_type.lower() else 1
                for _ in range(min(prize_count, len(self.prizes))):
                    if self.prizes:
                        prize = self.prizes.pop(0)
                        self.hand.append(prize)
                
                # Opponent must select new active Pokémon if available
                if opponent.bench:
                    # In a real game, opponent would choose; here we select the first one
                    opponent.active_pokemon = opponent.bench.pop(0)
        
        return {
            "success": True, 
            "damage": damage,
            "effect": attack.get("effect", "")
        }
    
    def reset_turn_flags(self):
        """Reset flags that track per-turn actions."""
        self.supporter_played_this_turn = False
        self.retreat_used_this_turn = False
        self.energy_attached_this_turn = False

class BattleEngine:
    """Simulates Pokémon TCG Pocket battles between two decks."""
    
    def __init__(self, deck1: Deck, deck2: Deck):
        self.player1 = Player("Player 1", deck1)
        self.player2 = Player("Player 2", deck2)
        self.current_player = None
        self.non_current_player = None
        self.turn_count = 0
        self.first_turn = True
        self.game_over = False
        self.winner = None
        self.log = []  # Battle log
        
    def add_log(self, message: str):
        """Add a message to the battle log."""
        self.log.append(message)
        print(message)  # Also print to console
        
    def initialize_game(self):
        """Set up the game - shuffle decks, draw hands, ensure Basic Pokémon."""
        # Initial setup for both players
        self.player1.setup()
        self.player2.setup()
        
        # Ensure player 1 has a Basic Pokémon
        if not self.player1.has_basic_pokemon():
            self.add_log(f"{self.player1.name} has no Basic Pokémon! Adding one to hand.")
            # Find a Basic Pokémon in the deck
            basic_indices = [i for i, card in enumerate(self.player1.deck_cards) 
                             if card.is_pokemon and card.is_basic]
            if basic_indices:
                # Add a random Basic Pokémon to hand
                basic_index = random.choice(basic_indices)
                basic_pokemon = self.player1.deck_cards.pop(basic_index)
                self.player1.hand.append(basic_pokemon)
            else:
                self.add_log(f"ERROR: {self.player1.name}'s deck contains no Basic Pokémon!")
        
        # Ensure player 2 has a Basic Pokémon
        if not self.player2.has_basic_pokemon():
            self.add_log(f"{self.player2.name} has no Basic Pokémon! Adding one to hand.")
            # Find a Basic Pokémon in the deck
            basic_indices = [i for i, card in enumerate(self.player2.deck_cards) 
                             if card.is_pokemon and card.is_basic]
            if basic_indices:
                # Add a random Basic Pokémon to hand
                basic_index = random.choice(basic_indices)
                basic_pokemon = self.player2.deck_cards.pop(basic_index)
                self.player2.hand.append(basic_pokemon)
            else:
                self.add_log(f"ERROR: {self.player2.name}'s deck contains no Basic Pokémon!")
        
        # Coin flip to determine first player
        if random.choice([True, False]):
            self.current_player = self.player1
            self.non_current_player = self.player2
            self.add_log(f"Coin flip result: {self.player1.name} goes first!")
        else:
            self.current_player = self.player2
            self.non_current_player = self.player1
            self.add_log(f"Coin flip result: {self.player2.name} goes first!")
            
        # Both players set up their active Pokémon and bench
        # In a real game, this would involve player choice
        self._setup_initial_pokemon(self.player1)
        self._setup_initial_pokemon(self.player2)
            
        return {
            "first_player": self.current_player.name,
            "player1_active": self.player1.active_pokemon.card.name if self.player1.active_pokemon else None,
            "player2_active": self.player2.active_pokemon.card.name if self.player2.active_pokemon else None
        }
    
    def _setup_initial_pokemon(self, player: Player):
        """Set up initial active and bench Pokémon for a player."""
        # Find all Basic Pokémon in hand
        basic_pokemon_indices = [i for i, card in enumerate(player.hand) 
                               if card.is_pokemon and card.is_basic]
        
        if not basic_pokemon_indices:
            self.add_log(f"{player.name} has no Basic Pokémon to play! Something went wrong!")
            return
            
        # Choose first one as active (in a real game, player would choose)
        player.set_active_pokemon(basic_pokemon_indices[0])
        self.add_log(f"{player.name} places {player.active_pokemon.card.name} as the Active Pokémon")
        
        # Update indices after removing the active Pokémon
        basic_pokemon_indices = [i for i, card in enumerate(player.hand) 
                               if card.is_pokemon and card.is_basic]
        
        # Place remaining Basic Pokémon on bench (up to 5)
        for i in basic_pokemon_indices[:5]:  # Only first 5 if more
            if player.add_to_bench(i):
                self.add_log(f"{player.name} places {player.bench[-1].card.name} on the bench")
            else:
                break  # Bench is full
    
    def start_turn(self):
        """Handle start-of-turn actions."""
        player = self.current_player
        
        # Reset turn-based flags
        player.reset_turn_flags()
        
        # Draw card (first player also draws on first turn in TCG Pocket)
        if not player.draw_cards(1):
            # Player decked out
            self.game_over = True
            self.winner = self.non_current_player
            self.add_log(f"{player.name} could not draw a card and lost the game!")
            return {"success": False, "message": f"{player.name} decked out"}
        else:
            self.add_log(f"{player.name} draws a card")
        
        # Generate energy (except first player's first turn)
        if not (self.first_turn and player == self.player1):
            energy = player.generate_energy()
            energy_name = next((name for name, value in TYPE_TO_ENERGY.items() 
                               if value == energy), "Colorless")
            self.add_log(f"{player.name} receives {energy_name} energy from the Energy Zone")
        else:
            self.add_log(f"{player.name} doesn't receive energy on the first turn")
            
        return {"success": True}
    
    def end_turn(self):
        """Handle end-of-turn actions and switch current player."""
        # Check win conditions
        if len(self.player1.prizes) == 0:
            self.game_over = True
            self.winner = self.player1
            self.add_log(f"{self.player1.name} won by taking all prize cards!")
            return {"success": False, "message": f"{self.player1.name} won by taking all prize cards"}
            
        if len(self.player2.prizes) == 0:
            self.game_over = True
            self.winner = self.player2
            self.add_log(f"{self.player2.name} won by taking all prize cards!")
            return {"success": False, "message": f"{self.player2.name} won by taking all prize cards"}
            
        if not self.player1.can_play():
            self.game_over = True
            self.winner = self.player2
            self.add_log(f"{self.player1.name} has no Pokémon in play and lost the game!")
            return {"success": False, "message": f"{self.player1.name} has no Pokémon in play"}
            
        if not self.player2.can_play():
            self.game_over = True
            self.winner = self.player1
            self.add_log(f"{self.player2.name} has no Pokémon in play and lost the game!")
            return {"success": False, "message": f"{self.player2.name} has no Pokémon in play"}
        
        # Switch current player
        self.current_player, self.non_current_player = self.non_current_player, self.current_player
        
        # Track turns
        self.turn_count += 1
        if self.turn_count >= 2:
            self.first_turn = False
            
        return {"success": True}
    
    def simulate_game(self, ai_player1=None, ai_player2=None, max_turns=100):
        """Simulate a complete game using provided AI for decisions."""
        result = self.initialize_game()
        self.add_log(f"Game initialized. {result['first_player']} goes first.")
        
        while not self.game_over and self.turn_count < max_turns:
            self.add_log(f"\n--- Turn {self.turn_count + 1}: {self.current_player.name} ---")
            
            # Start turn
            start_result = self.start_turn()
            if not start_result["success"]:
                self.add_log(start_result["message"])
                break
                
            # AI makes decisions here (play cards, attach energy, attack, etc.)
            # This is placeholder for actual AI implementation
            if self.current_player == self.player1 and ai_player1:
                ai_player1.take_turn(self)
            elif self.current_player == self.player2 and ai_player2:
                ai_player2.take_turn(self)
            else:
                # Default simple behavior if no AI provided
                self._simple_ai_turn()
                
            # End turn
            end_result = self.end_turn()
            if not end_result["success"]:
                self.add_log(end_result["message"])
                break
        
        if self.turn_count >= max_turns:
            self.add_log("Game ended due to maximum turn count")
            # Determine winner based on remaining prize cards
            if len(self.player1.prizes) < len(self.player2.prizes):
                self.winner = self.player1
                self.add_log(f"{self.player1.name} won with fewer prize cards remaining!")
            elif len(self.player2.prizes) < len(self.player1.prizes):
                self.winner = self.player2
                self.add_log(f"{self.player2.name} won with fewer prize cards remaining!")
            else:
                self.add_log("Game ended in a tie!")
                return {"winner": None, "turns": self.turn_count, "log": self.log}
                
        return {
            "winner": self.winner.name if self.winner else None,
            "turns": self.turn_count,
            "player1_prizes_left": len(self.player1.prizes),
            "player2_prizes_left": len(self.player2.prizes),
            "log": self.log
        }
    
    def _simple_ai_turn(self):
        """Simple AI behavior for demonstration purposes."""
        player = self.current_player
        opponent = self.non_current_player
        
        # Play a Basic Pokémon as active if needed
        if player.active_pokemon is None:
            for i, card in enumerate(player.hand):
                if card.is_pokemon and card.is_basic:
                    if player.set_active_pokemon(i):
                        self.add_log(f"{player.name} plays {card.name} as the active Pokémon")
                        break
        
        # Play Basic Pokémon to bench
        basic_indices = [i for i, card in enumerate(player.hand) 
                       if card.is_pokemon and card.is_basic]
        for i in basic_indices:
            if player.add_to_bench(i):
                self.add_log(f"{player.name} adds {player.bench[-1].card.name} to bench")
                if len(player.bench) >= 5:
                    break
                # Update indices since hand has changed
                basic_indices = [j for j, card in enumerate(player.hand) 
                              if card.is_pokemon and card.is_basic]
        
        # Evolve Pokémon if possible
        evolution_indices = [i for i, card in enumerate(player.hand) 
                          if card.is_pokemon and card.is_evolution]
        for i in evolution_indices:
            evolution_card = player.hand[i]
            # Check active first
            if (player.active_pokemon and 
                evolution_card.evolves_from == player.active_pokemon.card.name):
                if player.evolve_pokemon(i, "active"):
                    self.add_log(f"{player.name} evolves active {player.active_pokemon.card.name}")
                    # Update indices since hand has changed
                    evolution_indices = [j for j, card in enumerate(player.hand) 
                                      if card.is_pokemon and card.is_evolution]
                    continue
                    
            # Then check bench
            for j, benched in enumerate(player.bench):
                if evolution_card.evolves_from == benched.card.name:
                    if player.evolve_pokemon(i, "bench", j):
                        self.add_log(f"{player.name} evolves benched {player.bench[j].card.name}")
                        # Update indices since hand has changed
                        evolution_indices = [k for k, card in enumerate(player.hand) 
                                          if card.is_pokemon and card.is_evolution]
                        break
        
        # Attach energy if available
        if not player.energy_attached_this_turn and player.current_energy is not None:
            if player.active_pokemon is not None:
                if player.attach_energy("active"):
                    energy_name = next((name for name, value in TYPE_TO_ENERGY.items() 
                                     if value == player.current_energy), "Colorless")
                    self.add_log(f"{player.name} attaches {energy_name} energy to active Pokémon")
            elif player.bench:
                if player.attach_energy("bench", 0):
                    energy_name = next((name for name, value in TYPE_TO_ENERGY.items() 
                                     if value == player.current_energy), "Colorless")
                    self.add_log(f"{player.name} attaches {energy_name} energy to benched Pokémon")
        
        # Play a Trainer card if available
        trainer_indices = [i for i, card in enumerate(player.hand) if card.is_trainer]
        for i in trainer_indices:
            trainer_card = player.hand[i]
            if player.play_trainer(i):
                self.add_log(f"{player.name} plays {trainer_card.name} trainer card")
                # Update indices since hand has changed
                trainer_indices = [j for j, card in enumerate(player.hand) if card.is_trainer]
                if trainer_card.trainer_subtype == "Supporter":
                    break  # Only one Supporter per turn
        
        # Attack if possible
        if player.active_pokemon and opponent.active_pokemon and player.can_attack():
            # Find best attack (most damage)
            best_attack = 0
            best_damage = 0
            for i, attack in enumerate(player.active_pokemon.card.attacks):
                if player.active_pokemon.has_enough_energy(i):
                    damage_str = attack.get("damage", "0")
                    try:
                        damage = int(damage_str.split("+")[0].split("×")[0])
                    except ValueError:
                        damage = 0
                    if damage > best_damage:
                        best_attack = i
                        best_damage = damage
            
            attack_result = player.use_attack(best_attack, opponent)
            if attack_result["success"]:
                attack_name = player.active_pokemon.card.attacks[best_attack].get("name", "Unknown")
                self.add_log(f"{player.name} uses {attack_name} for {attack_result['damage']} damage")

# Simple implementation of a rule-based AI
class SimpleAI:
    """A simple rule-based AI for playing Pokémon TCG Pocket."""
    
    def __init__(self, name: str):
        self.name = name
    
    def take_turn(self, battle: BattleEngine):
        """Execute a turn in the battle."""
        # This will use the simple AI logic already in the BattleEngine
        battle._simple_ai_turn()

# Usage example
def test_battle_with_random_decks():
    from Deck import Deck
    
    # Create two random decks
    from Card import CardCollection
    collection = CardCollection()
    collection.load_from_db()
    
    deck1 = Deck.generate_random_deck(collection, "Random Deck 1")
    deck2 = Deck.generate_random_deck(collection, "Random Deck 2")
    
    # Create AIs
    ai1 = SimpleAI("AI 1")
    ai2 = SimpleAI("AI 2")
    
    # Create and run battle
    battle = BattleEngine(deck1, deck2)
    result = battle.simulate_game(ai1, ai2, max_turns=50)
    
    print("\n--- Battle Summary ---")
    print(f"Winner: {result['winner']}")
    print(f"Total turns: {result['turns']}")
    print(f"Player 1 prizes left: {result['player1_prizes_left']}")
    print(f"Player 2 prizes left: {result['player2_prizes_left']}")
    
    return result

if __name__ == "__main__":
    test_battle_with_random_decks()