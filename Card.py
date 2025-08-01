# Author: -REPLACE WITH YOUR NAME-
# OS support: -REPLACE WITH YOUR OS SUPPORT-
# Description: Defines Card and CardCollection classes for managing Pokemon card data.
import sqlite3
import json
import re
from typing import Dict, List, Optional, Union, Any, Tuple


class Card:
    """A class representing a Pokemon TCG Pocket card."""

    def __init__(
        self,
        id: int = None,
        name: str = "",
        energy_type: str = "",
        set_name: str = "",
        set_code: str = "",
        card_number: Optional[int] = None,  # Integer version
        card_number_str: str = "",  # Original string version
        card_type: str = "",
        hp: Optional[int] = None,
        attacks: Union[str, List[Dict[str, Any]]] = "[]",
        weakness: Optional[str] = None,
        retreat_cost: Optional[int] = None,
        illustrator: Optional[str] = None,
        firebase_image_url: Optional[str] = None,
        rarity: str = "",
        pack: str = "",
        flavor_text: Optional[str] = None,
        abilities: Optional[List[Dict[str, str]]] = None,
        original_image_url: Optional[str] = None,
        set_release_order: Optional[int] = None,  # New field for automatic set priority
    ):
        """Initialize a Card object with provided attributes."""
        self.id = id
        self.name = name
        self.energy_type = energy_type
        self.rarity = rarity
        self.pack = pack

        self.set_name = set_name.strip()
        if "(" in set_name:
            self.set_name = re.sub(r"\s*\([A-Za-z0-9\-]+\)\s*$", "", set_name).strip()

        self.set_code = set_code
        self.card_number = card_number  # Integer or None
        self.card_number_str = card_number_str  # Original string
        self.card_type = re.sub(r"\s+", " ", card_type.strip()) if card_type else ""
        self.hp = hp
        self.flavor_text = flavor_text

        self.abilities: List[Dict[str, str]] = (
            abilities if abilities is not None else []
        )

        if isinstance(attacks, str):
            try:
                self.attacks = json.loads(attacks.replace("'", '"'))
            except json.JSONDecodeError:
                self.attacks = []
        else:
            self.attacks = attacks

        self.weakness = weakness
        self.retreat_cost = retreat_cost
        self.illustrator = illustrator

        self.original_image_url = original_image_url
        self.firebase_image_url = firebase_image_url
        self.set_release_order = set_release_order

    @property
    def display_image_path(self) -> Optional[str]:
        if self.firebase_image_url:
            return self.firebase_image_url
        return self.original_image_url

    @property
    def is_pokemon(self) -> bool:
        return "Pokémon" in self.card_type

    @property
    def is_trainer(self) -> bool:
        return "Trainer" in self.card_type

    @property
    def is_basic(self) -> bool:
        return self.is_pokemon and "Basic" in self.card_type

    @property
    def is_evolution(self) -> bool:
        return self.is_pokemon and (
            "Stage 1" in self.card_type or "Stage 2" in self.card_type
        )

    @property
    def evolution_stage(self) -> Optional[int]:
        if not self.is_pokemon:
            return None
        if "Basic" in self.card_type:
            return 0
        elif "Stage 1" in self.card_type:
            return 1
        elif "Stage 2" in self.card_type:
            return 2
        return None

    @property
    def evolves_from(self) -> Optional[str]:
        if self.is_evolution and "Evolves from" in self.card_type:
            parts = self.card_type.split("Evolves from")
            if len(parts) > 1:
                return parts[1].strip()
        return None

    @property
    def trainer_subtype(self) -> Optional[str]:
        if not self.is_trainer:
            return None
        if "-" in self.card_type:
            return self.card_type.split("-")[1].strip()
        return None

    def get_attack(self, attack_name: str) -> Optional[Dict[str, Any]]:
        for attack in self.attacks:
            if attack.get("name", "").lower() == attack_name.lower():
                return attack
        return None

    def get_attack_cost(self, attack_name: str) -> List[str]:
        attack = self.get_attack(attack_name)
        if attack:
            return attack.get("cost", [])
        return []

    def get_attack_damage(self, attack_name: str) -> str:
        attack = self.get_attack(attack_name)
        if attack:
            return attack.get("damage", "0")
        return "0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "energy_type": self.energy_type,
            "set_name": self.set_name,
            "set_code": self.set_code,
            "card_number": self.card_number,  # Integer or None
            "card_number_str": self.card_number_str,  # Original String
            "card_type": self.card_type,
            "hp": self.hp,
            "attacks": self.attacks,
            "weakness": self.weakness,
            "retreat_cost": self.retreat_cost,
            "illustrator": self.illustrator,
            "original_image_url": self.original_image_url,
            "firebase_image_url": self.firebase_image_url,
            "rarity": self.rarity,
            "pack": self.pack,
            "flavor_text": self.flavor_text,
            "abilities": self.abilities,
            "set_release_order": self.set_release_order,
        }

    def __str__(self) -> str:
        card_info = f"{self.name} ({self.set_name} {self.card_number_str})"  # Use card_number_str
        if self.is_pokemon and self.energy_type:
            card_info += f" - {self.energy_type}"
        if self.is_pokemon and self.hp:
            card_info += f" - {self.hp} HP"
        if self.rarity:
            card_info += f" - {self.rarity}"
        return card_info

    def __repr__(self) -> str:
        return f"Card(id={self.id}, name='{self.name}', energy_type='{self.energy_type}', set_code='{self.set_code}', card_number_str='{self.card_number_str}')"  # Use card_number_str


class CardCollection:
    def __init__(self):
        self.cards: List[Card] = []
        self.cards_by_id: Dict[int, Card] = {}
        self.cards_by_name: Dict[str, List[Card]] = {}

    def add_card(self, card: Card) -> None:
        self.cards.append(card)
        if card.id is not None:
            self.cards_by_id[card.id] = card
        if card.name not in self.cards_by_name:
            self.cards_by_name[card.name] = []
        self.cards_by_name[card.name].append(card)

    def get_card_by_id(self, card_id: int) -> Optional[Card]:
        return self.cards_by_id.get(card_id)

    def get_cards_by_name(self, name: str) -> List[Card]:
        return self.cards_by_name.get(name, [])

    def get_card(
        self, set_code: str, card_number_str_to_find: str
    ) -> Optional[Card]:  # Parameter renamed for clarity
        for card in self.cards:
            if (
                card.set_code == set_code
                and card.card_number_str == card_number_str_to_find
            ):  # Compare with card.card_number_str
                return card
        return None

    def filter(self, **kwargs) -> List[Card]:
        result = []
        for card in self.cards:
            match = True
            for key, value in kwargs.items():
                if key == "name" and isinstance(value, str):
                    if value.lower() not in card.name.lower():
                        match = False
                        break
                elif hasattr(card, key) and getattr(card, key) != value:
                    match = False
                    break
                elif not hasattr(card, key):
                    match = False
                    break
            if match:
                result.append(card)
        return result

    def load_from_firestore(self, db_client, max_cards: int = None) -> None:
        """Load cards from Firestore with optimized batch queries.
        
        Args:
            db_client: Firestore client
            max_cards: Optional limit on number of cards to load (for partial loading)
        """
        self.cards = []
        self.cards_by_id = {}
        self.cards_by_name = {}
        loaded_card_count = 0
        
        try:
            # First, try to use collection group query for efficient loading
            # This reads all cards across all subcollections in one query
            try:
                from flask import current_app
                if current_app and current_app.debug:
                    current_app.logger.debug("Attempting optimized collection group query for cards...")
                
                # Use collection group query to get all set_cards in one go
                collection_group_ref = db_client.collection_group("set_cards")
                
                # Add limit if specified to reduce reads
                if max_cards:
                    query = collection_group_ref.limit(max_cards)
                else:
                    query = collection_group_ref
                
                card_docs = list(query.stream())
                
                if current_app and current_app.debug:
                    current_app.logger.debug(f"Collection group query returned {len(card_docs)} cards")
                
                # Process all cards from collection group query
                for card_doc in card_docs:
                    card_data = card_doc.to_dict()
                    if card_data is None:
                        continue
                    
                    try:
                        card_pk_id = card_data.get("id")
                        if card_pk_id is None:
                            continue

                        card = Card(
                            id=int(card_pk_id),
                            name=card_data.get("name", ""),
                            energy_type=card_data.get("energy_type", ""),
                            set_name=card_data.get("set_name", ""),
                            set_code=card_data.get("set_code", ""),
                            card_number=card_data.get("card_number"),
                            card_number_str=card_data.get("card_number_str", ""),
                            card_type=card_data.get("card_type", ""),
                            hp=card_data.get("hp"),
                            attacks=card_data.get("attacks", []),
                            weakness=card_data.get("weakness"),
                            retreat_cost=card_data.get("retreat_cost"),
                            illustrator=card_data.get("illustrator"),
                            firebase_image_url=card_data.get("firebase_image_url"),
                            rarity=card_data.get("rarity", ""),
                            pack=card_data.get("pack", ""),
                            original_image_url=card_data.get("original_image_url"),
                            flavor_text=card_data.get("flavor_text"),
                            abilities=card_data.get("abilities", []),
                            set_release_order=card_data.get("set_release_order"),
                        )
                        self.add_card(card)
                        loaded_card_count += 1
                        
                    except Exception as e_card_init:
                        # Card initialization error (skip silently in production)
                        if current_app and current_app.debug:
                            current_app.logger.debug(f"Error initializing card: {e_card_init}")
                        pass
                
                if loaded_card_count > 0:
                    if current_app and current_app.debug:
                        current_app.logger.debug(f"Successfully loaded {loaded_card_count} cards using collection group query")
                    return
                    
            except Exception as e_collection_group:
                # Collection group query failed, fall back to original method
                if current_app and current_app.debug:
                    current_app.logger.debug(f"Collection group query failed: {e_collection_group}, falling back to original method")
            
            # Fallback: Original method with some optimizations
            sets_collection_ref = db_client.collection("cards")
            set_docs = list(sets_collection_ref.stream())  # Load all set docs at once
            
            if current_app and current_app.debug:
                current_app.logger.debug(f"Found {len(set_docs)} documents in cards collection")
            
            # Try to load cards directly from documents first (for test data)
            direct_cards_loaded = 0
            for doc in set_docs:
                doc_data = doc.to_dict()
                if doc_data and doc_data.get("id") and doc_data.get("name"):
                    # This looks like a direct card document
                    try:
                        card_pk_id = doc_data.get("id")
                        if card_pk_id is None:
                            continue

                        card = Card(
                            id=int(card_pk_id),
                            name=doc_data.get("name", ""),
                            energy_type=doc_data.get("energy_type", ""),
                            set_name=doc_data.get("set_name", ""),
                            set_code=doc_data.get("set_code", ""),
                            card_number=doc_data.get("card_number"),
                            card_number_str=doc_data.get("card_number_str", ""),
                            card_type=doc_data.get("card_type", ""),
                            hp=doc_data.get("hp"),
                            attacks=doc_data.get("attacks", []),
                            weakness=doc_data.get("weakness"),
                            retreat_cost=doc_data.get("retreat_cost"),
                            illustrator=doc_data.get("illustrator"),
                            firebase_image_url=doc_data.get("firebase_image_url"),
                            rarity=doc_data.get("rarity", ""),
                            pack=doc_data.get("pack", ""),
                            original_image_url=doc_data.get("original_image_url"),
                            flavor_text=doc_data.get("flavor_text"),
                            abilities=doc_data.get("abilities", []),
                        )
                        self.add_card(card)
                        direct_cards_loaded += 1
                        loaded_card_count += 1
                        
                        # Respect max_cards limit
                        if max_cards and loaded_card_count >= max_cards:
                            break
                            
                    except Exception as e_card_init:
                        # Card initialization error (skip silently in production)
                        pass
            
            if current_app and current_app.debug:
                current_app.logger.debug(f"Loaded {direct_cards_loaded} cards directly from documents")
            
            # If we found direct cards, we're done
            if direct_cards_loaded > 0:
                return
            
            # Otherwise, try loading from subcollections (production structure) with limits
            # Apply smart loading strategy to reduce Firebase reads
            
            if current_app and current_app.debug:
                current_app.logger.debug("Loading from subcollections with read optimization...")
            
            # Limit the number of sets to process if max_cards is specified
            sets_to_process = set_docs
            if max_cards:
                # Only process a subset of sets to stay within card limit
                estimated_cards_per_set = max_cards // max(len(set_docs), 1)
                max_sets = min(len(set_docs), max(1, max_cards // 50))  # Assume ~50 cards per set average
                sets_to_process = set_docs[:max_sets]
                if current_app and current_app.debug:
                    current_app.logger.debug(f"Limited to processing {len(sets_to_process)} sets to stay within {max_cards} card limit")
            
            # Process sets with optimized batch loading
            batch_size = 3  # Reduced batch size to limit concurrent reads
            
            for i in range(0, len(sets_to_process), batch_size):
                batch_sets = sets_to_process[i:i + batch_size]
                batch_loaded = 0
                
                # Load cards for this batch of sets
                for set_doc in batch_sets:
                    try:
                        # Get set data including release_order
                        set_data = set_doc.to_dict() or {}
                        set_release_order = set_data.get("release_order", None)
                        
                        # Use limit to reduce reads per subcollection
                        cards_subcollection_ref = set_doc.reference.collection("set_cards")
                        
                        # Apply per-set card limit if max_cards is specified
                        if max_cards and loaded_card_count >= max_cards:
                            break
                            
                        remaining_cards = max_cards - loaded_card_count if max_cards else None
                        if remaining_cards and remaining_cards > 0:
                            # Limit query to remaining card count
                            query = cards_subcollection_ref.limit(min(remaining_cards, 100))
                            card_docs = list(query.stream())
                        else:
                            # No limit specified, load all (but still limit to 200 per set to prevent runaway reads)
                            query = cards_subcollection_ref.limit(200)
                            card_docs = list(query.stream())
                        
                        # Process all cards from this set
                        for card_doc in card_docs:
                            card_data = card_doc.to_dict()
                            if card_data is None:
                                continue
                            
                            # Check if we've hit our max_cards limit
                            if max_cards and loaded_card_count >= max_cards:
                                break
                                
                            try:
                                card_pk_id = card_data.get("id")
                                if card_pk_id is None:
                                    continue

                                card = Card(
                                    id=int(card_pk_id),
                                    name=card_data.get("name", ""),
                                    energy_type=card_data.get("energy_type", ""),
                                    set_name=card_data.get("set_name", ""),
                                    set_code=card_data.get("set_code", ""),
                                    card_number=card_data.get("card_number"),
                                    card_number_str=card_data.get("card_number_str", ""),
                                    card_type=card_data.get("card_type", ""),
                                    hp=card_data.get("hp"),
                                    attacks=card_data.get("attacks", []),
                                    weakness=card_data.get("weakness"),
                                    retreat_cost=card_data.get("retreat_cost"),
                                    illustrator=card_data.get("illustrator"),
                                    firebase_image_url=card_data.get("firebase_image_url"),
                                    rarity=card_data.get("rarity", ""),
                                    pack=card_data.get("pack", ""),
                                    original_image_url=card_data.get("original_image_url"),
                                    flavor_text=card_data.get("flavor_text"),
                                    abilities=card_data.get("abilities", []),
                                    set_release_order=set_release_order,
                                )
                                self.add_card(card)
                                batch_loaded += 1
                                loaded_card_count += 1
                                
                            except Exception as e_card_init:
                                # Card initialization error (skip silently in production)
                                pass
                                
                    except Exception as e_set:
                        # Set loading error (skip silently in production)
                        pass
                
                # Progress update for large collections
                # Batch loading progress (removed for production performance)
                        
            # Successfully loaded cards from Firestore
            
        except Exception as e:
            # Critical error loading cards (log only in debug mode)
            try:
                from flask import current_app
                if current_app and current_app.debug:
                    current_app.logger.error(f"Critical error loading cards from Firestore: {e}")
            except:
                pass

    def get_pokemon_cards(self) -> List[Card]:
        return [card for card in self.cards if card.is_pokemon]

    def get_trainer_cards(self) -> List[Card]:
        return [card for card in self.cards if card.is_trainer]

    def get_cards_by_type(self, card_type: str) -> List[Card]:
        return [
            card for card in self.cards if card_type.lower() in card.card_type.lower()
        ]

    def __len__(self) -> int:
        return len(self.cards)


# --- End of Card.py ---
