from typing import Dict, List, Optional, Set, Tuple
import json
import os  # Import os for directory creation
from Card import Card, CardCollection
import datetime  # Import the datetime module


class Deck:
    """A class representing a Pokemon TCG Pocket deck."""

    # Deck building constants
    MAX_CARDS = 20
    MAX_COPIES = 2  # Maximum number of cards with the same name

    def __init__(
        self,
        name: str = "New Deck",
        deck_types: Optional[
            List[str]
        ] = None,  
        cover_card_ids: Optional[List[str]] = None,
    ):
        self.name = name
        self.deck_types = deck_types if deck_types is not None else []
        self.cards: List[Card] = []
        self.card_counts: Dict[str, int] = {}
        self.cover_card_ids: List[str] = (
            cover_card_ids if cover_card_ids is not None else []
        ) 
        self.owner: Optional[str] = None 

    def get_cover_card_ids(self) -> List[str]:
        """Get the current list of cover card IDs."""
        return self.cover_card_ids

    def add_cover_card_id(self, card_id: str) -> bool:
        """
        Adds a card ID to the cover card list if not full and ID is not already present.
        Returns True if added, False otherwise.
        """
        if card_id not in self.cover_card_ids and len(self.cover_card_ids) < 3:
            self.cover_card_ids.append(card_id)
            return True
        return False

    def remove_cover_card_id(self, card_id: str) -> bool:
        """Removes a card ID from the cover card list. Returns True if removed."""
        if card_id in self.cover_card_ids:
            self.cover_card_ids.remove(card_id)
            return True
        return False

    # --- END NEW/MODIFIED COVER CARD ID METHODS ---

    # In Deck.py

    def set_cover_card_ids(self, card_ids: List[str]) -> None:
        """
        Set the list of cover card IDs, ensuring they are valid, unique,
        and present in the current deck. Max 3.
        """
        if not isinstance(card_ids, list):
            self.cover_card_ids = []
            return

        valid_and_unique_ids_in_order = []
        current_deck_master_ids = {
            str(card.id) for card in self.cards
        }  # Set of string IDs from current deck cards

        for cid_str in card_ids:
            cid_str_clean = str(cid_str).strip()  # Ensure it's a string and clean
            if not cid_str_clean:
                continue

            if (
                cid_str_clean in current_deck_master_ids
                and cid_str_clean not in valid_and_unique_ids_in_order
            ):
                if len(valid_and_unique_ids_in_order) < 3:
                    valid_and_unique_ids_in_order.append(cid_str_clean)

        self.cover_card_ids = valid_and_unique_ids_in_order
        print(f"Set cover_card_ids to: {self.cover_card_ids} after validation.")

    # In Deck.py
    def select_cover_card_automatically(self) -> None:
        print(
            f"Auto-select called for '{self.name}'. Current cover_card_ids: {self.cover_card_ids}"
        )

        if not self.cards:
            self.cover_card_ids = []
            print("Auto-select: No cards in deck, cover_card_ids set to [].")
            return

        final_selected_ids = list(self.cover_card_ids)  # Make a copy to work with

        temp_unique_set = set()
        deduplicated_initial_selection = []
        for cid in final_selected_ids:
            if cid not in temp_unique_set:
                deduplicated_initial_selection.append(cid)
                temp_unique_set.add(cid)
        final_selected_ids = deduplicated_initial_selection[:3]  # Max 3 from user

        if len(final_selected_ids) >= 3:
            self.cover_card_ids = (
                final_selected_ids  # Ensure it's capped at 3 if somehow more came in
            )
            print(
                f"Auto-select: Already have {len(self.cover_card_ids)} cover cards. No changes made by auto-select."
            )
            return

        num_to_add = 3 - len(final_selected_ids)

        # Candidates for auto-selection: cards in the deck NOT already in final_selected_ids
        candidate_cards_for_auto = []
        current_selection_set = set(final_selected_ids)  # IDs already chosen by user

        # Create a list of unique card objects from the deck to pick from
        unique_deck_cards_dict = {}
        for card in self.cards:
            if (
                str(card.id) not in unique_deck_cards_dict
            ):  # Prioritize first instance if duplicates exist in self.cards
                unique_deck_cards_dict[str(card.id)] = card

        potential_candidates = [
            card
            for card_id, card in unique_deck_cards_dict.items()
            if card_id not in current_selection_set
        ]

        if not potential_candidates:
            self.cover_card_ids = final_selected_ids  # Save what we have
            print(
                f"Auto-select: No more distinct candidate cards available. Final IDs: {self.cover_card_ids}"
            )
            return

        # Sort these *available* candidates
        # (Ensure self._auto_select_sort_key and its dependencies are correct)
        sorted_auto_candidates = sorted(
            potential_candidates, key=self._auto_select_sort_key
        )

        for candidate in sorted_auto_candidates:
            if len(final_selected_ids) >= 3:
                break
            final_selected_ids.append(str(candidate.id))  # Add string ID

        self.cover_card_ids = final_selected_ids
        print(
            f"Auto-select: Final cover_card_ids after auto-filling: {self.cover_card_ids}"
        )

    # Helper for the sort key to be part of the class or defined locally
    def _auto_select_sort_key(self, card):
        # You'll need to define or make rarity_map accessible here
        # For simplicity, assuming rarity_map is accessible (e.g., class or global constant)
        rarity_map = {
            "Crown Rare": 0,
            "✵✵": 1,
            "✵": 2,
            "☆☆☆": 3,
            "☆☆": 4,
            "☆": 5,
            "◊◊◊◊": 6,
            "◊◊◊": 7,
            "◊◊": 8,
            "◊": 9,
            "default": 99,
        }
        DEFAULT_RARITY_RANK = 99

        def get_card_rarity_rank(c):
            return rarity_map.get(c.rarity, DEFAULT_RARITY_RANK)

        is_pokemon = "Pokémon" in card.card_type
        is_supporter = "Supporter" in card.card_type
        is_item = "Item" in card.card_type

        category_rank = 5  # Default (other trainers, etc.)
        if is_pokemon:
            category_rank = 0
        elif is_supporter:
            category_rank = 1
        elif is_item:
            category_rank = 2
        # You can add more categories here if needed (e.g., Stadium before generic Trainer)
        elif "Trainer" in card.card_type:
            category_rank = 3  # Other trainers after Item

        rarity_rank_val = get_card_rarity_rank(card)
        return (category_rank, rarity_rank_val, card.name)

    def add_card(self, card: Card) -> bool:
        """
        Add a card to the deck if it doesn't violate deck building rules.
        Returns True if the card was added, False otherwise.
        """
        # Check if deck is already full
        if len(self.cards) >= self.MAX_CARDS:
            print(
                f"Cannot add {card.name}. Deck is already at maximum capacity ({self.MAX_CARDS} cards)."
            )
            return False

        # Check if we already have maximum copies of this card
        if self.card_counts.get(card.name, 0) >= self.MAX_COPIES:
            print(
                f"Cannot add {card.name}. Maximum number of copies ({self.MAX_COPIES}) already in deck."
            )
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
            return (
                False,
                f"Deck must contain exactly {self.MAX_CARDS} cards. Current count: {len(self.cards)}",
            )

        for name, count in self.card_counts.items():
            if count > self.MAX_COPIES:
                return (
                    False,
                    f"Cannot have more than {self.MAX_COPIES} copies of {name}. Current count: {count}",
                )

        # Check if the deck has at least one Basic Pokemon
        basic_pokemon = [
            card for card in self.cards if card.is_pokemon and card.is_basic
        ]
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

            valid_types = [
                "Fire",
                "Water",
                "Grass",
                "Lightning",
                "Psychic",
                "Fighting",
                "Darkness",
                "Metal",
            ]
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
            "C": "Colorless",
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
        evolution_counts = {"Basic": 0, "Stage 1": 0, "Stage 2": 0}

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
        stage_2_pokemon = [
            card for card in self.cards if card.is_pokemon and card.evolution_stage == 2
        ]

        for s2 in stage_2_pokemon:
            if not s2.evolves_from:
                continue

            # Find corresponding stage 1
            stage_1_cards = [
                card for card in self.cards if card.name == s2.evolves_from
            ]
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
        stage_1_pokemon = [
            card for card in self.cards if card.is_pokemon and card.evolution_stage == 1
        ]

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

        # Auto-fill cover cards IF the user hasn't selected 3 AND the deck has cards
        if len(self.cover_card_ids) < 3 and self.cards:
            print(
                f"Deck '{self.name}' has {len(self.cover_card_ids)} user-selected cover cards. Attempting auto-fill."
            )
            self.select_cover_card_automatically()  # This will fill remaining slots up to 3
        elif not self.cards:  # No cards in deck
            self.cover_card_ids = []

        deck_data = {
            "name": self.name,
            "deck_types": self.deck_types,
            "cards": [card.to_dict() for card in self.cards],
            "cover_card_ids": self.cover_card_ids,  # Save the (potentially auto-filled) list
            "owner": self.owner,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            json.dump(deck_data, f, indent=2)

    @classmethod
    def load_from_json(cls, filename: str, card_collection: CardCollection) -> "Deck":
        """Load a deck from a JSON file."""
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Deck file not found: {filename}")

        with open(filename, "r") as f:
            deck_data = json.load(f)

        # Load cover_card_ids, default to empty list if not present
        loaded_cover_card_ids = deck_data.get("cover_card_ids", [])
        if not isinstance(loaded_cover_card_ids, list):  # Ensure it's a list
            loaded_cover_card_ids = []

        deck = cls(
            name=deck_data.get("name", "Loaded Deck"),
            deck_types=deck_data.get("deck_types", []),
            cover_card_ids=loaded_cover_card_ids,  # ++ PASS LOADED IDs ++
        )
        deck.owner = deck_data.get("owner")  # Load owner

        # ... (your existing logic for loading self.cards, respecting MAX_COPIES via deck.add_card) ...
        for card_data in deck_data.get("cards", []):
            card_id_from_file = card_data.get(
                "id"
            )  # Assuming card_data in JSON has an 'id' field
            if card_id_from_file:
                card = card_collection.get_card_by_id(card_id_from_file)
                if card:
                    deck.add_card(card)  # This respects MAX_COPIES
                else:
                    print(
                        f"Warning: Card ID {card_id_from_file} not found in collection when loading deck {filename}"
                    )
            else:  # Legacy or different format handling
                set_code = card_data.get("set_code")
                card_number = card_data.get("card_number")
                if set_code and card_number:
                    card = card_collection.get_card(set_code, card_number)
                    if card:
                        deck.add_card(card)
                    else:
                        print(
                            f"Warning: Could not find card with set_code={set_code}, card_number={card_number} when loading deck {filename}"
                        )

        # If after loading, no cover cards are set (e.g., from an old deck file or empty list),
        # and the deck has cards, select automatically.
        if not deck.cover_card_ids and deck.cards:
            deck.select_cover_card_automatically()

        # Store created_at if needed as an attribute, or just let it be in deck_data for collection page
        # deck.created_at_str = deck_data.get("created_at")

        return deck

    @classmethod
    def generate_random_deck(
        cls, card_collection: CardCollection, deck_name: str = "Random Deck"
    ) -> "Deck":
        """
        Generate a random deck from the available cards in the collection.
        The deck will contain exactly MAX_CARDS with no more than MAX_COPIES of any card.
        Ensures at least one Basic Pokémon is included.
        """
        import random

        # Create a new empty deck
        deck = cls(deck_name)

        # Get all basic Pokémon to ensure we have at least one
        all_basic_pokemon = [
            card for card in card_collection.cards if card.is_pokemon and card.is_basic
        ]

        if not all_basic_pokemon:
            # Handle case where there are no basic pokemon in the collection
            if card_collection.cards:
                print(
                    "Warning: No Basic Pokémon found in card collection. Cannot guarantee a valid random deck."
                )
                # Fallback to adding any random card if no basic pokemon
                deck.add_card(random.choice(card_collection.cards))
            else:
                raise ValueError(
                    "Card collection is empty. Cannot generate a random deck."
                )

        else:
            # Add a random Basic Pokémon first to ensure the deck is valid
            basic_pokemon = random.choice(all_basic_pokemon)
            deck.add_card(basic_pokemon)

            # Use this first Pokémon as the cover card
            deck.set_cover_card(basic_pokemon)

        # Get all Pokémon with non-colorless energy requirements to potentially influence deck types
        typed_pokemon = [
            card
            for card in card_collection.cards
            if card.is_pokemon
            and any(
                cost != "C"
                for attack in card.attacks
                for cost in attack.get("cost", [])
            )
        ]

        # Attempt to add a few typed Pokémon if available and deck isn't full
        if typed_pokemon:
            typed_pokemon_shuffled = random.sample(
                typed_pokemon, min(len(typed_pokemon), 5)
            )  # Pick a few to try
            for typed_card in typed_pokemon_shuffled:
                if len(deck.cards) >= deck.MAX_CARDS:
                    break  # Stop if deck is full
                if deck.add_card(typed_card):
                    pass  # Card added

        # Get all cards that can be added to the deck respecting MAX_COPIES
        # Filter out cards we already have MAX_COPIES of initially
        available_cards_to_add = [
            card
            for card in card_collection.cards
            if deck.card_counts.get(card.name, 0) < deck.MAX_COPIES
        ]
        random.shuffle(available_cards_to_add)  # Randomize the order

        # Fill the remaining slots in the deck with random cards
        for card in available_cards_to_add:
            # Skip if we've reached the maximum deck size
            if len(deck.cards) >= deck.MAX_CARDS:
                break

            # add_card already checks for max copies, so we can just call it
            deck.add_card(card)

        # Ensure the deck has exactly MAX_CARDS (it might have less if not enough unique cards)
        # This random generation logic might need refinement if you strictly need MAX_CARDS always
        # but adding cards only if valid might result in fewer than 20 if the collection is small/restricted.
        # Assuming for now less than MAX_CARDS is acceptable if cannot fill.

        # Determine the deck types based on the Pokémon types included
        deck_types = deck.determine_deck_types()
        deck.set_deck_types(deck_types)

        return deck

    def __str__(self) -> str:
        valid, reason = self.is_valid()
        status = "Valid" if valid else f"Invalid: {reason}"
        pokemon_count = self.get_pokemon_count()
        trainer_count = self.get_trainer_count()
        deck_types_str = (
            ", ".join(self.deck_types) if self.deck_types else "Unspecified"
        )
        cover_ids_str = (
            ", ".join(self.cover_card_ids) if self.cover_card_ids else "None"
        )

        return (
            f"Deck: {self.name}\n"
            f"Owner: {self.owner or 'Unknown'}\n"
            f"Types: {deck_types_str}\n"
            f"Cover Card IDs: {cover_ids_str}\n"  # Displaying IDs
            f"Status: {status}\n"
            f"Card count: {len(self.cards)}/{self.MAX_CARDS}\n"
            f"Pokemon: {pokemon_count}\n"
            f"Trainers: {trainer_count}"
        )

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
            for name, cards in sorted(
                pokemon_by_name.items(),
                key=lambda x: (
                    0 if x[1][0].evolution_stage is None else x[1][0].evolution_stage,
                    x[0],
                ),
            ):
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
                subtype = (
                    f" ({cards[0].trainer_subtype})" if cards[0].trainer_subtype else ""
                )
                print(f"  {count}x {name}{subtype}")

        # Print deck status
        valid, reason = self.is_valid()
        if valid:
            print("\nDeck is valid and ready to play!")
        else:
            print(f"\nDeck is not valid: {reason}")
