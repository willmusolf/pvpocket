from typing import Dict, List, Optional, Set, Tuple, Any  # Added Any for type hints

# import json # No longer directly used for saving/loading decks
# import os  # No longer directly used for saving/loading decks
from Card import Card, CardCollection
import datetime  # Import the datetime module

from firebase_admin import firestore  # Assuming firebase_admin is initialized elsewhere


class Deck:
    """A class representing a Pokemon TCG Pocket deck."""

    # Deck building constants
    MAX_CARDS = 20
    MAX_COPIES = 2  # Maximum number of cards with the same name

    def __init__(
        self,
        name: str = "New Deck",
        deck_types: Optional[List[str]] = None,
        cover_card_ids: Optional[List[str]] = None,
        owner_id: Optional[str] = None,
        deck_id: Optional[
            str
        ] = None,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
    ):
        self.name = name
        self.name_lowercase = name.lower()  # For Firestore querying
        self.deck_types = deck_types if deck_types is not None else []
        self.cards: List[Card] = []
        self.card_counts: Dict[str, int] = {}
        self.cover_card_ids: List[str] = (
            cover_card_ids if cover_card_ids is not None else []
        )
        self.id: Optional[str] = deck_id  # Firestore document ID
        self.owner_id: Optional[str] = owner_id  # User's Firestore document ID
        self.created_at: Optional[datetime.datetime] = created_at
        self.updated_at: Optional[datetime.datetime] = updated_at

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        self.name_lowercase = value.lower()

    def get_cover_card_ids(self) -> List[str]:
        return self.cover_card_ids

    def add_cover_card_id(self, card_id: str) -> bool:
        if card_id not in self.cover_card_ids and len(self.cover_card_ids) < 3:
            self.cover_card_ids.append(str(card_id))
            return True
        return False

    def remove_cover_card_id(self, card_id: str) -> bool:
        """Removes a card ID from the cover card list. Returns True if removed."""
        if card_id in self.cover_card_ids:
            self.cover_card_ids.remove(str(card_id))
            return True
        return False

    # In Deck.py

    def set_cover_card_ids(
        self, card_ids: List[Any]
    ) -> None:  # Allow any type that can be str()
        """
        Set the list of cover card IDs, ensuring they are valid, unique,
        and present in the current deck. Max 3.
        """
        if not isinstance(card_ids, list):
            self.cover_card_ids = []
            return

        valid_and_unique_ids_in_order = []
        current_deck_master_ids = {str(card.id) for card in self.cards}

        for cid_any_type in card_ids:
            cid_str_clean = str(cid_any_type).strip()
            if not cid_str_clean:
                continue

            if (
                cid_str_clean in current_deck_master_ids
                and cid_str_clean not in valid_and_unique_ids_in_order
            ):
                if len(valid_and_unique_ids_in_order) < 3:
                    valid_and_unique_ids_in_order.append(cid_str_clean)

        self.cover_card_ids = valid_and_unique_ids_in_order

    # In Deck.py
    def select_cover_card_automatically(self) -> None:
        # print(f"Auto-select called for '{self.name}'. Current cover_card_ids: {self.cover_card_ids}") # Debug
        if not self.cards:
            self.cover_card_ids = []
            # print("Auto-select: No cards in deck, cover_card_ids set to [].") # Debug
            return

        final_selected_ids = [
            str(cid) for cid in self.cover_card_ids
        ]  # Ensure all are strings

        temp_unique_set = set()
        deduplicated_initial_selection = []
        for cid in final_selected_ids:
            if cid not in temp_unique_set:
                deduplicated_initial_selection.append(cid)
                temp_unique_set.add(cid)
        final_selected_ids = deduplicated_initial_selection[:3]

        if len(final_selected_ids) >= 3:
            self.cover_card_ids = final_selected_ids
            # print(f"Auto-select: Already have {len(self.cover_card_ids)} cover cards. No changes.") # Debug
            return

        num_to_add = 3 - len(final_selected_ids)
        candidate_cards_for_auto = []
        current_selection_set = set(final_selected_ids)

        unique_deck_cards_dict = {}
        for card in self.cards:
            if str(card.id) not in unique_deck_cards_dict:
                unique_deck_cards_dict[str(card.id)] = card

        potential_candidates = [
            card
            for card_id_str, card in unique_deck_cards_dict.items()
            if card_id_str not in current_selection_set
        ]

        if not potential_candidates:
            self.cover_card_ids = final_selected_ids
            # print(f"Auto-select: No more distinct candidates. Final IDs: {self.cover_card_ids}") # Debug
            return

        sorted_auto_candidates = sorted(
            potential_candidates, key=self._auto_select_sort_key
        )

        for candidate in sorted_auto_candidates:
            if len(final_selected_ids) >= 3:
                break
            final_selected_ids.append(str(candidate.id))

        self.cover_card_ids = final_selected_ids
        # print(f"Auto-select: Final cover_card_ids after auto-filling: {self.cover_card_ids}") # Debug

    # Helper for the sort key to be part of the class or defined locally
    def _auto_select_sort_key(self, card):
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
        category_rank = 5
        if is_pokemon:
            category_rank = 0
        elif is_supporter:
            category_rank = 1
        elif is_item:
            category_rank = 2
        elif "Trainer" in card.card_type:
            category_rank = 3
        rarity_rank_val = get_card_rarity_rank(card)
        return (category_rank, rarity_rank_val, card.name)

    def add_card(self, card: Card) -> bool:
        if len(self.cards) >= self.MAX_CARDS:
            # print(f"Cannot add {card.name}. Deck is full.") # Debug
            return False
        if self.card_counts.get(card.name, 0) >= self.MAX_COPIES:
            # print(f"Cannot add {card.name}. Max copies reached.") # Debug
            return False
        self.cards.append(card)
        self.card_counts[card.name] = self.card_counts.get(card.name, 0) + 1
        return True

    def remove_card(self, card: Card) -> bool:
        for i, deck_card in enumerate(self.cards):
            if deck_card.id == card.id:
                del self.cards[i]
                self.card_counts[card.name] -= 1
                if self.card_counts[card.name] == 0:
                    del self.card_counts[card.name]

                # Also remove from cover_card_ids if it was there
                self.remove_cover_card_id(str(card.id))
                return True
        return False

    def remove_card_by_name(self, card_name: str) -> bool:
        for card_in_deck in list(self.cards):  # Iterate over a copy if modifying
            if card_in_deck.name == card_name:
                return self.remove_card(
                    card_in_deck
                )  # remove_card handles cover_card_ids
        return False

    def clear(self) -> None:
        self.cards = []
        self.card_counts = {}
        self.cover_card_ids = []  # Clear cover cards as well

    def is_valid(self) -> Tuple[bool, str]:
        if len(self.cards) != self.MAX_CARDS:
            return (
                False,
                f"Deck must contain {self.MAX_CARDS} cards. Has: {len(self.cards)}",
            )
        for name, count in self.card_counts.items():
            if count > self.MAX_COPIES:
                return (False, f"Too many copies of {name} ({count}/{self.MAX_COPIES})")
        if not any(card.is_pokemon and card.is_basic for card in self.cards):
            return False, "Deck needs at least one Basic Pokémon."
        return True, ""

    def get_pokemon_count(self) -> int:
        return sum(1 for card in self.cards if card.is_pokemon)

    def get_trainer_count(self) -> int:
        return sum(1 for card in self.cards if card.is_trainer)

    def set_deck_types(self, types: List[str]) -> None:
        self.deck_types = types

    def determine_deck_types(self) -> List[str]:
        type_count = {}
        for card in self.cards:
            if not card.is_pokemon:
                continue
            for attack in card.attacks:
                for cost in attack.get("cost", []):
                    if cost == "C":
                        continue
                    type_name = self._energy_to_type(cost)
                    if type_name:
                        type_count[type_name] = type_count.get(type_name, 0) + 1
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
            return (
                [random.choice(valid_types)] if self.cards else []
            )  # Return empty if no cards
        sorted_types = sorted(type_count.items(), key=lambda x: x[1], reverse=True)
        return [t[0] for t in sorted_types[:3]]

    def _energy_to_type(self, energy_symbol: str) -> Optional[str]:
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

    def to_firestore_dict(self) -> Dict[str, Any]:
        """Converts the deck to a dictionary suitable for Firestore."""
        # Ensure cover cards are auto-selected if needed before saving
        if len(self.cover_card_ids) < 3 and self.cards:
            # print(f"Deck '{self.name}' has {len(self.cover_card_ids)} user-selected cover cards. Auto-filling for Firestore save.") # Debug
            self.select_cover_card_automatically()
        elif not self.cards:
            self.cover_card_ids = []

        deck_data = {
            "name": self.name,
            "name_lowercase": self.name_lowercase,
            "deck_types": self.deck_types,
            "card_ids": sorted([str(card.id) for card in self.cards]), # Store sorted list of string card IDs
            "cover_card_ids": self.cover_card_ids,
            "owner_id": self.owner_id,
            # Timestamps are handled by Firestore server or explicitly if loaded
            "updated_at": firestore.SERVER_TIMESTAMP, # Always update this on save/update
        }
        # Only add created_at if it's a new deck (self.created_at would be None)
        if self.created_at is None:
            deck_data["created_at"] = firestore.SERVER_TIMESTAMP
        # If self.created_at exists (is a datetime object from a loaded deck),
        # it means we are updating, and Firestore will preserve the original created_at value if not overwritten.
        # So, we don't need to explicitly add self.created_at back to the dict here if it's already a datetime object.

        return deck_data

    @classmethod
    def from_firestore_doc(cls, doc_snapshot: firestore.DocumentSnapshot, card_collection: CardCollection) -> "Deck":
        """Loads a deck from a Firestore DocumentSnapshot."""
        deck_data = doc_snapshot.to_dict()
        if not deck_data: # Should not happen if doc_snapshot.exists is true
            raise ValueError("Document data is empty.")

        # Handle cover_card_ids: ensure it's a list of strings
        loaded_cover_card_ids_any = deck_data.get("cover_card_ids", [])
        if not isinstance(loaded_cover_card_ids_any, list):
            loaded_cover_card_ids = []
        else:
            loaded_cover_card_ids = [str(cid) for cid in loaded_cover_card_ids_any]

        deck = cls(
            name=deck_data.get("name", "Loaded Deck"),
            deck_types=deck_data.get("deck_types", []),
            cover_card_ids=loaded_cover_card_ids,
            owner_id=deck_data.get("owner_id"),
            deck_id=doc_snapshot.id, # Get ID from the snapshot itself
            created_at=deck_data.get("created_at"), # Will be a datetime object from Firestore
            updated_at=deck_data.get("updated_at")  # Will be a datetime object
        )
        # deck.name_lowercase is set by the name.setter or __init__

        card_ids_from_db = deck_data.get("card_ids", [])
        if isinstance(card_ids_from_db, list):
            for card_id_str in card_ids_from_db:
                try:
                    card_obj = card_collection.get_card_by_id(int(card_id_str)) # Card.id is int
                    if card_obj:
                        deck.add_card(card_obj) # Respects MAX_COPIES
                    else:
                        print(f"Warning: Card ID {card_id_str} not found in collection for deck {deck.id}") # Debug
                except ValueError:
                    print(f"Warning: Invalid card ID format '{card_id_str}' in deck {deck.id}") # Debug

        # If after loading, no cover cards are set (e.g. old deck or empty list from DB),
        # and the deck has cards, select automatically.
        if not deck.cover_card_ids and deck.cards:
            # print(f"Deck {deck.id} loaded with no cover cards. Auto-selecting.") # Debug
            deck.select_cover_card_automatically()

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
            f"Deck: {self.name} (ID: {self.id or 'N/A'})\n"  # Added deck ID
            f"Owner ID: {self.owner_id or 'Unknown'}\n"  # Changed from owner to owner_id
            f"Types: {deck_types_str}\n"
            f"Cover Card IDs: {cover_ids_str}\n"
            f"Status: {status}\n"
            f"Card count: {len(self.cards)}/{self.MAX_CARDS}\n"
            f"Pokemon: {pokemon_count}\n"
            f"Trainers: {trainer_count}\n"
            f"Created: {self.created_at}\n"  # Added timestamps
            f"Updated: {self.updated_at}"
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
