import React, { useState } from 'react';
import type { BattleCard, GameState, BattleUIState } from '../../types/battle';
import BattleLog from './BattleLog';
import './TestingPanel.css';

interface TestingPanelProps {
  gameState: GameState | null;
  uiState: BattleUIState;
  selectedPokemon: number | null;
  selectedHandCard: number | null;
  onAction: (action: any) => void;
  isPlayerTurn: boolean;
  showBattleLog: boolean;
  onNewBattle?: () => void;
  isSandboxMode?: boolean;
  onOpenCardSearch?: () => void;
}

const TestingPanel: React.FC<TestingPanelProps> = ({
  gameState,
  uiState,
  selectedPokemon,
  selectedHandCard,
  onAction,
  isPlayerTurn,
  showBattleLog,
  onNewBattle,
  isSandboxMode = false,
  onOpenCardSearch
}) => {
  const clearLog = () => {
    // Clear the battle log by triggering an action
    onAction({ type: 'clear_log' });
  };

  return (
    <div className="testing-panel">
      <div className="testing-header">
        <h3>🧪 Testing Sandbox</h3>
        <small>Development Only</small>
        <div className="testing-actions">
          {isSandboxMode && onOpenCardSearch && (
            <button 
              className="search-cards-btn"
              onClick={onOpenCardSearch}
              title="Search and place cards"
            >
              🔍 Search Cards
            </button>
          )}
          {onNewBattle && (
            <button 
              className="new-battle-btn compact"
              onClick={onNewBattle}
              style={{
                padding: '6px 12px',
                background: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: '600',
                width: '100%',
                maxWidth: '120px'
            }}
          >
            New Battle
          </button>
          )}
        </div>
      </div>

      {/* Battle Log */}
      {showBattleLog && (
        <div className="log-section">
          <BattleLog 
            entries={uiState.battle_log}
            maxEntries={20}
            onClear={clearLog}
          />
        </div>
      )}
    </div>
  );
};

export default TestingPanel;