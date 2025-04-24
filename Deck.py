from typing import Dict, List, Optional, Set, Tuple
import json
from Card import Card, CardCollection

class Deck:
    """A class representing a Pokemon TCG Pocket deck."""
    
    # Deck building constants
    MAX_CARDS = 20
    MAX_COPIES = 2  # Maximum number of cards with the same name
    
    def __init__(self, name: str = "New Deck", deck_types: List[str] = None, cover_card: Optional[Card] = None):
        """Initialize an empty deck."""
        self.name = name
        self.deck_types = deck_types or []  # e.g., ["Fire", "Fighting"]
        self.cards: List[Card] = []
        self.card_counts: Dict[str, int] = {}  # Keep track of how many of each card by name
        self.cover_card = cover_card  # Store a cover card for visual representation

    def set_cover_card(self, card: Card) -> None:
        """Set a card as the cover card for this deck."""
        self.cover_card = card
    
    def get_cover_card(self) -> Optional[Card]:
        """Get the current cover card of the deck."""
        return self.cover_card
    
    def select_cover_card_automatically(self) -> Optional[Card]:
        """Automatically select a cover card from the deck (preferably a Pokémon)."""
        # First, try to find a Pokémon card
        for card in self.cards:
            if card.is_pokemon:
                self.cover_card = card
                return card
        
        # If no Pokémon, use the first card
        if self.cards:
            self.cover_card = self.cards[0]
            return self.cards[0]
        
        return None
    
    def add_card(self, card: Card) -> bool:
        """
        Add a card to the deck if it doesn't violate deck building rules.
        Returns True if the card was added, False otherwise.
        """
        # Check if deck is already full
        if len(self.cards) >= self.MAX_CARDS:
            print(f"Cannot add {card.name}. Deck is already at maximum capacity ({self.MAX_CARDS} cards).")
            return False
        
        # Check if we already have maximum copies of this card
        if self.card_counts.get(card.name, 0) >= self.MAX_COPIES:
            print(f"Cannot add {card.name}. Maximum number of copies ({self.MAX_COPIES}) already in deck.")
            return False
        
        # Add the card
        self.cards.append(card)
        self.card_counts[card.name] = self.card_counts.get(card.name, 0) + 1
        return True
    
    def remove_card(self, card: Card) -> bool:
        """
        Remove a specific card instance from the deck.
        Returns True if the card was removed, False if it wasn't in the deck.
        """
        for i, deck_card in enumerate(self.cards):
            if deck_card.id == card.id:
                # Remove the card
                del self.cards[i]
                self.card_counts[card.name] -= 1
                if self.card_counts[card.name] == 0:
                    del self.card_counts[card.name]
                return True
        return False
    
    def remove_card_by_name(self, card_name: str) -> bool:
        """
        Remove the first instance of a card with the given name.
        Returns True if a card was removed, False if no matching card was found.
        """
        for card in self.cards:
            if card.name == card_name:
                return self.remove_card(card)
        return False
    
    def clear(self) -> None:
        """Remove all cards from the deck."""
        self.cards = []
        self.card_counts = {}
    
    def is_valid(self) -> Tuple[bool, str]:
        """
        Check if the deck is valid according to Pokemon TCG Pocket rules.
        Returns a tuple: (is_valid, reason_if_invalid)
        """
        if len(self.cards) != self.MAX_CARDS:
            return False, f"Deck must contain exactly {self.MAX_CARDS} cards. Current count: {len(self.cards)}"
        
        for name, count in self.card_counts.items():
            if count > self.MAX_COPIES:
                return False, f"Cannot have more than {self.MAX_COPIES} copies of {name}. Current count: {count}"
        
        # Check if the deck has at least one Basic Pokemon
        basic_pokemon = [card for card in self.cards if card.is_pokemon and card.is_basic]
        if not basic_pokemon:
            return False, "Deck must contain at least one Basic Pokémon."
        
        return True, ""
    
    def get_pokemon_count(self) -> int:
        """Get the number of Pokemon cards in the deck."""
        return sum(1 for card in self.cards if card.is_pokemon)
    
    def get_trainer_count(self) -> int:
        """Get the number of Trainer cards in the deck."""
        return sum(1 for card in self.cards if card.is_trainer)
    
    def set_deck_types(self, types: List[str]) -> None:
        """Set the deck types (e.g., ["Fire", "Fighting"])."""
        self.deck_types = types
    
    def determine_deck_types(self) -> List[str]:
        """
        Determine the deck types based on the Pokémon in the deck.
        Returns a list of type names (e.g., ["Fire", "Fighting"]).
        Colorless is not considered a deck type.
        Decks can only be 1-3 types.
        """
        type_count = {}
        
        # Count the types of all Pokémon attacks in the deck
        for card in self.cards:
            if not card.is_pokemon:
                continue
                
            for attack in card.attacks:
                for cost in attack.get("cost", []):
                    # Skip colorless energy as it's not a deck type
                    if cost == "C":
                        continue
                        
                    # Map energy symbols to type names
                    type_name = self._energy_to_type(cost)
                    if type_name:
                        type_count[type_name] = type_count.get(type_name, 0) + 1
        
        # If no specific energy types found, default to a random type
        if not type_count:
            import random
            valid_types = ["Fire", "Water", "Grass", "Lightning", "Psychic", "Fighting", "Darkness", "Metal"]
            return [random.choice(valid_types)]
            
        # Sort types by frequency
        sorted_types = sorted(type_count.items(), key=lambda x: x[1], reverse=True)
        
        # Take top 3 types maximum
        result = [t[0] for t in sorted_types[:3]]
            
        return result
    
    def _energy_to_type(self, energy_symbol: str) -> Optional[str]:
        """Convert energy symbol to type name."""
        energy_map = {
            "R": "Fire",
            "W": "Water",
            "G": "Grass",
            "L": "Lightning",
            "P": "Psychic",
            "F": "Fighting",
            "D": "Darkness",
            "M": "Metal",
            "C": "Colorless"
        }
        return energy_map.get(energy_symbol)
    
    def get_type_breakdown(self) -> Dict[str, int]:
        """
        Get a breakdown of Pokemon types in the deck.
        This counts the dominant type of each Pokemon based on attack costs.
        """
        type_counts = {}
        
        for card in self.cards:
            if not card.is_pokemon:
                continue
            
            # Check the attacks to determine the dominant type
            energy_types = []
            for attack in card.attacks:
                for cost in attack.get("cost", []):
                    if cost not in energy_types and cost != "C":  # Skip colorless
                        energy_types.append(cost)
            
            if energy_types:
                # Count occurrences of each type
                type_freq = {}
                for energy_type in energy_types:
                    type_freq[energy_type] = type_freq.get(energy_type, 0) + 1
                
                # Find the most frequent type
                dominant_type = max(type_freq.items(), key=lambda x: x[1])[0]
                type_name = self._energy_to_type(dominant_type)
                if type_name:
                    type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        return type_counts
    
    def get_evolution_counts(self) -> Dict[str, int]:
        """Get counts of Basic, Stage 1, and Stage 2 Pokemon."""
        evolution_counts = {
            "Basic": 0,
            "Stage 1": 0,
            "Stage 2": 0
        }
        
        for card in self.cards:
            if not card.is_pokemon:
                continue
            
            stage = card.evolution_stage
            if stage == 0:
                evolution_counts["Basic"] += 1
            elif stage == 1:
                evolution_counts["Stage 1"] += 1
            elif stage == 2:
                evolution_counts["Stage 2"] += 1
        
        return evolution_counts
    
    def get_evolution_lines(self) -> List[List[str]]:
        """
        Identify complete evolution lines in the deck.
        Returns a list of lists, where each inner list contains names of Pokemon in an evolution line.
        """
        evolution_lines = []
        
        # Find all stage 2 Pokemon
        stage_2_pokemon = [card for card in self.cards if card.is_pokemon and card.evolution_stage == 2]
        
        for s2 in stage_2_pokemon:
            if not s2.evolves_from:
                continue
                
            # Find corresponding stage 1
            stage_1_cards = [card for card in self.cards if card.name == s2.evolves_from]
            if not stage_1_cards:
                continue
                
            s1 = stage_1_cards[0]
            if not s1.evolves_from:
                continue
                
            # Find corresponding basic
            basic_cards = [card for card in self.cards if card.name == s1.evolves_from]
            if not basic_cards:
                continue
                
            b = basic_cards[0]
            
            # Complete evolution line found
            evolution_lines.append([b.name, s1.name, s2.name])
        
        # Find Stage 1 + Basic lines
        stage_1_pokemon = [card for card in self.cards if card.is_pokemon and card.evolution_stage == 1]
        
        for s1 in stage_1_pokemon:
            if not s1.evolves_from:
                continue
                
            # Skip if this stage 1 is already part of a complete line
            if any(s1.name in line for line in evolution_lines):
                continue
                
            # Find corresponding basic
            basic_cards = [card for card in self.cards if card.name == s1.evolves_from]
            if not basic_cards:
                continue
                
            b = basic_cards[0]
            
            # Stage 1 + Basic line found
            evolution_lines.append([b.name, s1.name])
        
        return evolution_lines
    
    def save_to_json(self, filename: str) -> None:
        """Save the deck to a JSON file."""
        # Make sure we have a cover card selected
        if not self.cover_card and self.cards:
            self.select_cover_card_automatically()
        
        cover_card_dict = self.cover_card.to_dict() if self.cover_card else None
        
        deck_data = {
            "name": self.name,
            "deck_types": self.deck_types,
            "cards": [card.to_dict() for card in self.cards],
            "cover_card_id": self.cover_card.id if self.cover_card else None
        }
        
        with open(filename, 'w') as f:
            json.dump(deck_data, f, indent=2)
    
    @classmethod
    def load_from_json(cls, filename: str, card_collection: CardCollection) -> 'Deck':
        """Load a deck from a JSON file."""
        with open(filename, 'r') as f:
            deck_data = json.load(f)
        
        deck = cls(
            deck_data.get("name", "Loaded Deck"),
            deck_data.get("deck_types", [])
        )
        
        # Add each card from the saved deck
        for card_data in deck_data.get("cards", []):
            # Try to find the card in the collection
            card = card_collection.get_card(card_data.get("set_code"), card_data.get("card_number"))
            if card:
                deck.add_card(card)
        
        # Set the cover card if specified
        cover_card_id = deck_data.get("cover_card_id")
        if cover_card_id:
            cover_card = card_collection.get_card_by_id(cover_card_id)
            if cover_card:
                deck.set_cover_card(cover_card)
        else:
            # Select a cover card automatically if none was specified
            deck.select_cover_card_automatically()
        
        return deck
    
    @classmethod
    def generate_random_deck(cls, card_collection: CardCollection, deck_name: str = "Random Deck") -> 'Deck':
        """
        Generate a random deck from the available cards in the collection.
        The deck will contain exactly MAX_CARDS with no more than MAX_COPIES of any card.
        Ensures at least one Basic Pokémon is included.
        """
        import random
        
        # Create a new empty deck
        deck = cls(deck_name)
        
        # Get all basic Pokémon to ensure we have at least one
        all_basic_pokemon = [card for card in card_collection.cards if card.is_pokemon and card.is_basic]
        
        if not all_basic_pokemon:
            raise ValueError("Card collection does not contain any Basic Pokémon cards.")
        
        # Add a random Basic Pokémon first to ensure the deck is valid
        basic_pokemon = random.choice(all_basic_pokemon)
        deck.add_card(basic_pokemon)
        
        # Use this first Pokémon as the cover card
        deck.set_cover_card(basic_pokemon)
        
        # Get all Pokémon with non-colorless energy requirements to ensure the deck has at least one energy type
        typed_pokemon = [
            card for card in card_collection.cards 
            if card.is_pokemon and any(
                cost != "C" for attack in card.attacks for cost in attack.get("cost", [])
            )
        ]
        
        if typed_pokemon:
            # Add at least one Pokémon with a specific energy type
            for _ in range(3):  # Try up to 3 times to find a card we can add
                typed_card = random.choice(typed_pokemon)
                if deck.add_card(typed_card):
                    break
        
        # Get all cards that can be added to the deck
        available_cards = [card for card in card_collection.cards]
        random.shuffle(available_cards)  # Randomize the order
        
        # Fill the deck with random cards
        for card in available_cards:
            # Skip if we've reached the maximum deck size
            if len(deck.cards) >= deck.MAX_CARDS:
                break
                
            # Skip if we already have max copies of this card
            if deck.card_counts.get(card.name, 0) >= deck.MAX_COPIES:
                continue
                
            deck.add_card(card)
        
        # Determine the deck types based on the Pokémon types included
        deck_types = deck.determine_deck_types()
        deck.set_deck_types(deck_types)
        
        return deck


    
    
    def __str__(self) -> str:
        """Return a string representation of the deck."""
        valid, reason = self.is_valid()
        status = "Valid" if valid else f"Invalid: {reason}"
        
        pokemon_count = self.get_pokemon_count()
        trainer_count = self.get_trainer_count()
        deck_types = ", ".join(self.deck_types) if self.deck_types else "Unspecified"
        
        return (f"Deck: {self.name}\n"
                f"Types: {deck_types}\n"
                f"Status: {status}\n"
                f"Card count: {len(self.cards)}/{self.MAX_CARDS}\n"
                f"Pokemon: {pokemon_count}\n"
                f"Trainers: {trainer_count}")
    
    def print_deck_list(self) -> None:
        """Print a formatted deck list."""
        deck_types = ", ".join(self.deck_types) if self.deck_types else "Unspecified"
        print(f"=== {self.name} ({deck_types}) ===")
        
        # Group cards by type and count them
        pokemon = []
        trainers = []
        
        for card in self.cards:
            if card.is_pokemon:
                pokemon.append(card)
            elif card.is_trainer:
                trainers.append(card)
        
        # Print Pokemon section
        if pokemon:
            print("\nPokemon ({}/20):".format(len(pokemon)))
            # Group by name and evolution stage
            pokemon_by_name = {}
            for card in pokemon:
                key = card.name
                if key not in pokemon_by_name:
                    pokemon_by_name[key] = []
                pokemon_by_name[key].append(card)
            
            # Sort by evolution stage and name
            for name, cards in sorted(pokemon_by_name.items(), 
                                      key=lambda x: (0 if x[1][0].evolution_stage is None else x[1][0].evolution_stage, x[0])):
                count = len(cards)
                stage = ""
                if cards[0].evolution_stage == 1:
                    stage = " (Stage 1)"
                elif cards[0].evolution_stage == 2:
                    stage = " (Stage 2)"
                print(f"  {count}x {name}{stage}")
        
        # Print Trainers section
        if trainers:
            print("\nTrainers ({}/20):".format(len(trainers)))
            trainer_by_name = {}
            for card in trainers:
                key = card.name
                if key not in trainer_by_name:
                    trainer_by_name[key] = []
                trainer_by_name[key].append(card)
            
            for name, cards in sorted(trainer_by_name.items()):
                count = len(cards)
                subtype = f" ({cards[0].trainer_subtype})" if cards[0].trainer_subtype else ""
                print(f"  {count}x {name}{subtype}")
        
        # Print deck status
        valid, reason = self.is_valid()
        if valid:
            print("\nDeck is valid and ready to play!")
        else:
            print(f"\nDeck is not valid: {reason}")


# Example usage
if __name__ == "__main__":
    from Card import Card, CardCollection
    import random
    
    # Create a collection and load cards
    collection = CardCollection()
    try:
        collection.load_from_db()
        print(f"Loaded {len(collection)} cards from database")
    except Exception as e:
        print(f"Failed to load from database: {e}")
        try:
            collection.load_from_csv()
            print(f"Loaded {len(collection)} cards from CSV")
        except Exception as e:
            print(f"Failed to load from CSV: {e}")
    
    if len(collection) > 0:
        # Generate a random deck
        random_deck = Deck.generate_random_deck(collection, "Random Deck")
        print("\nRandom Deck Generated!")
        
        # Print deck information
        print("\nDeck Information:")
        print(random_deck)
        
        # Print detailed deck list
        print("\nDetailed Deck List:")
        random_deck.print_deck_list()
        
        # Check if the random deck is valid
        valid, reason = random_deck.is_valid()
        if valid:
            print("\nRandom deck is valid!")
        else:
            print(f"\nRandom deck is not valid: {reason}")
        
        # Save the random deck
        random_deck.save_to_json("random_deck.json")
        print("\nRandom deck saved to random_deck.json")
        
        # Example of creating a custom deck
        print("\n\n=== Creating a Custom Deck ===")
        custom_deck = Deck("Custom Deck")
        
        # Add at least one Basic Pokémon
        basic_pokemon = [card for card in collection.cards if card.is_pokemon and card.is_basic]
        if basic_pokemon:
            for i in range(min(5, len(basic_pokemon))):
                card = basic_pokemon[i]
                if custom_deck.add_card(card):
                    print(f"Added {card.name} to custom deck")
        
        # Add some random cards to fill the deck
        all_cards = [card for card in collection.cards]
        random.shuffle(all_cards)
        
        for card in all_cards:
            if len(custom_deck.cards) >= Deck.MAX_CARDS:
                break
            if custom_deck.card_counts.get(card.name, 0) < Deck.MAX_COPIES:
                if custom_deck.add_card(card):
                    print(f"Added {card.name} to custom deck")
        
        # Print custom deck information
        print("\nCustom Deck Information:")
        print(custom_deck)
        
        # Print detailed custom deck list
        print("\nDetailed Custom Deck List:")
        custom_deck.print_deck_list()