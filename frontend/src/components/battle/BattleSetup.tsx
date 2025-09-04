import React, { useState } from 'react';
import './BattleSetup.css';

interface BattleSetupProps {
  onStartBattle: (settings: {
    playerMode: 'human_vs_ai' | 'human_vs_human' | 'ai_vs_ai' | 'sandbox';
    player1Deck: string;
    player2Deck: string;
    isSandboxMode?: boolean;
  }) => void;
  onCancel?: () => void;
}

const BattleSetup: React.FC<BattleSetupProps> = ({ onStartBattle, onCancel }) => {
  const [playerMode, setPlayerMode] = useState<'human_vs_ai' | 'human_vs_human' | 'ai_vs_ai' | 'sandbox'>('human_vs_ai');
  const [player1Deck, setPlayer1Deck] = useState<string>('fire');
  const [player2Deck, setPlayer2Deck] = useState<string>('water');

  const handleStartBattle = () => {
    onStartBattle({
      playerMode,
      player1Deck,
      player2Deck,
      isSandboxMode: playerMode === 'sandbox'
    });
  };

  return (
    <div className="battle-setup-overlay">
      <div className="battle-setup-modal">
        <h2>Battle Simulator Setup</h2>
        
        <div className="setup-section">
          <h3>Player Control Mode</h3>
          <div className="mode-options">
            <label className={`mode-option ${playerMode === 'human_vs_ai' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="playerMode"
                value="human_vs_ai"
                checked={playerMode === 'human_vs_ai'}
                onChange={(e) => setPlayerMode(e.target.value as 'human_vs_ai')}
              />
              <div className="option-content">
                <div className="option-title">Human vs AI</div>
                <div className="option-description">You control Player 1, AI controls Player 2</div>
              </div>
            </label>

            <label className={`mode-option ${playerMode === 'human_vs_human' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="playerMode"
                value="human_vs_human"
                checked={playerMode === 'human_vs_human'}
                onChange={(e) => setPlayerMode(e.target.value as 'human_vs_human')}
              />
              <div className="option-content">
                <div className="option-title">Human vs Human</div>
                <div className="option-description">You control both players (hot-seat mode)</div>
              </div>
            </label>

            <label className={`mode-option ${playerMode === 'ai_vs_ai' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="playerMode"
                value="ai_vs_ai"
                checked={playerMode === 'ai_vs_ai'}
                onChange={(e) => setPlayerMode(e.target.value as 'ai_vs_ai')}
              />
              <div className="option-content">
                <div className="option-title">AI vs AI</div>
                <div className="option-description">Watch AI play against itself for testing</div>
              </div>
            </label>

            <label className={`mode-option sandbox-mode ${playerMode === 'sandbox' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="playerMode"
                value="sandbox"
                checked={playerMode === 'sandbox'}
                onChange={(e) => setPlayerMode(e.target.value as 'sandbox')}
              />
              <div className="option-content">
                <div className="option-title">🧪 Sandbox Mode</div>
                <div className="option-description">Free-form testing with card search and manipulation</div>
              </div>
            </label>
          </div>
        </div>

        <div className="setup-section">
          <h3>Deck Selection</h3>
          <div className="deck-options">
            <div className="deck-option">
              <label className="deck-label">Player 1 Deck</label>
              <select 
                className="deck-select" 
                value={player1Deck} 
                onChange={(e) => setPlayer1Deck(e.target.value)}
              >
                <option value="fire">🔥 Fire Deck (Charizard/Arcanine)</option>
                <option value="water">💧 Water Deck (Blastoise/Starmie)</option>
                <option value="lightning">⚡ Lightning Deck (Pikachu/Raichu)</option>
                <option value="psychic">🧠 Psychic Deck (Mewtwo/Alakazam)</option>
                <option value="grass">🍃 Grass Deck (Venusaur/Exeggutor)</option>
                <option value="fighting">👊 Fighting Deck (Machamp/Primeape)</option>
                <option value="colorless">⚪ Colorless Deck (Pidgeot/Kangaskhan)</option>
                <option value="dark">🌙 Dark Deck (Mixed Dark Types)</option>
                <option value="metal">⚙️ Metal Deck (Mixed Metal Types)</option>
              </select>
            </div>

            <div className="deck-option">
              <label className="deck-label">Player 2 Deck</label>
              <select 
                className="deck-select" 
                value={player2Deck} 
                onChange={(e) => setPlayer2Deck(e.target.value)}
              >
                <option value="fire">🔥 Fire Deck (Charizard/Arcanine)</option>
                <option value="water">💧 Water Deck (Blastoise/Starmie)</option>
                <option value="lightning">⚡ Lightning Deck (Pikachu/Raichu)</option>
                <option value="psychic">🧠 Psychic Deck (Mewtwo/Alakazam)</option>
                <option value="grass">🍃 Grass Deck (Venusaur/Exeggutor)</option>
                <option value="fighting">👊 Fighting Deck (Machamp/Primeape)</option>
                <option value="colorless">⚪ Colorless Deck (Pidgeot/Kangaskhan)</option>
                <option value="dark">🌙 Dark Deck (Mixed Dark Types)</option>
                <option value="metal">⚙️ Metal Deck (Mixed Metal Types)</option>
              </select>
            </div>
          </div>
        </div>

        <div className="setup-actions">
          {onCancel && (
            <button className="cancel-btn" onClick={onCancel}>
              Cancel
            </button>
          )}
          <button className="start-battle-btn" onClick={handleStartBattle}>
            Start Battle
          </button>
        </div>
      </div>
    </div>
  );
};

export default BattleSetup;