import React, { useState, useCallback } from 'react';
import type { BattlePokemon } from '../../types/battle';
import { imageCache } from '../../utils/imageCache';
import './PokemonCard.css';

interface PokemonCardProps {
  pokemon: BattlePokemon | null;
  isOpponent?: boolean;
  isSelected?: boolean;
  onClick?: () => void;
  onAbilityClick?: (abilityIndex: number) => void;
  onAttackClick?: (attackIndex: number) => void;
  showInteractiveElements?: boolean;
  size?: 'small' | 'medium' | 'large';
  onCardClick?: () => void;
}

const PokemonCard: React.FC<PokemonCardProps> = ({
  pokemon,
  isOpponent = false,
  isSelected = false,
  onClick,
  onAbilityClick,
  onAttackClick,
  showInteractiveElements = false,
  size = 'small',
  onCardClick
}) => {
  const [imageState, setImageState] = useState<'loading' | 'loaded' | 'error'>('loading');
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  // Add null check for pokemon
  if (!pokemon || !pokemon.card) {
    return (
      <div className={`pokemon-card empty size-${size}`}>
        <div className="empty-card">No Pokemon</div>
      </div>
    );
  }

  // Initialize image URL when component mounts or card changes
  React.useEffect(() => {
    const url = pokemon.card.firebase_image_url;
    if (url && url.trim() !== '') {
      setImageUrl(url);
      
      // Check cache first
      if (imageCache.isLoaded(url)) {
        setImageState('loaded');
      } else if (imageCache.hasFailed(url)) {
        setImageState('error');
      } else {
        setImageState('loading');
      }
    } else {
      setImageUrl(null);
      setImageState('error');
    }
  }, [pokemon.card.firebase_image_url]);

  const { card, current_hp, max_hp, status_conditions, attached_energy, damage_taken } = pokemon;
  
  const hpPercentage = (current_hp / max_hp) * 100;
  const isDamaged = damage_taken > 0;
  const isKnocked = current_hp <= 0;

  const getHPBarColor = () => {
    if (hpPercentage > 60) return '#4ade80'; // green
    if (hpPercentage > 30) return '#fbbf24'; // yellow
    return '#ef4444'; // red
  };

  const getEnergyTypeColor = (energyType: string) => {
    const colors: Record<string, string> = {
      'Grass': '#16a34a',
      'Fire': '#dc2626', 
      'Water': '#2563eb',
      'Lightning': '#eab308',
      'Psychic': '#7c3aed',
      'Fighting': '#ea580c',
      'Darkness': '#374151',
      'Metal': '#6b7280',
      'Fairy': '#ec4899',
      'Dragon': '#7c2d12',
      'Colorless': '#9ca3af'
    };
    return colors[energyType] || '#9ca3af';
  };

  const handleCardClick = () => {
    if (onCardClick) {
      onCardClick();
    } else if (onClick) {
      onClick();
    }
  };

  const handleImageLoad = useCallback(() => {
    setImageState('loaded');
    if (imageUrl) {
      imageCache.markLoaded(imageUrl);
    }
    if (process.env.NODE_ENV === 'development') {
      console.log(`✅ Image loaded: ${card.name}`);
    }
  }, [card.name, imageUrl]);

  const handleImageError = useCallback((e: React.SyntheticEvent<HTMLImageElement>) => {
    const target = e.target as HTMLImageElement;
    console.warn(`❌ Image failed: ${card.name} - ${imageUrl?.slice(-30)}`);
    setImageState('error');
    if (imageUrl) {
      imageCache.markFailed(imageUrl);
    }
    target.style.display = 'none';
  }, [card.name, imageUrl]);

  // Debug logging (only in development) - reduced frequency
  React.useEffect(() => {
    if (process.env.NODE_ENV === 'development' && Math.random() < 0.1) { // Only log 10% of renders
      console.log('PokemonCard state:', {
        name: card.name,
        imageState,
        hasUrl: !!imageUrl,
        energy_type: card.energy_type
      });
    }
  }, [card.name, imageState, imageUrl, card.energy_type]);

  return (
    <div 
      className={`pokemon-card ${isOpponent ? 'opponent' : 'player'} ${isSelected ? 'selected' : ''} ${isKnocked ? 'knocked-out' : ''} size-${size}`}
      onClick={handleCardClick}
      title={`Click to view ${card.name} details${imageState === 'error' ? ' (Image unavailable)' : ''}`}
    >
      {/* Card Image Container */}
      <div className="card-image-container">
        {/* Loading state indicator */}
        {imageState === 'loading' && imageUrl && (
          <div className="image-loading-state">
            <div className="loading-spinner"></div>
            <span className="loading-text">Loading...</span>
          </div>
        )}

        {/* Actual card image */}
        {imageUrl && (
          <img 
            src={imageUrl} 
            alt={card.name}
            loading="lazy"
            className={`card-main-image ${imageState === 'loaded' ? 'image-loaded' : ''}`}
            onError={handleImageError}
            onLoad={handleImageLoad}
            style={{ 
              display: imageState === 'error' ? 'none' : 'block',
              opacity: imageState === 'loaded' ? 1 : 0
            }}
          />
        )}
        
        {/* Fallback card display - shows when no image or image fails to load */}
        <div 
          className={`energy-type-indicator ${imageState === 'loaded' ? 'hidden' : ''}`}
          style={{ 
            backgroundColor: getEnergyTypeColor(card.energy_type),
            display: imageState === 'loading' && imageUrl ? 'none' : 'flex'
          }}
        >
          <div className="card-content">
            <span className="energy-symbol">{card.energy_type.charAt(0)}</span>
            <span className="card-name">{card.name}</span>
            <span className="energy-name">{card.energy_type}</span>
            {card.hp && <span className="hp-display">HP: {card.hp}</span>}
          </div>
          {imageState === 'error' && !imageUrl && (
            <div className="debug-info">
              <small>No image available</small>
            </div>
          )}
          {imageState === 'error' && imageUrl && (
            <div className="debug-info">
              <small>Image failed to load</small>
            </div>
          )}
        </div>
        
        {/* Subtle click overlay for visual feedback */}
        <div className="click-overlay">
          <span className="click-hint">👁️</span>
        </div>

        {/* Energy Counter Display */}
        {attached_energy && attached_energy.length > 0 && (
          <div className="energy-counter">
            <div className="energy-icons">
              {attached_energy.slice(0, 6).map((energyType, index) => (
                <span 
                  key={index}
                  className="energy-icon"
                  style={{ backgroundColor: getEnergyTypeColor(energyType) }}
                  title={`${energyType} Energy`}
                >
                  {energyType.charAt(0)}
                </span>
              ))}
              {attached_energy.length > 6 && (
                <span className="energy-overflow">+{attached_energy.length - 6}</span>
              )}
            </div>
            <div className="energy-count-text">
              {attached_energy.length} Energy
            </div>
          </div>
        )}

        {/* HP Bar and Status */}
        <div className="pokemon-stats">
          <div className="hp-bar">
            <div 
              className="hp-fill"
              style={{ 
                width: `${hpPercentage}%`,
                backgroundColor: getHPBarColor()
              }}
            />
            <div className="hp-text">{current_hp}/{max_hp}</div>
          </div>
          
          {status_conditions && status_conditions.length > 0 && (
            <div className="status-conditions">
              {status_conditions.map((condition, index) => (
                <span key={index} className="status-icon" title={condition}>
                  {getStatusIcon(condition)}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Only show KO overlay if knocked out */}
        {isKnocked && (
          <div className="knocked-out-overlay">
            <div className="ko-text">KO</div>
          </div>
        )}
      </div>
    </div>
  );
};

const getStatusIcon = (condition: string): string => {
  const icons: Record<string, string> = {
    'burned': '🔥',
    'poisoned': '☠️',
    'asleep': '😴',
    'paralyzed': '⚡',
    'confused': '😵'
  };
  return icons[condition] || '❓';
};

export default PokemonCard;