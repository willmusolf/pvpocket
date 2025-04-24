import sqlite3
import json
import csv
import re
from typing import Dict, List, Optional, Union, Any, Tuple

class Card:
    """A class representing a Pokemon TCG Pocket card."""
    
    def __init__(self, 
                id: int = None,
                name: str = "",
                energy_type: str = "",
                set_name: str = "",
                set_code: str = "",
                card_number: str = "",
                card_type: str = "",
                hp: Optional[int] = None,
                attacks: Union[str, List[Dict[str, Any]]] = "[]",
                weakness: Optional[str] = None,
                retreat_cost: Optional[int] = None,
                illustrator: Optional[str] = None,
                image_url: str = "",
                rarity: str = "",
                pack: str = "",
                local_image_path: Optional[str] = None
                ):
        """Initialize a Card object with provided attributes."""
        self.id = id
        self.name = name
        self.energy_type = energy_type
        self.rarity = rarity
        self.pack = pack
        
        # Clean up set_name to remove extra spaces and set code
        self.set_name = set_name.strip()
        if '(' in set_name:
            self.set_name = re.sub(r'\s*\([A-Za-z0-9]+\)\s*$', '', set_name).strip()
            
        self.set_code = set_code
        self.card_number = card_number
        
        # Clean up card_type to remove extra spaces
        self.card_type = re.sub(r'\s+', ' ', card_type.strip()) if card_type else ""
        
        self.hp = hp
        
        # Handle attacks as either a JSON string or a list of dictionaries
        if isinstance(attacks, str):
            try:
                self.attacks = json.loads(attacks.replace("'", "\""))
            except json.JSONDecodeError:
                self.attacks = []
        else:
            self.attacks = attacks
            
        self.weakness = weakness
        self.retreat_cost = retreat_cost
        self.illustrator = illustrator
        self.image_url = image_url
        self.local_image_path = local_image_path
        
    @property
    def display_image_path(self):
        """Returns the appropriate path for displaying the card image."""
        if self.local_image_path:
            # Since paths are already relative to the images folder 
            # and Flask is configured with static_url_path='/images'
            return f"/images/{self.local_image_path}"
        # Fall back to the original URL if no local path
        return self.image_url
    
    @property
    def is_pokemon(self) -> bool:
        """Check if the card is a Pokemon card."""
        return "Pokémon" in self.card_type
    
    @property
    def is_trainer(self) -> bool:
        """Check if the card is a Trainer card."""
        return "Trainer" in self.card_type
    
    # Note: Pokemon TCG Pocket doesn't have separate Energy cards
    
    @property
    def is_basic(self) -> bool:
        """Check if the card is a Basic Pokemon."""
        return self.is_pokemon and "Basic" in self.card_type
    
    @property
    def is_evolution(self) -> bool:
        """Check if the card is an Evolution Pokemon."""
        return self.is_pokemon and ("Stage 1" in self.card_type or "Stage 2" in self.card_type)
    
    @property
    def evolution_stage(self) -> Optional[int]:
        """Get the evolution stage of the Pokemon, if applicable."""
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
        """Get the name of the Pokemon this card evolves from, if applicable."""
        if self.is_evolution and "Evolves from" in self.card_type:
            parts = self.card_type.split("Evolves from")
            if len(parts) > 1:
                return parts[1].strip()
        return None
    
    @property
    def trainer_subtype(self) -> Optional[str]:
        """Get the subtype of a Trainer card (Item, Tool, Supporter, etc.)."""
        if not self.is_trainer:
            return None
        
        if "-" in self.card_type:
            return self.card_type.split("-")[1].strip()
        return None
    
    def get_attack(self, attack_name: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific attack by name."""
        for attack in self.attacks:
            if attack.get("name", "").lower() == attack_name.lower():
                return attack
        return None
    
    def get_attack_cost(self, attack_name: str) -> List[str]:
        """Get the energy cost of a specific attack."""
        attack = self.get_attack(attack_name)
        if attack:
            return attack.get("cost", [])
        return []
    
    def get_attack_damage(self, attack_name: str) -> str:
        """Get the base damage of a specific attack."""
        attack = self.get_attack(attack_name)
        if attack:
            return attack.get("damage", "0")
        return "0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the card to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "energy_type": self.energy_type,
            "set_name": self.set_name,
            "set_code": self.set_code,
            "card_number": self.card_number,
            "card_type": self.card_type,
            "hp": self.hp,
            "attacks": self.attacks,
            "weakness": self.weakness,
            "retreat_cost": self.retreat_cost,
            "illustrator": self.illustrator,
            "image_url": self.image_url,
            "rarity": self.rarity,
            "pack": self.pack,
            "local_image_path": self.local_image_path
        }
    
    def __str__(self) -> str:
        """Return a string representation of the card."""
        card_info = f"{self.name} ({self.set_name} {self.card_number})"
        if self.is_pokemon and self.energy_type:
            card_info += f" - {self.energy_type}"
        if self.is_pokemon and self.hp:
            card_info += f" - {self.hp} HP"
        if self.rarity:
            card_info += f" - {self.rarity}"
        return card_info
    
    def __repr__(self) -> str:
        """Return a detailed string representation of the card."""
        return f"Card(id={self.id}, name='{self.name}', energy_type='{self.energy_type}', set_code='{self.set_code}', card_number='{self.card_number}')"


class CardCollection:
    """A collection of Pokemon cards with methods for loading and querying."""
    
    def __init__(self):
        """Initialize an empty card collection."""
        self.cards: List[Card] = []
        self.cards_by_id: Dict[int, Card] = {}
        self.cards_by_name: Dict[str, List[Card]] = {}
    
    def add_card(self, card: Card) -> None:
        """Add a card to the collection."""
        self.cards.append(card)
        
        # Update lookup dictionaries
        if card.id:
            self.cards_by_id[card.id] = card
        
        if card.name not in self.cards_by_name:
            self.cards_by_name[card.name] = []
        self.cards_by_name[card.name].append(card)
    
    def get_card_by_id(self, card_id: int) -> Optional[Card]:
        """Get a card by its ID."""
        return self.cards_by_id.get(card_id)
    
    def get_cards_by_name(self, name: str) -> List[Card]:
        """Get all cards with the given name."""
        return self.cards_by_name.get(name, [])
    
    def get_card(self, set_code: str, card_number: str) -> Optional[Card]:
        """Get a specific card by set code and card number."""
        for card in self.cards:
            if card.set_code == set_code and card.card_number == card_number:
                return card
        return None
    
    def filter(self, **kwargs) -> List[Card]:
        """Filter cards by various attributes."""
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
            if match:
                result.append(card)
        return result
    
    def load_from_db(self, db_path: str = "pokemon_cards.db") -> None:
        """Load cards from the SQLite database."""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check how many rows actually exist
        cursor.execute("SELECT COUNT(*) FROM cards")
        row_count = cursor.fetchone()[0]
        print(f"Database contains {row_count} rows")
        
        # Get list of unique card IDs to avoid duplicates
        cursor.execute("SELECT id, name, set_code, card_number FROM cards")
        rows = cursor.fetchall()
        
        # Keep track of unique card identifiers to avoid duplicates
        seen_cards = set()
        
        for row in rows:
            # Create a unique identifier for the card (set code + card number)
            card_key = f"{row['set_code']}_{row['card_number']}"
            
            # Skip if we've already loaded this card
            if card_key in seen_cards:
                # print(f"Skipping duplicate: {row['name']} ({card_key})")
                continue
                
            seen_cards.add(card_key)
            
            # Now load the full card data
            cursor.execute("SELECT * FROM cards WHERE id = ?", (row['id'],))
            card_data = cursor.fetchone()
        
            card = Card(
                id=card_data['id'],
                name=card_data['name'],
                energy_type=card_data.get('energy_type', ''),
                set_name=card_data['set_name'],
                set_code=card_data['set_code'],
                card_number=card_data['card_number'],
                card_type=card_data['card_type'],
                hp=card_data['hp'],
                attacks=card_data['attacks'],
                weakness=card_data['weakness'],
                retreat_cost=card_data['retreat_cost'],
                illustrator=card_data['illustrator'],
                image_url=card_data['image_url'],
                rarity=card_data.get('rarity', ''),
                pack=card_data.get('pack', ''),
                local_image_path=card_data.get('local_image_path', None)
            )
            self.add_card(card)
        
        print(f"Actually loaded {len(self.cards)} unique cards")
        conn.close()
    
    def load_from_csv(self, csv_path: str = "pokemon_cards.csv") -> None:
        """Load cards from CSV file."""
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            id_counter = 1
            for row in reader:
                # CSV doesn't have IDs, so we generate them
                card = Card(
                    id=id_counter,
                    name=row.get('Name', ''),
                    energy_type=row.get('Energy Type', ''),
                    set_name=row.get('Set Name', ''),
                    set_code=row.get('Set Code', ''),
                    card_number=row.get('Card Number', ''),
                    card_type=row.get('Card Type', ''),
                    hp=int(row.get('HP', 0)) if row.get('HP') and row.get('HP').isdigit() else None,
                    attacks=row.get('Attacks', '[]'),
                    weakness=row.get('Weakness', ''),
                    retreat_cost=int(row.get('Retreat Cost', 0)) if row.get('Retreat Cost') and row.get('Retreat Cost').isdigit() else None,
                    illustrator=row.get('Illustrator', ''),
                    image_url=row.get('Image URL', ''),
                    rarity=row.get('Rarity', ''),
                    pack=row.get('Pack', ''),
                    local_image_path=row.get('Local Image Path', '')
                )
                self.add_card(card)
                id_counter += 1
    
    def get_pokemon_cards(self) -> List[Card]:
        """Get all Pokemon cards in the collection."""
        return [card for card in self.cards if card.is_pokemon]
    
    def get_trainer_cards(self) -> List[Card]:
        """Get all Trainer cards in the collection."""
        return [card for card in self.cards if card.is_trainer]

    
    def get_cards_by_type(self, card_type: str) -> List[Card]:
        """Get cards of a specific type."""
        return [card for card in self.cards if card_type.lower() in card.card_type.lower()]
    
    def __len__(self) -> int:
        """Return the number of cards in the collection."""
        return len(self.cards)

