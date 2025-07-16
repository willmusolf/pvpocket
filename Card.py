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

    def load_from_firestore(self, db_client) -> None:
        self.cards = []
        self.cards_by_id = {}
        self.cards_by_name = {}
        print("Loading card collection from Firestore (nested structure)...")
        loaded_card_count = 0
        try:
            sets_collection_ref = db_client.collection("cards")
            set_docs_stream = sets_collection_ref.stream()
            for set_doc in set_docs_stream:
                cards_subcollection_ref = set_doc.reference.collection("set_cards")
                card_docs_stream = cards_subcollection_ref.stream()
                for card_doc in card_docs_stream:
                    card_data = card_doc.to_dict()
                    if card_data is None:
                        # print(f"Warning: Card document {set_doc.id}/{card_doc.id} has no data. Skipping.")
                        continue
                    try:
                        card_pk_id = card_data.get("id")
                        if card_pk_id is None:
                            # print(f"Warning: Card data from Firestore doc {set_doc.id}/{card_doc.id} is missing 'id' field. Skipping.")
                            continue

                        card = Card(
                            id=int(card_pk_id),
                            name=card_data.get("name", ""),
                            energy_type=card_data.get("energy_type", ""),
                            set_name=card_data.get("set_name", ""),
                            set_code=card_data.get("set_code", ""),
                            card_number=card_data.get(
                                "card_number"
                            ),  # This is the int (or None) from Firestore
                            card_number_str=card_data.get(
                                "card_number_str", ""
                            ),  # This is the string from Firestore
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
                        )
                        self.add_card(card)
                        loaded_card_count += 1
                    except Exception as e_card_init:
                        print(
                            f"Error initializing Card object from Firestore doc {set_doc.id}/{card_doc.id}. Data: {card_data}. Error: {e_card_init}"
                        )
            print(
                f"Successfully loaded {loaded_card_count} cards from Firestore into CardCollection."
            )
        except Exception as e:
            print(f"Error loading cards from Firestore for CardCollection: {e}")

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
