import React, { useState } from 'react';
import type { GameState, BattleUIState } from '../../types/battle';
import './GameControls.css';

interface GameControlsProps {
  gameState: GameState;
  uiState: BattleUIState;
  selectedPokemon: number | null;
  selectedHandCard: number | null;
  onAction: (action: any) => void;
  isPlayerTurn: boolean;
}

const GameControls: React.FC<GameControlsProps> = ({
  gameState,
  uiState,
  selectedPokemon,
  selectedHandCard,
  onAction,
  isPlayerTurn
}) => {
  const [selectedAttack, setSelectedAttack] = useState<number | null>(null);

  const player = gameState.players[0];
  const activePokemon = player.active_pokemon;
  const canAct = isPlayerTurn && uiState.mode === 'manual' && !uiState.loading;

  const handleAttack = (attackIndex: number) => {
    if (!canAct || !activePokemon || !activePokemon.card) return;
    
    onAction({
      type: 'attack',
      player_id: 0,
      data: {
        attack_index: attackIndex,
        target: 'opponent_active' // Default target
      }
    });
  };

  const handleSwitchPokemon = () => {
    if (!canAct || selectedPokemon === null || selectedPokemon === -1) return;
    
    onAction({
      type: 'switch',
      player_id: 0,
      data: {
        bench_index: selectedPokemon
      }
    });
  };

  const handlePassTurn = () => {
    if (!canAct) return;
    
    onAction({
      type: 'pass_turn',
      player_id: 0,
      data: {}
    });
  };

  const handleAttachEnergy = () => {
    if (!canAct || !activePokemon || player.energy_attached_this_turn) return;
    
    // For simplicity, attach the first available energy from hand
    const energyCard = player.hand.find(card => card.card_type === 'Energy');
    if (!energyCard) return;
    
    // Default to active Pokemon if no specific selection
    const targetPosition = selectedPokemon === -1 || selectedPokemon === null ? 'active' : `bench_${selectedPokemon}`;
    
    const targetData = {
      card_id: energyCard.id,
      target_player: 0, // Always attaching to current player (backend Player 0, display Player 1)
      target_position: targetPosition,
      energy_type: energyCard.energy_type
    };
    
    console.log('🔋 CONTROLS: Auto-attaching energy with explicit targeting to Player 0 (Player 1):', targetData);
    
    onAction({
      type: 'attach_energy',
      player_id: 0,
      data: targetData
    });
  };

  const handlePlayCard = () => {
    if (!canAct || selectedHandCard === null) return;
    
    const card = player.hand[selectedHandCard];
    if (!card) return;
    
    // Determine target based on card type and board state
    let targetSlot = 'active';
    if (card.card_type === 'Pokemon') {
      if (player.active_pokemon) {
        // Find first empty bench slot
        const emptyBenchIndex = player.bench?.findIndex(slot => !slot);
        if (emptyBenchIndex !== -1 && emptyBenchIndex !== undefined) {
          targetSlot = emptyBenchIndex;
        }
      }
    }
    
    onAction({
      type: 'play_pokemon',
      player_id: 0,
      data: {
        hand_index: selectedHandCard,
        target_slot: targetSlot
      }
    });
  };

  const handleAttachEnergyToSelected = () => {
    if (!canAct || selectedHandCard === null || selectedPokemon === null) return;
    
    const card = player.hand[selectedHandCard];
    if (!card || card.card_type !== 'Energy') return;
    
    // More explicit targeting with player context
    const targetData = {
      hand_index: selectedHandCard,
      target_player: 0, // Always attaching to current player (backend Player 0, display Player 1)
      target_position: selectedPokemon === -1 ? 'active' : `bench_${selectedPokemon}`,
      energy_type: card.energy_type
    };
    
    console.log('🔋 CONTROLS: Attaching energy with explicit targeting to Player 0 (Player 1):', targetData);
    
    onAction({
      type: 'attach_energy',
      player_id: 0,
      data: targetData
    });
  };

  const canAttack = (attackIndex: number): boolean => {
    if (!activePokemon || !activePokemon.card || !canAct) return false;
    
    const attack = activePokemon.card.attacks[attackIndex];
    if (!attack) return false;
    
    // Check if Pokemon has enough energy
    const requiredEnergy = attack.cost || [];
    const attachedEnergy = activePokemon.attached_energy || [];
    
    // Simple energy check - just count total energy for now
    return attachedEnergy.length >= requiredEnergy.length;
  };

  const getSelectedCard = () => {
    if (selectedHandCard === null) return null;
    return player.hand[selectedHandCard];
  };

  const canPlaySelectedCard = (): boolean => {
    const selectedCard = getSelectedCard();
    if (!selectedCard || !canAct) return false;
    
    if (selectedCard.card_type === 'Pokemon') {
      // Can play Pokemon if active slot is empty or bench has space
      const hasActiveSlot = !!player.active_pokemon;
      const benchSpots = player.bench?.filter(spot => !!spot).length || 0;
      return !hasActiveSlot || benchSpots < 3;
    }
    
    return false;
  };

  const canAttachSelectedEnergy = (): boolean => {
    const selectedCard = getSelectedCard();
    if (!selectedCard || !canAct) return false;
    
    return (
      selectedCard.card_type === 'Energy' &&
      !player.energy_attached_this_turn &&
      selectedPokemon !== null
    );
  };

  return (
    <div className="game-controls">
      <div className="controls-header">
        <h3>Game Controls</h3>
        <div className="turn-status">
          {isPlayerTurn ? (
            <span className="your-turn">Your Turn</span>
          ) : (
            <span className="opponent-turn">Opponent's Turn</span>
          )}
        </div>
      </div>

      {/* Battle Phase Info */}
      <div className="phase-info">
        <div className="current-phase">
          Phase: <span className="phase-name">{gameState.phase}</span>
        </div>
        <div className="turn-number">
          Turn: {gameState.current_turn}
        </div>
      </div>

      {/* Hand Card Actions */}
      {uiState.mode === 'manual' && selectedHandCard !== null && (
        <div className="hand-actions">
          <h4>Selected Card: {getSelectedCard()?.name}</h4>
          <div className="card-actions">
            {getSelectedCard()?.card_type === 'Pokemon' && (
              <button
                className="play-card-btn"
                onClick={handlePlayCard}
                disabled={!canPlaySelectedCard()}
              >
                Play Pokemon
                {!canPlaySelectedCard() && (
                  <span className="disabled-reason">
                    (No space available)
                  </span>
                )}
              </button>
            )}
            
            {getSelectedCard()?.card_type === 'Energy' && (
              <button
                className="attach-energy-btn"
                onClick={handleAttachEnergyToSelected}
                disabled={!canAttachSelectedEnergy()}
              >
                Attach Energy
                {selectedPokemon === null && (
                  <span className="action-hint">
                    (Select a Pokemon first)
                  </span>
                )}
                {player.energy_attached_this_turn && (
                  <span className="disabled-reason">
                    (Already attached this turn)
                  </span>
                )}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Manual Mode Controls */}
      {uiState.mode === 'manual' && (
        <div className="manual-controls">
          {/* Active Pokemon Actions */}
          {activePokemon && activePokemon.card && (
            <div className="pokemon-actions">
              <h4>Active Pokemon: {activePokemon.card.name}</h4>
              
              {/* Attack Buttons */}
              <div className="attack-section">
                <div className="section-label">Attacks</div>
                {activePokemon.card.attacks?.map((attack, index) => (
                  <button
                    key={index}
                    className={`attack-btn ${selectedAttack === index ? 'selected' : ''} ${!canAttack(index) ? 'disabled' : ''}`}
                    onClick={() => {
                      setSelectedAttack(index);
                      handleAttack(index);
                    }}
                    disabled={!canAttack(index)}
                  >
                    <div className="attack-name">{attack.name}</div>
                    <div className="attack-details">
                      <span className="attack-damage">{attack.damage}</span>
                      <span className="attack-cost">
                        {attack.cost?.join('') || ''}
                      </span>
                    </div>
                    {attack.effect_text && (
                      <div className="attack-effect">{attack.effect_text}</div>
                    )}
                  </button>
                ))}
              </div>

              {/* Energy Management */}
              <div className="energy-section">
                <div className="section-label">Energy</div>
                <button
                  className="energy-btn"
                  onClick={handleAttachEnergy}
                  disabled={!canAct || player.energy_attached_this_turn || !player.hand.some(card => card.card_type === 'Energy')}
                >
                  Attach Energy
                  {player.energy_attached_this_turn && ' ✓'}
                </button>
                <div className="energy-info">
                  Attached: {activePokemon.attached_energy?.length || 0}
                </div>
              </div>
            </div>
          )}

          {/* Bench Actions */}
          <div className="bench-actions">
            <div className="section-label">Bench</div>
            <button
              className="switch-btn"
              onClick={handleSwitchPokemon}
              disabled={!canAct || selectedPokemon === null || selectedPokemon === -1}
            >
              Switch Pokemon
              {selectedPokemon !== null && selectedPokemon !== -1 && (
                <span className="switch-target">
                  → {player.bench[selectedPokemon]?.card.name}
                </span>
              )}
            </button>
          </div>

          {/* Turn Controls */}
          <div className="turn-controls">
            <button
              className="pass-turn-btn"
              onClick={handlePassTurn}
              disabled={!canAct}
            >
              Pass Turn
            </button>
          </div>
        </div>
      )}

      {/* Auto-Sim Mode Controls */}
      {uiState.mode === 'auto_sim' && (
        <div className="auto-sim-controls">
          <div className="auto-sim-status">
            <div className="status-indicator running">
              🤖 Auto-Simulation Running
            </div>
            <div className="speed-display">
              Speed: {uiState.auto_sim_speed}x
            </div>
          </div>
          
          <div className="sim-controls">
            <button
              className="pause-btn"
              onClick={() => onAction({ type: 'pause_simulation' })}
            >
              ⏸️ Pause
            </button>
            <button
              className="step-btn"
              onClick={() => onAction({ type: 'step_simulation' })}
            >
              ⏭️ Step
            </button>
          </div>
        </div>
      )}

      {/* Hand Preview */}
      {player.hand && player.hand.length > 0 && (
        <div className="hand-preview">
          <div className="section-label">Hand ({player.hand.length})</div>
          <div className="hand-cards">
            {player.hand.slice(0, 5).map((card) => (
              <div key={card.id} className="hand-card">
                <div className="card-name">{card.name}</div>
                <div className="card-type">{card.card_type}</div>
              </div>
            ))}
            {player.hand.length > 5 && (
              <div className="card-overflow">+{player.hand.length - 5}</div>
            )}
          </div>
        </div>
      )}

      {/* Game Status */}
      <div className="game-status">
        {gameState.winner !== null && (
          <div className="winner-announcement">
            {gameState.winner === 0 ? '🎉 You Win!' : '😞 You Lose!'}
          </div>
        )}
        
        {gameState.is_tie && (
          <div className="tie-announcement">
            🤝 It's a Tie!
          </div>
        )}
        
        {uiState.loading && (
          <div className="loading-status">
            <div className="loading-spinner"></div>
            Processing...
          </div>
        )}
      </div>
    </div>
  );
};

export default GameControls;