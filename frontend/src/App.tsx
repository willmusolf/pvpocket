import React, { useState } from 'react'
import BattleField from './components/battle/BattleField'
import BattleSetup from './components/battle/BattleSetup'
import { useBattleWebSocket } from './hooks/useBattleWebSocket'
import './App.css'

function App() {
  const [showSetup, setShowSetup] = useState(true);
  const [isSandboxMode, setIsSandboxMode] = useState(false);
  const {
    gameState,
    uiState,
    connected,
    sendAction,
    toggleMode,
    connectToBattle,
    disconnect
  } = useBattleWebSocket();

  const handleStartBattle = (settings: {
    playerMode: 'human_vs_ai' | 'human_vs_human' | 'ai_vs_ai' | 'sandbox';
    player1Deck: string;
    player2Deck: string;
    isSandboxMode?: boolean;
  }) => {
    setShowSetup(false);
    setIsSandboxMode(settings.isSandboxMode || false);
    connectToBattle(undefined, settings.playerMode, {
      player1Deck: settings.player1Deck,
      player2Deck: settings.player2Deck
    });
    console.log('Starting battle with settings:', settings);
  };

  const handleNewBattle = () => {
    disconnect();
    setShowSetup(true);
    setIsSandboxMode(false);
  };

  // Show setup modal if no game state or explicitly requested
  if (showSetup || (!gameState && !connected)) {
    return (
      <div className="app">
        <BattleSetup
          onStartBattle={handleStartBattle}
        />
      </div>
    );
  }

  return (
    <div className="app">
      <BattleField
        gameState={gameState}
        uiState={uiState}
        onAction={sendAction}
        onModeToggle={toggleMode}
        onNewBattle={handleNewBattle}
        isSandboxMode={isSandboxMode}
      />
    </div>
  )
}

export default App
