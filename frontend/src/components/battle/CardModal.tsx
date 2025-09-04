import React from 'react';
import type { BattlePokemon } from '../../types/battle';
import './CardModal.css';

interface CardModalProps {
  pokemon: BattlePokemon | null;
  isOpen: boolean;
  onClose: () => void;
  onAbilityClick?: (abilityIndex: number) => void;
  onAttackClick?: (attackIndex: number) => void;
  showInteractiveElements?: boolean;
  isOpponent?: boolean;
  isSandboxMode?: boolean;
  onSandboxAction?: (action: string, params: any) => void;
  playerIndex?: number;
  pokemonPosition?: string; // 'active' or bench index
}

const CardModal: React.FC<CardModalProps> = ({
  pokemon,
  isOpen,
  onClose,
  onAbilityClick,
  onAttackClick,
  showInteractiveElements = false,
  isOpponent = false,
  isSandboxMode = false,
  onSandboxAction,
  playerIndex = 0,
  pokemonPosition = 'active'
}) => {
  if (!isOpen || !pokemon) return null;

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

  const getEnergyIconUrl = (energyType: string) => {
    // Map energy types to CDN URLs
    const iconMap: Record<string, string> = {
      'Grass': 'https://cdn.pvpocket.xyz/energy_icons/grass.png',
      'Fire': 'https://cdn.pvpocket.xyz/energy_icons/fire.png',
      'Water': 'https://cdn.pvpocket.xyz/energy_icons/water.png',
      'Lightning': 'https://cdn.pvpocket.xyz/energy_icons/electric.png',
      'Psychic': 'https://cdn.pvpocket.xyz/energy_icons/psychic.png',
      'Fighting': 'https://cdn.pvpocket.xyz/energy_icons/fighting.png',
      'Darkness': 'https://cdn.pvpocket.xyz/energy_icons/darkness.png',
      'Metal': 'https://cdn.pvpocket.xyz/energy_icons/metal.png',
      'Fairy': 'https://cdn.pvpocket.xyz/energy_icons/fairy.png',
      'Dragon': 'https://cdn.pvpocket.xyz/energy_icons/dragon.png',
      'Colorless': 'https://cdn.pvpocket.xyz/energy_icons/colorless.png'
    };
    return iconMap[energyType] || iconMap['Colorless'];
  };

  const handleSandboxAction = (actionType: string, params: any = {}) => {
    if (onSandboxAction) {
      // Enhanced targeting for energy attachment
      let actionData = {
        player_id: playerIndex,
        target: pokemonPosition,
        ...params
      };
      
      // Special handling for energy attachment to ensure proper targeting
      if (actionType === 'attach_energy') {
        actionData = {
          ...actionData,
          target_player: playerIndex,
          target_position: pokemonPosition,
          energy_type: params.energy_type
        };
        console.log(`🔋 MODAL: Energy attachment targeting Player ${playerIndex} (${['Player 1', 'Player 2'][playerIndex]}) at ${pokemonPosition}`, actionData);
      }
      
      onSandboxAction(actionType, actionData);
    }
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

  const canUseAbility = (abilityIndex: number) => {
    // Basic check - can be enhanced with actual game logic
    return !isKnocked && !isOpponent;
  };

  const canUseAttack = (attackIndex: number) => {
    // Basic check - can be enhanced with energy cost validation
    return !isKnocked && !isOpponent && attached_energy.length > 0;
  };

  return (
    <div className="card-modal-overlay" onClick={onClose}>
      <div className="card-modal-container" onClick={(e) => e.stopPropagation()}>
        <button className="card-modal-close" onClick={onClose}>×</button>
        
        <div className="card-modal-content">
          {/* Left side - Card Image */}
          <div className="card-modal-image-section">
            <div className="card-modal-image">
              {card.firebase_image_url ? (
                <img 
                  src={card.firebase_image_url} 
                  alt={card.name}
                  loading="lazy"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                    target.nextElementSibling?.classList.remove('hidden');
                  }}
                />
              ) : null}
              
              {/* Fallback energy indicator */}
              <div 
                className={`modal-energy-indicator ${card.firebase_image_url ? 'hidden' : ''}`}
                style={{ backgroundColor: getEnergyTypeColor(card.energy_type) }}
              >
                <span className="energy-symbol">{card.energy_type.charAt(0)}</span>
                <span className="energy-name">{card.energy_type}</span>
              </div>

              {/* Status Effects Overlay */}
              {status_conditions.length > 0 && (
                <div className="modal-status-overlay">
                  {status_conditions.map((condition, index) => (
                    <div 
                      key={index} 
                      className={`modal-status-effect ${condition.condition}`}
                      title={`${condition.condition} (${condition.turns_remaining || '∞'} turns)`}
                    >
                      <span className="status-icon">{getStatusIcon(condition.condition)}</span>
                      <span className="status-name">{condition.condition}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Damage Counter */}
              {isDamaged && (
                <div className="modal-damage-counter">
                  <span className="damage-amount">-{damage_taken}</span>
                  <span className="damage-label">DMG</span>
                </div>
              )}

              {/* Knocked Out Overlay */}
              {isKnocked && (
                <div className="modal-ko-overlay">
                  <div className="ko-text">KNOCKED OUT</div>
                </div>
              )}
            </div>
          </div>

          {/* Right side - Card Details */}
          <div className="card-modal-details-section">
            <div className="card-modal-header">
              <h2 className="card-name">{card.name} {card.is_ex ? 'ex' : ''}</h2>
              <div className="card-type-info">
                <span className="card-type">{card.card_type}</span>
                {card.evolution_stage !== null && (
                  <span className="evolution-stage">Stage {card.evolution_stage}</span>
                )}
              </div>
            </div>

            {/* HP Section */}
            <div className="hp-section">
              <div className="hp-display">
                <span className="hp-current">{current_hp}</span>
                <span className="hp-separator">/</span>
                <span className="hp-max">{max_hp}</span>
                <span className="hp-label">HP</span>
              </div>
              <div className="hp-bar-container">
                <div 
                  className="hp-bar-fill"
                  style={{ 
                    width: `${hpPercentage}%`,
                    backgroundColor: getHPBarColor()
                  }}
                />
              </div>
            </div>

            {/* Energy Section */}
            {attached_energy.length > 0 && (
              <div className="energy-section">
                <h3>Attached Energy ({attached_energy.length})</h3>
                <div className="energy-grid">
                  {attached_energy.map((energy, index) => (
                    <div 
                      key={index}
                      className="energy-card-icon"
                      title={energy}
                    >
                      <img 
                        src={getEnergyIconUrl(energy)} 
                        alt={energy}
                        className="energy-icon"
                        onError={(e) => {
                          // Fallback to colored circle with letter
                          const target = e.target as HTMLImageElement;
                          target.style.display = 'none';
                          if (target.nextElementSibling) {
                            (target.nextElementSibling as HTMLElement).style.display = 'flex';
                          }
                        }}
                      />
                      <div 
                        className="energy-fallback"
                        style={{ 
                          backgroundColor: getEnergyTypeColor(energy),
                          display: 'none'
                        }}
                      >
                        {energy.charAt(0)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Abilities Section */}
            {card.abilities && card.abilities.length > 0 && (
              <div className="abilities-section">
                <h3>Abilities</h3>
                <div className="abilities-list">
                  {card.abilities.map((ability, index) => (
                    <div key={index} className="ability-item">
                      <div className="ability-header">
                        <span className="ability-name">🔮 {ability.name}</span>
                        {ability.type && (
                          <span className="ability-type">({ability.type})</span>
                        )}
                      </div>
                      <p className="ability-description">{ability.effect_text}</p>
                      {showInteractiveElements && canUseAbility(index) && (
                        <button
                          className="ability-action-btn"
                          onClick={() => onAbilityClick?.(index)}
                          disabled={!canUseAbility(index)}
                        >
                          Use Ability
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Attacks Section */}
            {card.attacks && card.attacks.length > 0 && (
              <div className="attacks-section">
                <h3>Attacks</h3>
                <div className="attacks-list">
                  {card.attacks.map((attack, index) => (
                    <div key={index} className="attack-item">
                      <div className="attack-header">
                        <span className="attack-name">{attack.name}</span>
                        <span className="attack-damage">{attack.damage}</span>
                      </div>
                      {attack.cost && (
                        <div className="energy-cost">
                          {attack.cost.map((cost, costIndex) => (
                            <div 
                              key={costIndex}
                              className="energy-cost-pip"
                              title={cost}
                            >
                              <img 
                                src={getEnergyIconUrl(cost)} 
                                alt={cost}
                                className="energy-cost-icon"
                                onError={(e) => {
                                  const target = e.target as HTMLImageElement;
                                  target.style.display = 'none';
                                  if (target.nextElementSibling) {
                                    (target.nextElementSibling as HTMLElement).style.display = 'flex';
                                  }
                                }}
                              />
                              <div 
                                className="energy-cost-fallback"
                                style={{ 
                                  backgroundColor: getEnergyTypeColor(cost),
                                  display: 'none'
                                }}
                              >
                                {cost.charAt(0)}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                      <p className="attack-description">{attack.effect_text}</p>
                      {showInteractiveElements && canUseAttack(index) && (
                        <button
                          className="attack-action-btn"
                          onClick={() => onAttackClick?.(index)}
                          disabled={!canUseAttack(index)}
                        >
                          Use Attack
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Sandbox Mode Controls */}
            {isSandboxMode && (
              <div className="sandbox-controls-section">
                <h3>🧪 Sandbox Controls</h3>
                <div className="sandbox-controls-grid">
                  <button
                    className="sandbox-btn attach-energy-btn"
                    onClick={() => handleSandboxAction('attach_energy', { energy_type: card.energy_type || 'Fire', amount: 1 })}
                    title="Attach 1 energy of this Pokemon's type"
                  >
                    ⚡ Attach Energy
                  </button>
                  
                  <div className="hp-control-group">
                    <input
                      type="range"
                      min="0"
                      max={max_hp}
                      value={current_hp}
                      className="hp-slider"
                      onChange={(e) => handleSandboxAction('set_hp', { hp: parseInt(e.target.value) })}
                      title={`Set HP (0-${max_hp})`}
                    />
                    <label className="hp-slider-label">HP: {current_hp}/{max_hp}</label>
                  </div>
                  
                  <select
                    className="status-selector"
                    defaultValue=""
                    onChange={(e) => {
                      if (e.target.value) {
                        handleSandboxAction('apply_status', { status: e.target.value });
                        e.target.value = ''; // Reset selector
                      }
                    }}
                  >
                    <option value="">Apply Status...</option>
                    <option value="asleep">😴 Sleep</option>
                    <option value="burned">🔥 Burn</option>
                    <option value="poisoned">☠️ Poison</option>
                    <option value="paralyzed">⚡ Paralysis</option>
                    <option value="confused">😵 Confusion</option>
                  </select>
                  
                  <button
                    className="sandbox-btn remove-btn"
                    onClick={() => handleSandboxAction('remove_pokemon', {})}
                    title="Remove this Pokemon from the game"
                  >
                    🗑️ Remove Pokemon
                  </button>
                </div>
              </div>
            )}

            {/* Additional Info */}
            <div className="card-info-section">
              {card.weakness && (
                <div className="weakness-info">
                  <strong>Weakness:</strong> {card.weakness}
                </div>
              )}
              {card.retreat_cost !== null && (
                <div className="retreat-cost-info">
                  <strong>Retreat Cost:</strong> {card.retreat_cost}
                </div>
              )}
              {card.rarity && (
                <div className="rarity-info">
                  <strong>Rarity:</strong> {card.rarity}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CardModal;