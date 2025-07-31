"""
Unit tests for Deck class core functionality.
"""

import pytest
import datetime
from Card import Card
from Deck import Deck


@pytest.mark.unit
class TestDeck:
    """Test Deck class functionality."""
    
    def test_deck_initialization(self):
        """Test basic deck creation."""
        deck = Deck(name="Test Deck", owner_id="user123")
        
        assert deck.name == "Test Deck"
        assert deck.name_lowercase == "test deck"
        assert deck.owner_id == "user123"
        assert len(deck.cards) == 0
        assert len(deck.card_counts) == 0
        assert deck.is_public is False
    
    def test_deck_name_property(self):
        """Test deck name property setter."""
        deck = Deck()
        deck.name = "New Deck Name"
        
        assert deck.name == "New Deck Name"
        assert deck.name_lowercase == "new deck name"
    
    def test_add_card_success(self):
        """Test successfully adding a card to deck."""
        deck = Deck()
        card = Card(id=1, name="Pikachu", energy_type="Lightning")
        
        result = deck.add_card(card)
        
        assert result is True
        assert len(deck.cards) == 1
        assert deck.card_counts["Pikachu"] == 1
        assert deck.cards[0].name == "Pikachu"
    
    def test_add_card_multiple_copies(self):
        """Test adding multiple copies of same card (up to limit)."""
        deck = Deck()
        card1 = Card(id=1, name="Pikachu", energy_type="Lightning")
        card2 = Card(id=2, name="Pikachu", energy_type="Lightning")
        
        # Add first copy
        result1 = deck.add_card(card1)
        assert result1 is True
        assert deck.card_counts["Pikachu"] == 1
        
        # Add second copy
        result2 = deck.add_card(card2)
        assert result2 is True
        assert deck.card_counts["Pikachu"] == 2
        assert len(deck.cards) == 2
    
    def test_add_card_max_copies_exceeded(self):
        """Test adding more than max copies of same card."""
        deck = Deck()
        card1 = Card(id=1, name="Pikachu", energy_type="Lightning")
        card2 = Card(id=2, name="Pikachu", energy_type="Lightning")
        card3 = Card(id=3, name="Pikachu", energy_type="Lightning")
        
        # Add first two copies (should succeed)
        deck.add_card(card1)
        deck.add_card(card2)
        
        # Try to add third copy (should fail)
        result = deck.add_card(card3)
        
        assert result is False
        assert deck.card_counts["Pikachu"] == 2
        assert len(deck.cards) == 2
    
    def test_add_card_deck_full(self):
        """Test adding card when deck is at max capacity."""
        deck = Deck()
        
        # Fill deck to capacity (20 cards)
        for i in range(20):
            card = Card(id=i, name=f"Card{i}", energy_type="Normal")
            deck.add_card(card)
        
        # Try to add 21st card
        extra_card = Card(id=21, name="Extra Card", energy_type="Normal")
        result = deck.add_card(extra_card)
        
        assert result is False
        assert len(deck.cards) == 20
    
    def test_remove_card_success(self):
        """Test successfully removing a card from deck."""
        deck = Deck()
        card1 = Card(id=1, name="Pikachu", energy_type="Lightning")
        card2 = Card(id=2, name="Charizard", energy_type="Fire")
        
        deck.add_card(card1)
        deck.add_card(card2)
        
        result = deck.remove_card(card1)
        
        assert result is True
        assert len(deck.cards) == 1
        assert "Pikachu" not in deck.card_counts
        assert deck.card_counts["Charizard"] == 1
    
    def test_remove_card_not_in_deck(self):
        """Test removing a card that's not in the deck."""
        deck = Deck()
        card1 = Card(id=1, name="Pikachu", energy_type="Lightning")
        card2 = Card(id=2, name="Charizard", energy_type="Fire")
        
        deck.add_card(card1)
        
        result = deck.remove_card(card2)
        
        assert result is False
        assert len(deck.cards) == 1
        assert deck.card_counts["Pikachu"] == 1
    
    def test_remove_card_by_name(self):
        """Test removing card by name."""
        deck = Deck()
        card1 = Card(id=1, name="Pikachu", energy_type="Lightning")
        card2 = Card(id=2, name="Pikachu", energy_type="Lightning")
        
        deck.add_card(card1)
        deck.add_card(card2)
        
        result = deck.remove_card_by_name("Pikachu")
        
        assert result is True
        assert len(deck.cards) == 1
        assert deck.card_counts["Pikachu"] == 1
    
    def test_clear_deck(self):
        """Test clearing all cards from deck."""
        deck = Deck()
        card1 = Card(id=1, name="Pikachu", energy_type="Lightning")
        card2 = Card(id=2, name="Charizard", energy_type="Fire")
        
        deck.add_card(card1)
        deck.add_card(card2)
        
        deck.clear()
        
        assert len(deck.cards) == 0
        assert len(deck.card_counts) == 0
    
    def test_is_valid_empty_deck(self):
        """Test validation of empty deck."""
        deck = Deck()
        
        is_valid, message = deck.is_valid()
        
        assert is_valid is False
        assert "20 cards" in message
        assert "Has: 0" in message
    
    def test_is_valid_incomplete_deck(self):
        """Test validation of incomplete deck."""
        deck = Deck()
        for i in range(10):  # Only 10 cards
            card = Card(id=i, name=f"Card{i}", energy_type="Normal")
            deck.add_card(card)
        
        is_valid, message = deck.is_valid()
        
        assert is_valid is False
        assert "20 cards" in message
        assert "Has: 10" in message
    
    def test_is_valid_too_many_copies(self):
        """Test validation fails with too many copies."""
        deck = Deck()
        
        # Fill deck with 20 cards including too many copies of one card
        # Add 17 different cards
        for i in range(17):
            card = Card(id=i, name=f"Card{i}", energy_type="Normal")
            deck.add_card(card)
        
        # Manually add 3 copies of Pikachu to bypass add_card validation
        for i in range(3):
            card = Card(id=17+i, name="Pikachu", energy_type="Lightning")
            deck.cards.append(card)
        deck.card_counts["Pikachu"] = 3
        
        is_valid, message = deck.is_valid()
        
        assert is_valid is False
        assert "Too many copies of Pikachu" in message
        assert "(3/2)" in message
    
    def test_cover_card_management(self):
        """Test cover card ID management."""
        deck = Deck()
        
        # Test adding cover card IDs
        result1 = deck.add_cover_card_id("1")
        result2 = deck.add_cover_card_id("2")
        result3 = deck.add_cover_card_id("3")
        result4 = deck.add_cover_card_id("4")  # Should fail (max 3)
        
        assert result1 is True
        assert result2 is True
        assert result3 is True
        assert result4 is False
        assert len(deck.cover_card_ids) == 3
        assert "1" in deck.cover_card_ids
        assert "2" in deck.cover_card_ids
        assert "3" in deck.cover_card_ids
        assert "4" not in deck.cover_card_ids
    
    def test_cover_card_removal(self):
        """Test removing cover card IDs."""
        deck = Deck()
        deck.add_cover_card_id("1")
        deck.add_cover_card_id("2")
        
        result1 = deck.remove_cover_card_id("1")
        result2 = deck.remove_cover_card_id("3")  # Not in list
        
        assert result1 is True
        assert result2 is False
        assert len(deck.cover_card_ids) == 1
        assert "2" in deck.cover_card_ids
        assert "1" not in deck.cover_card_ids
    
    def test_set_cover_card_ids_validation(self):
        """Test setting cover card IDs with validation."""
        deck = Deck()
        # Add actual cards to deck first
        card1 = Card(id=1, name="Pikachu", energy_type="Lightning")
        card2 = Card(id=2, name="Charizard", energy_type="Fire")
        deck.add_card(card1)
        deck.add_card(card2)
        
        # Set cover cards - only valid ones should be kept
        deck.set_cover_card_ids(["1", "2", "3"])  # "3" not in deck
        
        assert len(deck.cover_card_ids) == 2
        assert "1" in deck.cover_card_ids
        assert "2" in deck.cover_card_ids
        assert "3" not in deck.cover_card_ids