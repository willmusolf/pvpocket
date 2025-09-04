import React from 'react';
import type { BattleCard } from '../../types/battle';
import './HandCards.css';

interface HandCardsProps {
  cards: BattleCard[];
  isOpponent: boolean;
  onCardClick?: (card: BattleCard, index: number) => void;
  maxDisplayCards?: number;
  selectedCardIndex?: number | null;
  gameState?: any; // For determining card playability
  canPlayCards?: boolean; // Whether cards can be played (battle has started or sandbox mode)
}

const HandCards: React.FC<HandCardsProps> = ({
  cards,
  isOpponent,
  onCardClick,
  maxDisplayCards = 10,
  selectedCardIndex = null,
  gameState = null,
  canPlayCards = true
}) => {
  const cardCount = cards.length;
  const displayCards = cards.slice(0, maxDisplayCards);
  const hasOverflow = cardCount > maxDisplayCards;

  const getCardSpacing = (cardCount: number) => {
    // Create a proper fan spread where each card is clearly visible
    // Responsive card and container widths
    const containerWidth = window.innerWidth <= 900 ? 300 : window.innerWidth <= 1200 ? 350 : 400;
    const cardWidth = window.innerWidth <= 900 ? 50 : window.innerWidth <= 1200 ? 55 : 60;
    
    if (cardCount <= 1) return 0;
    
    // Calculate the total available space for spacing
    const availableSpace = containerWidth - cardWidth; // Space available for all cards except the last one
    
    // Distribute space evenly between cards, but ensure minimum visibility
    const idealSpacing = availableSpace / (cardCount - 1);
    const minVisiblePortion = cardWidth * 0.45; // 45% of card should be visible
    const maxOverlap = cardWidth - minVisiblePortion;
    const maxSpacing = maxOverlap;
    
    // Return the smaller of ideal spacing or max allowed spacing
    return Math.min(idealSpacing, maxSpacing);
  };

  const spacing = getCardSpacing(cardCount);

  const getCardPlayability = (card: BattleCard, index: number): 'playable' | 'evolution' | 'disabled' => {
    // Opponent cards are never playable by player, and cards can't be played if battle hasn't started
    if (isOpponent || !gameState || !canPlayCards) return 'disabled';
    
    // Energy cards are always playable if we haven't attached energy this turn
    if (card.card_type === 'Energy') {
      const currentPlayer = gameState.players?.[0];
      if (currentPlayer && !currentPlayer.energy_attached_this_turn) {
        return 'playable';
      }
      return 'disabled';
    }
    
    // Pokemon cards
    if (card.card_type === 'Pokemon') {
      const currentPlayer = gameState.players?.[0];
      if (!currentPlayer) return 'disabled';
      
      // Basic Pokemon (evolution_stage 0) can be played if active slot is empty or bench has space
      if (!card.evolution_stage || card.evolution_stage === 0) {
        const hasActiveSlot = !!currentPlayer.active_pokemon;
        const benchSpots = currentPlayer.bench?.filter(spot => !!spot).length || 0;
        
        if (!hasActiveSlot || benchSpots < 3) {
          return 'playable';
        }
      } else {
        // Evolution cards - check if we have a matching Pokemon to evolve
        const evolvesFrom = card.evolves_from;
        if (evolvesFrom) {
          // Check active Pokemon
          if (currentPlayer.active_pokemon?.card.name === evolvesFrom) {
            return 'evolution';
          }
          // Check bench Pokemon
          const canEvolve = currentPlayer.bench?.some(pokemon => 
            pokemon && pokemon.card.name === evolvesFrom
          );
          if (canEvolve) {
            return 'evolution';
          }
        }
      }
    }
    
    return 'disabled';
  };

  const handleCardClick = (card: BattleCard, index: number) => {
    if (onCardClick) {
      onCardClick(card, index);
    }
  };

  if (cardCount === 0) {
    return (
      <div className={`hand-cards empty ${isOpponent ? 'opponent' : 'player'}`}>
        <div className="empty-hand-message">No cards in hand</div>
      </div>
    );
  }

  // Calculate total width needed and center the cards
  const containerWidth = window.innerWidth <= 900 ? 300 : window.innerWidth <= 1200 ? 350 : 400;
  const cardWidth = window.innerWidth <= 900 ? 50 : window.innerWidth <= 1200 ? 55 : 60;
  const totalHandWidth = Math.max((cardCount - 1) * spacing + cardWidth, cardWidth); // Ensure minimum width for single card
  const centerOffset = Math.max((containerWidth - totalHandWidth) / 2, 0); // Center in container, ensure non-negative

  return (
    <div className={`hand-cards ${isOpponent ? 'opponent' : 'player'}`}>
      <div 
        className="hand-container"
        style={{
          '--card-spacing': `${spacing}px`,
          '--center-offset': `${centerOffset}px`
        } as React.CSSProperties}
      >
        {displayCards.map((card, index) => {
          const playability = getCardPlayability(card, index);
          const isSelected = selectedCardIndex === index;
          
          return (
            <div
              key={`${card.id}-${index}`}
              className={`hand-card ${isOpponent ? 'face-down' : 'face-up'} ${playability} ${isSelected ? 'selected' : ''}`}
              onClick={() => !isOpponent && handleCardClick(card, index)}
              style={{
                zIndex: index,
                transform: `translateX(${centerOffset + (index * spacing)}px)`,
                '--card-index': index
              } as React.CSSProperties}
            >
              {isOpponent ? (
                // Face-down card back for opponent
                <div className="card-back">
                  <div className="card-back-pattern"></div>
                </div>
              ) : (
                // Face-up card for player
                <div className="card-front" data-type={card.energy_type?.toLowerCase()}>
                  {card.firebase_image_url ? (
                    // Show actual card image if available
                    <div className="card-image-container">
                      <img 
                        src={card.firebase_image_url} 
                        alt={card.name}
                        className="card-image"
                        onError={(e) => {
                          // Fallback to text display if image fails to load
                          const target = e.target as HTMLImageElement;
                          target.style.display = 'none';
                          const fallback = target.nextElementSibling as HTMLElement;
                          if (fallback) fallback.style.display = 'flex';
                        }}
                      />
                      <div className="card-text-fallback" style={{display: 'none'}}>
                        <div className="card-header">
                          <span className="card-name">{card.name}</span>
                          <span className="card-cost">
                            {card.card_type === 'Energy' ? '⚡' : (card.retreat_cost || 0)}
                          </span>
                        </div>
                        <div className="card-type">{card.card_type}</div>
                        {card.hp && <div className="card-hp">{card.hp} HP</div>}
                      </div>
                    </div>
                  ) : (
                    // Fallback to text display if no image URL
                    <>
                      <div className="card-header">
                        <span className="card-name">{card.name}</span>
                        <span className="card-cost">
                          {card.card_type === 'Energy' ? '⚡' : (card.retreat_cost || 0)}
                        </span>
                      </div>
                      <div className="card-type">{card.card_type}</div>
                      {card.hp && <div className="card-hp">{card.hp} HP</div>}
                    </>
                  )}
                  {playability === 'evolution' && (
                    <div className="evolution-indicator">⬆️</div>
                  )}
                </div>
              )}
            </div>
          );
        })}
        
        {hasOverflow && (
          <div className="overflow-indicator" style={{
            transform: `translateX(${centerOffset + (displayCards.length * spacing)}px)`,
            zIndex: displayCards.length
          }}>
            +{cardCount - maxDisplayCards}
          </div>
        )}
      </div>
    </div>
  );
};

export default HandCards;