"""
Unit tests for Card class core functionality.
"""

import pytest
import json
from Card import Card, CardCollection


@pytest.mark.unit
class TestCard:
    """Test Card class functionality."""
    
    def test_card_initialization_basic(self):
        """Test basic card creation with minimal data."""
        card = Card(
            id=1,
            name="Test Card",
            energy_type="Fire",
            hp=100
        )
        
        assert card.id == 1
        assert card.name == "Test Card"
        assert card.energy_type == "Fire"
        assert card.hp == 100
        assert card.attacks == []  # Default empty attacks
    
    def test_card_initialization_complete(self):
        """Test card creation with complete data."""
        attacks_data = [{"name": "Flame Thrower", "damage": 50, "energy_cost": 2}]
        
        card = Card(
            id=25,
            name="Charizard",
            energy_type="Fire",
            set_name="Base Set",
            set_code="BS",
            card_number=4,
            card_number_str="004",
            card_type="Pokemon",
            hp=120,
            attacks=json.dumps(attacks_data),
            weakness="Water",
            retreat_cost=2,
            rarity="Rare",
            pack="Charizard Pack"
        )
        
        assert card.id == 25
        assert card.name == "Charizard"
        assert card.energy_type == "Fire"
        assert card.hp == 120
        assert card.weakness == "Water"
        assert card.retreat_cost == 2
        assert card.rarity == "Rare"
        assert card.pack == "Charizard Pack"
    
    def test_attacks_parsing_valid_json(self):
        """Test automatic parsing of valid JSON attacks."""
        attacks_json = '[{"name": "Thunder Shock", "damage": 20, "energy_cost": 1}]'
        card = Card(id=1, name="Pikachu", attacks=attacks_json)
        
        assert len(card.attacks) == 1
        assert card.attacks[0]["name"] == "Thunder Shock"
        assert card.attacks[0]["damage"] == 20
        assert card.attacks[0]["energy_cost"] == 1
    
    def test_attacks_parsing_empty_string(self):
        """Test parsing empty attacks string."""
        card = Card(id=1, name="Test Card", attacks="")
        
        assert card.attacks == []
    
    def test_attacks_parsing_invalid_json(self):
        """Test parsing invalid JSON attacks."""
        card = Card(id=1, name="Test Card", attacks="invalid json")
        
        assert card.attacks == []
    
    def test_attacks_already_list(self):
        """Test when attacks is already a list."""
        attacks_list = [{"name": "Splash", "damage": 0}]
        card = Card(id=1, name="Magikarp", attacks=attacks_list)
        
        assert card.attacks == attacks_list
    
    def test_card_str_representation(self):
        """Test string representation of card."""
        card = Card(
            id=1, 
            name="Pikachu", 
            energy_type="Lightning", 
            hp=60,
            set_name="Base Set",
            card_number_str="025"
        )
        
        str_repr = str(card)
        
        assert "Pikachu" in str_repr
        assert "Base Set" in str_repr


@pytest.mark.unit
class TestCardCollection:
    """Test CardCollection functionality."""
    
    def test_empty_collection(self):
        """Test empty collection creation."""
        collection = CardCollection()
        
        assert len(collection) == 0
        assert collection.get_card_by_id(1) is None
    
    def test_add_and_get_card(self):
        """Test adding and retrieving cards."""
        collection = CardCollection()
        card = Card(id=1, name="Pikachu", energy_type="Lightning")
        
        collection.add_card(card)
        
        assert len(collection) == 1
        retrieved_card = collection.get_card_by_id(1)
        assert retrieved_card is not None
        assert retrieved_card.name == "Pikachu"
    
    def test_get_cards_by_name(self):
        """Test retrieving cards by name."""
        collection = CardCollection()
        card1 = Card(id=1, name="Pikachu", energy_type="Lightning")
        card2 = Card(id=2, name="Charizard", energy_type="Fire")
        
        collection.add_card(card1)
        collection.add_card(card2)
        
        found_cards = collection.get_cards_by_name("Pikachu")
        assert len(found_cards) == 1
        assert found_cards[0].id == 1
        
        not_found = collection.get_cards_by_name("Blastoise")
        assert len(not_found) == 0
    
    def test_get_cards_by_type(self):
        """Test filtering cards by card type."""
        collection = CardCollection()
        pokemon_card = Card(id=1, name="Charmander", card_type="Pokemon")
        trainer_card = Card(id=2, name="Professor Oak", card_type="Trainer")
        pokemon_card2 = Card(id=3, name="Charizard", card_type="Pokemon")
        
        collection.add_card(pokemon_card)
        collection.add_card(trainer_card)
        collection.add_card(pokemon_card2)
        
        pokemon_cards = collection.get_cards_by_type("Pokemon")
        assert len(pokemon_cards) == 2
        
        trainer_cards = collection.get_cards_by_type("Trainer")
        assert len(trainer_cards) == 1
        
        energy_cards = collection.get_cards_by_type("Energy")
        assert len(energy_cards) == 0