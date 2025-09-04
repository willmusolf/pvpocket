import React, { useState, useEffect, useRef } from 'react';
import type { GameState, BattleUIState, BattlePokemon } from '../../types/battle';
import PokemonCard from './PokemonCard';
import GameControls from './GameControls';
import BattleLog from './BattleLog';
import TestingPanel from './TestingPanel';
import CardModal from './CardModal';
import CardSearchPanel from './CardSearchPanel';
import HandCards from './HandCards';
import './BattleField.css';

interface BattleFieldProps {
  gameState: GameState | null;
  uiState: BattleUIState;
  onAction: (action: any) => void;
  onModeToggle: () => void;
  onNewBattle?: () => void;
  isSandboxMode?: boolean;
}

const BattleField: React.FC<BattleFieldProps> = ({
  gameState,
  uiState,
  onAction,
  onModeToggle,
  onNewBattle,
  isSandboxMode = false
}) => {
  const [showBattleLog, setShowBattleLog] = useState(true);
  const [selectedPokemon, setSelectedPokemon] = useState<number | null>(null);
  const [selectedHandCard, setSelectedHandCard] = useState<number | null>(null);
  const [modalPokemon, setModalPokemon] = useState<BattlePokemon | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isCardSearchOpen, setIsCardSearchOpen] = useState(false);
  
  // Track if we've already sent start_game action to prevent infinite loop
  const battleStartSentRef = useRef(false);
  // Track setup_ready state to prevent duplicate emissions
  const setupReadySentRef = useRef({player1: false, player2: false});

  // Extract data from gameState
  const player = gameState?.players?.[0];
  const opponent = gameState?.players?.[1];
  const currentPlayerIndex = gameState?.current_player || 0;
  
  // Default to human vs AI control (human controls player 0, but display as Player 1)
  const isPlayerTurn = currentPlayerIndex === 0;
  
  // Convert backend player IDs (0-indexed) to display format (1-indexed)
  const displayCurrentPlayer = currentPlayerIndex + 1;

  // Check if we're in setup phase - more comprehensive check
  const isSetupPhase = gameState?.phase === 'setup' || 
                       gameState?.phase === 'initial_pokemon_placement' ||
                       gameState?.phase?.includes('PLACEMENT') || 
                       gameState?.current_turn === 0 ||
                       gameState?.turn_number === 0;
  
  // Check if battle has actually started (both players ready and not in setup)
  const isBattleStarted = !isSetupPhase && gameState?.phase === 'player_turn' && gameState?.turn_number >= 1;
  
  // Check if both players are ready (for showing battle starting message)
  const bothPlayersReady = player?.setup_ready && opponent?.setup_ready;
  
  // Reset battle start ref when game state changes or new battle
  useEffect(() => {
    if (gameState?.battle_id) {
      battleStartSentRef.current = false;
      setupReadySentRef.current = {player1: false, player2: false};
    }
  }, [gameState?.battle_id]);
  
  useEffect(() => {
    if (gameState && isSetupPhase && player?.setup_ready && opponent?.setup_ready && !uiState.loading && !battleStartSentRef.current) {
      console.log('Both players ready, starting battle...');
      battleStartSentRef.current = true; // Mark as sent to prevent repeat
      
      // Start the battle by sending start game action
      onAction({
        type: 'start_game',
        player_id: 0,
        data: {}
      });
    }
  }, [gameState, player?.setup_ready, opponent?.setup_ready, isSetupPhase, onAction, uiState.loading]);

  if (!gameState || !player || !opponent) {
    return (
      <div className="battle-field loading">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>{!gameState ? 'Connecting to Battle Server...' : 'Loading Battle Data...'}</p>
        </div>
      </div>
    );
  }
  const isDevelopment = process.env.NODE_ENV === 'development';

  const handleAbilityClick = (pokemon: any, abilityIndex: number) => {
    if (!pokemon?.card?.abilities) return;
    console.log('Ability triggered:', pokemon.card.abilities[abilityIndex]);
    onAction({
      type: 'use_ability',
      player_id: 0, // Human player is always player 0
      data: {
        ability_index: abilityIndex
      }
    });
  };

  const handleAttackClick = (pokemon: any, attackIndex: number) => {
    if (!pokemon?.card?.attacks) return;
    console.log('Attack triggered:', pokemon.card.attacks[attackIndex]);
    onAction({
      type: 'attack',
      player_id: 0, // Human player is always player 0
      data: {
        attack_index: attackIndex
      }
    });
    // Close any open modals after attack is initiated
    if (isModalOpen) {
      setIsModalOpen(false);
      setModalPokemon(null);
    }
  };

  const handleCardClick = (pokemon: BattlePokemon) => {
    setModalPokemon(pokemon);
    setIsModalOpen(true);
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setModalPokemon(null);
  };

  const handleModalAbilityClick = (abilityIndex: number) => {
    if (modalPokemon) {
      console.log('Modal ability triggered:', modalPokemon.card.abilities[abilityIndex]);
      onAction({
        type: 'use_ability',
        player_id: 0, // Human player is always player 0
        data: {
          ability_index: abilityIndex
        }
      });
    }
  };

  const handleModalAttackClick = (attackIndex: number) => {
    if (modalPokemon) {
      console.log('Modal attack triggered:', modalPokemon.card.attacks[attackIndex]);
      onAction({
        type: 'attack',
        player_id: 0, // Human player is always player 0
        data: {
          attack_index: attackIndex
        }
      });
      // Close the modal after attack is initiated
      setIsModalOpen(false);
      setModalPokemon(null);
    }
  };

  // Sandbox manipulation functions
  const handleSandboxAction = async (actionType: string, data: any) => {
    try {
      console.log('Battle ID:', gameState?.battle_id, 'Action:', actionType, 'Data:', data);
      
      // Enhanced data preparation for different action types
      let requestData = {
        battle_id: gameState?.battle_id,
        type: actionType,
        ...data
      };
      
      // Special handling for energy attachment to ensure correct player targeting
      if (actionType === 'attach_energy' && !data.target_player && data.player_id !== undefined) {
        requestData.target_player = data.player_id;
        console.log('Enhanced energy attachment targeting:', requestData);
      }
      
      const response = await fetch('/api/dev/battle/manipulate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
      });

      const result = await response.json();
      if (result.success) {
        // Battle state will be updated via WebSocket
        console.log('✅ Sandbox action successful:', actionType, result.message || result);
        
        // Close search modal after successful placement
        if (actionType === 'place_card') {
          setIsCardSearchOpen(false);
        }
      } else {
        console.error('❌ Sandbox action failed:', result.error);
      }
    } catch (error) {
      console.error('Error performing sandbox action:', error);
    }
  };

  const handleCardPlace = (card: any, position: string, benchIndex?: number, selectedPlayer?: number) => {
    const data: any = {
      card_id: card.id,
      player: selectedPlayer ?? 0, // Use selectedPlayer or default to player 0
      position: position
    };

    if (position === 'bench' && benchIndex !== undefined) {
      data.bench_index = benchIndex;
    }

    console.log('Placing card:', card.name, 'at position:', position, 'data:', data);
    handleSandboxAction('place_card', data);
  };

  const handleOpenCardSearch = () => {
    if (isSandboxMode) {
      setIsCardSearchOpen(true);
    }
  };

  return (
    <div className="battle-field">
      {/* Turn Indicator - Always visible during battle */}
      {isBattleStarted && (
        <div className="turn-indicator-banner">
          <div className="turn-info">
            <span className="turn-number">Turn {gameState?.turn_number || 1}</span>
            <span className="turn-player">
              {isPlayerTurn ? (
                <span className="your-turn">🔴 Player 1's Turn (You)</span>
              ) : (
                <span className="opponent-turn">🔵 Player 2's Turn (Opponent)</span>
              )}
            </span>
            {gameState?.phase && (
              <span className="game-phase">Phase: {gameState.phase}</span>
            )}
          </div>
        </div>
      )}
      
      <div className="battle-content">
        {/* Mobile-style narrow game area */}
        <div className="mobile-game-area">
          {/* Opponent's hand and prize points */}
          <div className="opponent-section">
            <div className="opponent-status-bar">
              <div className="prize-points opponent-prizes">
                Prize Points: {opponent.prize_points}/3
              </div>
              {isSetupPhase && !isBattleStarted && (
                <div className="opponent-setup-controls">
                  <span className={`ready-indicator ${opponent?.setup_ready ? 'ready' : 'not-ready'}`}>
                    Player 2: {opponent?.setup_ready ? '✓ Ready' : '⏳ Not Ready'}
                  </span>
                  {isSandboxMode && (
                    <button 
                      className={`ready-btn ${opponent?.setup_ready ? 'is-ready' : 'not-ready'}`}
                      onClick={() => {
                        const newReadyState = !opponent?.setup_ready;
                        // Prevent duplicate emissions
                        if (setupReadySentRef.current.player2 !== newReadyState) {
                          setupReadySentRef.current.player2 = newReadyState;
                          onAction({
                            type: 'setup_ready',
                            player_id: 1,
                            data: { ready: newReadyState }
                          });
                        }
                      }}
                      disabled={!opponent?.active_pokemon || uiState.loading}
                    >
                      {opponent?.setup_ready ? 'Unready Opponent' : 'Ready Opponent'}
                    </button>
                  )}
                </div>
              )}
            </div>
            <div className="opponent-hand">
              <HandCards 
                cards={opponent.hand || []}
                isOpponent={true}
                onCardClick={() => {}} // Opponent cards not clickable
              />
            </div>
          </div>

          {/* Opponent's bench (top row) */}
          <div className="opponent-bench">
            <div className="bench-slots horizontal">
              {Array.from({ length: 3 }, (_, i) => (
                <div key={i} className="pokemon-slot bench-slot">
                  {opponent.bench[i] ? (
                    <PokemonCard 
                      pokemon={opponent.bench[i]}
                      isOpponent={true}
                      isSelected={false}
                      size="small"
                      onClick={() => {}}
                      onCardClick={() => handleCardClick(opponent.bench[i])}
                      showInteractiveElements={isDevelopment && (isSandboxMode || (isBattleStarted && !isPlayerTurn))}
                      onAbilityClick={(abilityIndex) => handleAbilityClick(opponent.bench[i], abilityIndex)}
                      onAttackClick={(attackIndex) => handleAttackClick(opponent.bench[i], attackIndex)}
                    />
                  ) : (
                    <div className="empty-slot">Empty</div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Opponent's active Pokemon */}
          <div className="opponent-active">
            <div className="active-pokemon-area">
              <div className="pokemon-slot active-slot large">
                {opponent.active_pokemon ? (
                  <PokemonCard 
                    pokemon={opponent.active_pokemon}
                    isOpponent={true}
                    isSelected={false}
                    size="large"
                    onClick={() => {}}
                    onCardClick={() => opponent.active_pokemon && handleCardClick(opponent.active_pokemon)}
                    showInteractiveElements={isDevelopment && (isSandboxMode || (isBattleStarted && !isPlayerTurn))}
                    onAbilityClick={(abilityIndex) => opponent.active_pokemon && handleAbilityClick(opponent.active_pokemon, abilityIndex)}
                    onAttackClick={(attackIndex) => opponent.active_pokemon && handleAttackClick(opponent.active_pokemon, attackIndex)}
                  />
                ) : (
                  <div className="empty-slot large">No Active Pokemon</div>
                )}
              </div>
              <div className="deck-indicator opponent-deck">
                <div className="deck-sleeve"></div>
                <div className="deck-count">{opponent?.deck?.length || 0}</div>
              </div>
            </div>
          </div>


          {/* Player's active Pokemon */}
          <div className="player-active">
            <div className="active-pokemon-area">
              <div className="deck-indicator player-deck">
                <div className="deck-sleeve"></div>
                <div className="deck-count">{player?.deck?.length || 0}</div>
              </div>
              <div className="pokemon-slot active-slot large">
                {player.active_pokemon ? (
                  <PokemonCard 
                    pokemon={player.active_pokemon}
                    isOpponent={false}
                    isSelected={selectedPokemon === -1}
                    size="large"
                    onClick={() => setSelectedPokemon(-1)}
                    onCardClick={() => player.active_pokemon && handleCardClick(player.active_pokemon)}
                    showInteractiveElements={isDevelopment && (isSandboxMode || (isBattleStarted && isPlayerTurn))}
                    onAbilityClick={(abilityIndex) => player.active_pokemon && handleAbilityClick(player.active_pokemon, abilityIndex)}
                    onAttackClick={(attackIndex) => player.active_pokemon && handleAttackClick(player.active_pokemon, attackIndex)}
                  />
                ) : (
                  <div className="empty-slot large">No Active Pokemon</div>
                )}
              </div>
            </div>
          </div>

          {/* Player's bench (bottom row) */}
          <div className="player-bench">
            <div className="bench-slots horizontal">
              {Array.from({ length: 3 }, (_, i) => (
                <div key={i} className="pokemon-slot bench-slot">
                  {player.bench[i] ? (
                    <PokemonCard 
                      pokemon={player.bench[i]}
                      isOpponent={false}
                      isSelected={selectedPokemon === i}
                      size="small"
                      onClick={() => setSelectedPokemon(i)}
                      onCardClick={() => handleCardClick(player.bench[i])}
                      showInteractiveElements={isDevelopment && (isSandboxMode || (isBattleStarted && isPlayerTurn))}
                      onAbilityClick={(abilityIndex) => handleAbilityClick(player.bench[i], abilityIndex)}
                      onAttackClick={(attackIndex) => handleAttackClick(player.bench[i], attackIndex)}
                    />
                  ) : (
                    <div className="empty-slot">Empty</div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Player's hand and prize points */}
          <div className="player-section">
            <div className="player-status-bar">
              <div className="prize-points player-prizes">
                Prize Points: {player.prize_points}/3
              </div>
              {isBattleStarted && (
                <div className="energy-status">
                  <div className="energy-indicator">
                    ⚡ {player?.energy_per_turn || 1}/turn
                    {player?.energy_attached_this_turn && " ✓"}
                  </div>
                </div>
              )}
              {isSetupPhase && !isBattleStarted && (
                <div className="player-setup-controls">
                  <span className={`ready-indicator ${player?.setup_ready ? 'ready' : 'not-ready'}`}>
                    Player 1 (You): {player?.setup_ready ? '✓ Ready' : '⏳ Not Ready'}
                  </span>
                  <button 
                    className={`ready-btn ${player?.setup_ready ? 'is-ready' : 'not-ready'}`}
                    onClick={() => {
                      const newReadyState = !player?.setup_ready;
                      // Prevent duplicate emissions
                      if (setupReadySentRef.current.player1 !== newReadyState) {
                        setupReadySentRef.current.player1 = newReadyState;
                        onAction({
                          type: 'setup_ready',
                          player_id: 0,
                          data: { ready: newReadyState }
                        });
                      }
                    }}
                    disabled={!player?.active_pokemon || uiState.loading}
                  >
                    {player?.setup_ready ? 'Unready' : 'Ready Up'}
                  </button>
                  {!player?.active_pokemon && (
                    <div className="setup-instructions">
                      Place a basic Pokemon in your active slot first!
                    </div>
                  )}
                  {player?.setup_ready && opponent?.setup_ready && (
                    <div className="battle-starting">
                      🚀 Battle Starting...
                    </div>
                  )}
                </div>
              )}
              {isBattleStarted && (
                <div className="battle-status">
                  <div className="turn-indicator">
                    Turn {gameState?.turn_number || 1} - {isPlayerTurn ? 'Player 1 (Your Turn)' : 'Player 2 (Opponent Turn)'}
                  </div>
                </div>
              )}
              {isBattleStarted && isPlayerTurn && !isSandboxMode && (
                <div className="player-turn-controls">
                  <button 
                    className="draw-card-btn"
                    onClick={() => onAction({
                      type: 'draw_card',
                      player_id: 0,
                      data: {}
                    })}
                    disabled={uiState.loading || !player?.deck || player.deck.length === 0}
                    title={player?.deck?.length === 0 ? 'No cards left in deck' : 'Draw a card from your deck'}
                  >
                    🃏 Draw Card
                  </button>
                  <button 
                    className="end-turn-btn"
                    onClick={() => onAction({
                      type: 'pass_turn',
                      player_id: 0,
                      data: {}
                    })}
                    disabled={uiState.loading}
                  >
                    End Turn
                  </button>
                </div>
              )}
              {isBattleStarted && !isPlayerTurn && !isSandboxMode && (
                <div className="waiting-indicator">
                  <div className="waiting-message">
                    ⏳ Waiting for Player 2's turn...
                  </div>
                </div>
              )}
            </div>
            <div className="player-hand">
              <HandCards 
                cards={player.hand || []}
                isOpponent={false}
                selectedCardIndex={selectedHandCard}
                gameState={gameState}
                canPlayCards={isBattleStarted || isSandboxMode}
                onCardClick={(card, index) => {
                  console.log('Hand card clicked:', card, index);
                  // Toggle selection if same card clicked, otherwise select new card
                  setSelectedHandCard(selectedHandCard === index ? null : index);
                }}
              />
            </div>
          </div>
        </div>

        {/* Testing sandbox panel */}
        {process.env.NODE_ENV === 'development' && (
          <TestingPanel
            gameState={gameState}
            uiState={uiState}
            selectedPokemon={selectedPokemon}
            selectedHandCard={selectedHandCard}
            onAction={onAction}
            isPlayerTurn={isPlayerTurn}
            showBattleLog={showBattleLog}
            onNewBattle={onNewBattle}
            isSandboxMode={isSandboxMode}
            onOpenCardSearch={handleOpenCardSearch}
          />
        )}

        {/* Fallback side panel for production */}
        {process.env.NODE_ENV !== 'development' && (
          <div className="side-panel">
            <GameControls 
              gameState={gameState}
              uiState={uiState}
              selectedPokemon={selectedPokemon}
              selectedHandCard={selectedHandCard}
              onAction={onAction}
              isPlayerTurn={isPlayerTurn}
            />

            {showBattleLog && (
              <BattleLog 
                entries={uiState.battle_log}
                maxEntries={50}
              />
            )}
          </div>
        )}
      </div>

      {/* Connection status */}
      {!uiState.connected && (
        <div className="connection-status disconnected">
          ⚠️ Disconnected from server
        </div>
      )}

      {/* Card Modal */}
      <CardModal
        pokemon={modalPokemon}
        isOpen={isModalOpen}
        onClose={handleModalClose}
        onAbilityClick={handleModalAbilityClick}
        onAttackClick={handleModalAttackClick}
        showInteractiveElements={isDevelopment && (isSandboxMode || isBattleStarted)}
        isOpponent={modalPokemon ? (gameState?.players[0].active_pokemon === modalPokemon || gameState?.players[0].bench.includes(modalPokemon)) ? false : true : false}
        isSandboxMode={isSandboxMode}
        onSandboxAction={handleSandboxAction}
        playerIndex={modalPokemon ? (gameState?.players[0].active_pokemon === modalPokemon || gameState?.players[0].bench.includes(modalPokemon)) ? 0 : 1 : 0}
        pokemonPosition={modalPokemon ? (() => {
          // Determine if this is active or bench position
          if (gameState?.players[0].active_pokemon === modalPokemon) return 'active';
          if (gameState?.players[1].active_pokemon === modalPokemon) return 'active';
          
          // Check bench positions for both players
          const player0BenchIndex = gameState?.players[0].bench.findIndex(p => p === modalPokemon);
          if (player0BenchIndex !== -1 && player0BenchIndex !== undefined) return player0BenchIndex.toString();
          
          const player1BenchIndex = gameState?.players[1].bench.findIndex(p => p === modalPokemon);
          if (player1BenchIndex !== -1 && player1BenchIndex !== undefined) return player1BenchIndex.toString();
          
          return 'active';
        })() : 'active'}
      />

      {/* Card Search Panel */}
      <CardSearchPanel
        isOpen={isCardSearchOpen}
        onClose={() => setIsCardSearchOpen(false)}
        onCardPlace={handleCardPlace}
        isSandboxMode={isSandboxMode}
      />
    </div>
  );
};

export default BattleField;