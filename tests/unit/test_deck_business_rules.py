"""
Unit tests for Pokemon TCG Deck Building Rules.

Tests the business logic constraints for deck building including:
- 20-card deck limit enforcement
- 2-copy per card name limit
- Basic Pokemon requirement
- Deck validation rules
- Energy type determination
"""

import pytest
from unittest.mock import Mock
from Deck import Deck
from Card import Card


@pytest.fixture
def sample_basic_pokemon():
    """Create a sample basic Pokemon card."""
    card = Mock(spec=Card)
    card.id = 1
    card.name = "Pikachu"
    card.energy_type = "Lightning"
    card.is_pokemon = True
    card.is_basic = True
    card.is_trainer = False
    card.stage = "Basic"
    return card


@pytest.fixture
def sample_evolved_pokemon():
    """Create a sample evolved Pokemon card."""
    card = Mock(spec=Card)
    card.id = 2
    card.name = "Raichu"
    card.energy_type = "Lightning"
    card.is_pokemon = True
    card.is_basic = False
    card.is_trainer = False
    card.stage = "Stage 1"
    return card


@pytest.fixture
def sample_trainer_card():
    """Create a sample trainer card."""
    card = Mock(spec=Card)
    card.id = 3
    card.name = "Professor Oak"
    card.energy_type = None
    card.is_pokemon = False
    card.is_basic = False
    card.is_trainer = True
    return card


@pytest.fixture
def sample_different_pokemon():
    """Create a different basic Pokemon card."""
    card = Mock(spec=Card)
    card.id = 4
    card.name = "Charmander"
    card.energy_type = "Fire"
    card.is_pokemon = True
    card.is_basic = True
    card.is_trainer = False
    card.stage = "Basic"
    return card


@pytest.mark.unit
class TestDeckCapacityLimits:
    """Test deck capacity and card limits."""
    
    def test_deck_max_cards_limit(self, sample_basic_pokemon):
        """Test that decks cannot exceed 20 cards."""
        deck = Deck("Test Deck")
        
        # Add 20 different cards (mocking different IDs and names)
        cards_added = 0
        for i in range(25):  # Try to add more than the limit
            card = Mock(spec=Card)
            card.id = i
            card.name = f"Card_{i}"
            card.is_pokemon = True
            card.is_basic = True
            card.is_trainer = False
            
            result = deck.add_card(card)
            
            if cards_added < deck.MAX_CARDS:
                assert result is True
                cards_added += 1
            else:
                # Should reject cards beyond the limit
                assert result is False
        
        # Verify final deck size
        assert len(deck.cards) == deck.MAX_CARDS
        assert len(deck.cards) == 20

    def test_max_copies_per_card_name(self, sample_basic_pokemon):
        """Test maximum 2 copies per card name rule."""
        deck = Deck("Test Deck")
        
        # Create multiple cards with same name but different IDs
        pikachu1 = Mock(spec=Card)
        pikachu1.id = 1
        pikachu1.name = "Pikachu"
        pikachu1.is_pokemon = True
        pikachu1.is_basic = True
        pikachu1.is_trainer = False
        
        pikachu2 = Mock(spec=Card)
        pikachu2.id = 2  # Different ID
        pikachu2.name = "Pikachu"  # Same name
        pikachu2.is_pokemon = True
        pikachu2.is_basic = True
        pikachu2.is_trainer = False
        
        pikachu3 = Mock(spec=Card)
        pikachu3.id = 3  # Different ID
        pikachu3.name = "Pikachu"  # Same name
        pikachu3.is_pokemon = True
        pikachu3.is_basic = True
        pikachu3.is_trainer = False
        
        # First copy should succeed
        assert deck.add_card(pikachu1) is True
        assert deck.card_counts["Pikachu"] == 1
        
        # Second copy should succeed
        assert deck.add_card(pikachu2) is True
        assert deck.card_counts["Pikachu"] == 2
        
        # Third copy should fail
        assert deck.add_card(pikachu3) is False
        assert deck.card_counts["Pikachu"] == 2
        assert len(deck.cards) == 2

    def test_empty_deck_validation(self):
        """Test that empty decks are invalid."""
        deck = Deck("Empty Deck")
        
        is_valid, message = deck.is_valid()
        
        assert is_valid is False
        assert "must contain 20 cards" in message
        assert "Has: 0" in message

    def test_partial_deck_validation(self, sample_basic_pokemon):
        """Test that partially filled decks are invalid."""
        deck = Deck("Partial Deck")
        
        # Add only 10 cards
        for i in range(10):
            card = Mock(spec=Card)
            card.id = i
            card.name = f"Card_{i}"
            card.is_pokemon = True
            card.is_basic = True
            card.is_trainer = False
            
            deck.add_card(card)
        
        is_valid, message = deck.is_valid()
        
        assert is_valid is False
        assert "must contain 20 cards" in message
        assert "Has: 10" in message


@pytest.mark.unit
class TestBasicPokemonRequirement:
    """Test the Basic Pokemon requirement rule."""
    
    def test_deck_needs_basic_pokemon(self, sample_trainer_card, sample_evolved_pokemon):
        """Test that decks must contain at least one Basic Pokemon."""
        deck = Deck("No Basic Pokemon Deck")
        
        # Fill deck with non-basic cards (trainers and evolved pokemon)
        cards_added = 0
        for i in range(20):
            if i < 10:
                # Add trainer cards
                card = Mock(spec=Card)
                card.id = i
                card.name = f"Trainer_{i}"
                card.is_pokemon = False
                card.is_basic = False
                card.is_trainer = True
            else:
                # Add evolved Pokemon (not basic)
                card = Mock(spec=Card)
                card.id = i
                card.name = f"Evolved_{i}"
                card.is_pokemon = True
                card.is_basic = False  # Not basic
                card.is_trainer = False
            
            deck.add_card(card)
            cards_added += 1
        
        assert len(deck.cards) == 20
        
        is_valid, message = deck.is_valid()
        
        assert is_valid is False
        assert "at least one Basic Pokémon" in message

    def test_deck_with_basic_pokemon_valid(self, sample_basic_pokemon, sample_trainer_card):
        """Test that deck with Basic Pokemon is valid (regarding Basic Pokemon rule)."""
        deck = Deck("Valid Basic Pokemon Deck")
        
        # Add at least one basic Pokemon
        deck.add_card(sample_basic_pokemon)
        
        # Fill rest with trainer cards
        for i in range(19):
            card = Mock(spec=Card)
            card.id = i + 10
            card.name = f"Trainer_{i}"
            card.is_pokemon = False
            card.is_basic = False
            card.is_trainer = True
            
            deck.add_card(card)
        
        assert len(deck.cards) == 20
        
        is_valid, message = deck.is_valid()
        
        # Should be valid now (has Basic Pokemon and correct card count)
        assert is_valid is True
        assert message == ""

    def test_multiple_basic_pokemon_allowed(self):
        """Test that multiple Basic Pokemon are allowed."""
        deck = Deck("Multiple Basic Pokemon Deck")
        
        # Add multiple different Basic Pokemon
        for i in range(5):
            card = Mock(spec=Card)
            card.id = i
            card.name = f"BasicMon_{i}"
            card.is_pokemon = True
            card.is_basic = True
            card.is_trainer = False
            
            deck.add_card(card)
        
        # Fill rest with trainer cards
        for i in range(15):
            card = Mock(spec=Card)
            card.id = i + 10
            card.name = f"Trainer_{i}"
            card.is_pokemon = False
            card.is_basic = False
            card.is_trainer = True
            
            deck.add_card(card)
        
        is_valid, message = deck.is_valid()
        
        assert is_valid is True
        assert message == ""


@pytest.mark.unit
class TestCardRemoval:
    """Test card removal functionality."""
    
    def test_remove_card_by_id(self, sample_basic_pokemon, sample_different_pokemon):
        """Test removing cards by ID."""
        deck = Deck("Remove Test Deck")
        
        deck.add_card(sample_basic_pokemon)
        deck.add_card(sample_different_pokemon)
        
        assert len(deck.cards) == 2
        assert sample_basic_pokemon.name in deck.card_counts
        
        # Remove first card
        result = deck.remove_card(sample_basic_pokemon)
        
        assert result is True
        assert len(deck.cards) == 1
        assert sample_basic_pokemon.name not in deck.card_counts
        assert sample_different_pokemon.name in deck.card_counts

    def test_remove_card_by_name(self):
        """Test removing cards by name."""
        deck = Deck("Remove by Name Test")
        
        # Add two cards with same name
        pikachu1 = Mock(spec=Card)
        pikachu1.id = 1
        pikachu1.name = "Pikachu"
        pikachu1.is_pokemon = True
        pikachu1.is_basic = True
        pikachu1.is_trainer = False
        
        pikachu2 = Mock(spec=Card)
        pikachu2.id = 2
        pikachu2.name = "Pikachu"
        pikachu2.is_pokemon = True
        pikachu2.is_basic = True
        pikachu2.is_trainer = False
        
        deck.add_card(pikachu1)
        deck.add_card(pikachu2)
        
        assert deck.card_counts["Pikachu"] == 2
        
        # Remove one by name
        result = deck.remove_card_by_name("Pikachu")
        
        assert result is True
        assert deck.card_counts["Pikachu"] == 1
        assert len(deck.cards) == 1

    def test_remove_nonexistent_card(self, sample_basic_pokemon):
        """Test removing a card that doesn't exist in deck."""
        deck = Deck("Empty Deck")
        
        # Try to remove from empty deck
        result = deck.remove_card(sample_basic_pokemon)
        
        assert result is False
        assert len(deck.cards) == 0

    def test_clear_deck(self, sample_basic_pokemon, sample_different_pokemon):
        """Test clearing all cards from deck."""
        deck = Deck("Clear Test Deck")
        
        deck.add_card(sample_basic_pokemon)
        deck.add_card(sample_different_pokemon)
        
        assert len(deck.cards) == 2
        assert len(deck.card_counts) == 2
        
        deck.clear()
        
        assert len(deck.cards) == 0
        assert len(deck.card_counts) == 0
        assert len(deck.cover_card_ids) == 0


@pytest.mark.unit
class TestDeckTypes:
    """Test deck type determination and management."""
    
    def test_determine_deck_types_single_type(self):
        """Test deck type determination with single energy type."""
        deck = Deck("Lightning Deck")
        
        # Add only Lightning-type Pokemon
        for i in range(10):
            card = Mock(spec=Card)
            card.id = i
            card.name = f"LightningMon_{i}"
            card.energy_type = "Lightning"
            card.is_pokemon = True
            card.is_basic = True if i < 3 else False
            card.is_trainer = False
            
            deck.add_card(card)
        
        deck_types = deck.determine_deck_types()
        
        assert "Lightning" in deck_types
        assert len([t for t in deck_types if t != "Colorless"]) == 1  # Only Lightning (plus maybe Colorless)

    def test_determine_deck_types_multiple_types(self):
        """Test deck type determination with multiple energy types."""
        deck = Deck("Multi-Type Deck")
        
        # Add Lightning-type Pokemon
        for i in range(5):
            card = Mock(spec=Card)
            card.id = i
            card.name = f"LightningMon_{i}"
            card.energy_type = "Lightning"
            card.is_pokemon = True
            card.is_basic = True
            card.is_trainer = False
            
            deck.add_card(card)
        
        # Add Fire-type Pokemon
        for i in range(5, 10):
            card = Mock(spec=Card)
            card.id = i
            card.name = f"FireMon_{i}"
            card.energy_type = "Fire"
            card.is_pokemon = True
            card.is_basic = True
            card.is_trainer = False
            
            deck.add_card(card)
        
        deck_types = deck.determine_deck_types()
        
        assert "Lightning" in deck_types
        assert "Fire" in deck_types

    def test_set_deck_types_manually(self):
        """Test manually setting deck types."""
        deck = Deck("Manual Types Deck")
        
        custom_types = ["Fire", "Water", "Lightning"]
        deck.set_deck_types(custom_types)
        
        assert deck.deck_types == custom_types

    def test_get_pokemon_count(self):
        """Test counting Pokemon cards in deck."""
        deck = Deck("Pokemon Count Test")
        
        # Add 3 Pokemon
        for i in range(3):
            card = Mock(spec=Card)
            card.id = i
            card.name = f"Pokemon_{i}"
            card.is_pokemon = True
            card.is_basic = True
            card.is_trainer = False
            
            deck.add_card(card)
        
        # Add 2 Trainers
        for i in range(3, 5):
            card = Mock(spec=Card)
            card.id = i
            card.name = f"Trainer_{i}"
            card.is_pokemon = False
            card.is_basic = False
            card.is_trainer = True
            
            deck.add_card(card)
        
        assert deck.get_pokemon_count() == 3
        assert deck.get_trainer_count() == 2


@pytest.mark.unit
class TestDeckValidationEdgeCases:
    """Test edge cases in deck validation."""
    
    def test_deck_with_exactly_max_copies(self):
        """Test deck with exactly maximum copies of cards."""
        deck = Deck("Max Copies Test")
        
        # Add exactly 10 different cards, 2 copies each (20 total)
        for i in range(10):
            # First copy
            card1 = Mock(spec=Card)
            card1.id = i * 2
            card1.name = f"Card_{i}"
            card1.is_pokemon = True
            card1.is_basic = True
            card1.is_trainer = False
            
            # Second copy
            card2 = Mock(spec=Card)
            card2.id = i * 2 + 1
            card2.name = f"Card_{i}"  # Same name
            card2.is_pokemon = True
            card2.is_basic = True
            card2.is_trainer = False
            
            deck.add_card(card1)
            deck.add_card(card2)
        
        assert len(deck.cards) == 20
        assert all(count == 2 for count in deck.card_counts.values())
        
        is_valid, message = deck.is_valid()
        assert is_valid is True

    def test_validation_with_excess_copies_in_card_counts(self):
        """Test validation detects excess copies even if artificially created."""
        deck = Deck("Excess Copies Test")
        
        # Manually create invalid state (this shouldn't happen in normal usage)
        card = Mock(spec=Card)
        card.id = 1
        card.name = "Pikachu"
        card.is_pokemon = True
        card.is_basic = True
        card.is_trainer = False
        
        # Add normally
        deck.add_card(card)
        
        # Artificially inflate count (simulating a bug)
        deck.card_counts["Pikachu"] = 3  # More than MAX_COPIES
        
        is_valid, message = deck.is_valid()
        
        assert is_valid is False
        assert "Too many copies of Pikachu (3/2)" in message

    def test_deck_name_case_insensitive_storage(self):
        """Test that deck names are stored in lowercase for querying."""
        deck = Deck("My AWESOME Deck")
        
        assert deck.name == "My AWESOME Deck"
        assert deck.name_lowercase == "my awesome deck"

    def test_cover_card_ids_management(self):
        """Test cover card IDs are managed properly."""
        deck = Deck("Cover Cards Test")
        
        card = Mock(spec=Card)
        card.id = 1
        card.name = "Pikachu"
        card.is_pokemon = True
        card.is_basic = True
        card.is_trainer = False
        
        deck.add_card(card)
        
        # Add card ID to cover cards
        deck.cover_card_ids = ["1"]
        
        # Remove the card
        result = deck.remove_card(card)
        
        assert result is True
        # Cover card ID should be removed automatically
        assert "1" not in deck.cover_card_ids