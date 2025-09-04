import React, { useState, useEffect } from 'react';
import './CardSearchPanel.css';

interface Card {
  id: number;
  name: string;
  card_type: string;
  energy_type: string;
  hp?: number;
  attacks?: any[];
  abilities?: any[];
  weakness?: string;
  retreat_cost?: number;
  evolution_stage?: number;
  evolves_from?: string;
  is_ex: boolean;
  rarity: string;
  set_name: string;
  firebase_image_url?: string;
}

interface CardSearchPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onCardPlace: (card: Card, position: string, benchIndex?: number, selectedPlayer?: number) => void;
  isSandboxMode: boolean;
}

const CardSearchPanel: React.FC<CardSearchPanelProps> = ({
  isOpen,
  onClose,
  onCardPlace,
  isSandboxMode
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Card[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedPlayer, setSelectedPlayer] = useState(0);

  useEffect(() => {
    if (searchQuery.length >= 2) {
      searchCards(searchQuery);
    } else {
      setSearchResults([]);
    }
  }, [searchQuery]);

  const searchCards = async (query: string) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/dev/cards/search?q=${encodeURIComponent(query)}&limit=20`);
      const data = await response.json();
      
      if (data.success) {
        setSearchResults(data.cards || []);
      } else {
        console.error('Card search failed:', data.error);
        setSearchResults([]);
      }
    } catch (error) {
      console.error('Error searching cards:', error);
      setSearchResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCardPlace = (card: Card, position: string, benchIndex?: number) => {
    onCardPlace(card, position, benchIndex, selectedPlayer);
  };

  const getCardTypeIcon = (cardType: string) => {
    if (cardType.includes('Pokémon')) return '🎯';
    if (cardType.includes('Trainer')) return '👤';
    if (cardType.includes('Energy')) return '⚡';
    return '📄';
  };

  const getEnergyIcon = (energyType: string) => {
    const icons: Record<string, string> = {
      'Grass': '🌿',
      'Fire': '🔥',
      'Water': '💧',
      'Lightning': '⚡',
      'Psychic': '🔮',
      'Fighting': '👊',
      'Darkness': '🌑',
      'Metal': '⚙️',
      'Fairy': '🧚',
      'Dragon': '🐉',
      'Colorless': '⭐'
    };
    return icons[energyType] || '❓';
  };

  if (!isOpen) return null;

  return (
    <div className="card-search-overlay" onClick={onClose}>
      <div className="card-search-panel" onClick={(e) => e.stopPropagation()}>
        <div className="search-header">
          <h3>🔍 Card Search</h3>
          <button className="search-close-btn" onClick={onClose}>×</button>
        </div>

        <div className="search-controls">
          <input
            type="text"
            placeholder="Search for cards..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
            autoFocus
          />
          
          {isSandboxMode && (
            <div className="player-selector">
              <label>Target Player:</label>
              <select
                value={selectedPlayer}
                onChange={(e) => setSelectedPlayer(Number(e.target.value))}
                className="player-select"
              >
                <option value={0}>Player 1</option>
                <option value={1}>Player 2</option>
              </select>
            </div>
          )}
        </div>

        <div className="search-results">
          {isLoading && (
            <div className="loading-indicator">
              <div className="spinner"></div>
              <span>Searching...</span>
            </div>
          )}

          {!isLoading && searchQuery.length >= 2 && searchResults.length === 0 && (
            <div className="no-results">
              <span>No cards found for "{searchQuery}"</span>
            </div>
          )}

          {!isLoading && searchResults.map((card) => (
            <div key={card.id} className="search-result-item">
              <div className="card-preview">
                <div className="card-icon">
                  {card.firebase_image_url ? (
                    <img 
                      src={card.firebase_image_url} 
                      alt={card.name}
                      className="card-thumbnail"
                      loading="lazy"
                    />
                  ) : (
                    <div className="card-placeholder">
                      <span className="card-type-icon">{getCardTypeIcon(card.card_type)}</span>
                      <span className="energy-icon">{getEnergyIcon(card.energy_type)}</span>
                    </div>
                  )}
                </div>
                
                <div className="card-info">
                  <div className="card-name-line">
                    <span className="card-name">{card.name} {card.is_ex ? 'ex' : ''}</span>
                    {card.hp && <span className="card-hp">{card.hp} HP</span>}
                  </div>
                  
                  <div className="card-details">
                    <span className="card-type">{card.card_type}</span>
                    <span className="card-set">{card.set_name}</span>
                    {card.rarity && <span className="card-rarity">{card.rarity}</span>}
                  </div>
                  
                  {card.attacks && card.attacks.length > 0 && (
                    <div className="card-attacks-preview">
                      {card.attacks.slice(0, 2).map((attack, index) => (
                        <div key={index} className="attack-preview">
                          <div className="attack-name-damage">
                            <strong>{attack.name}</strong> ({attack.damage || '0'})
                          </div>
                          {attack.effect && (
                            <div className="attack-effect">
                              {attack.effect}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="placement-buttons">
                <button
                  className="place-btn hand-btn"
                  onClick={() => handleCardPlace(card, 'hand')}
                  title="Add to hand"
                >
                  ✋ Hand
                </button>
                
                {card.card_type.includes('Pokémon') && (
                  <>
                    <button
                      className="place-btn active-btn"
                      onClick={() => handleCardPlace(card, 'active')}
                      title="Place as active Pokemon"
                    >
                      🎯 Active
                    </button>
                    
                    <div className="bench-buttons">
                      {[0, 1, 2].map((benchIndex) => (
                        <button
                          key={benchIndex}
                          className="place-btn bench-btn"
                          onClick={() => handleCardPlace(card, 'bench', benchIndex)}
                          title={`Place on bench slot ${benchIndex + 1}`}
                        >
                          Bench {benchIndex + 1}
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>

        {searchQuery.length < 2 && !isLoading && (
          <div className="search-hint">
            <span>Type at least 2 characters to search for cards</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default CardSearchPanel;