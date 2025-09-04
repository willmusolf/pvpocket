import { useState, useEffect, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import type { GameState, BattleUIState, BattleLogEntry } from '../types/battle';

interface UseBattleWebSocketResult {
  gameState: GameState | null;
  uiState: BattleUIState;
  connected: boolean;
  sendAction: (action: any) => void;
  toggleMode: () => void;
  connectToBattle: (battleId?: string, playerMode?: 'human_vs_ai' | 'human_vs_human' | 'ai_vs_ai') => void;
  disconnect: () => void;
}

export const useBattleWebSocket = (
  serverUrl: string = 'http://localhost:5002'
): UseBattleWebSocketResult => {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [connected, setConnected] = useState(false);
  const [battleLog, setBattleLog] = useState<BattleLogEntry[]>([]);
  const [mode, setMode] = useState<'manual' | 'auto_sim'>('manual');
  const [autoSimSpeed, setAutoSimSpeed] = useState<1 | 2 | 4 | 8>(1);
  const [loading, setLoading] = useState(false);
  
  const socketRef = useRef<Socket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const uiState: BattleUIState = {
    mode,
    auto_sim_speed: autoSimSpeed,
    selected_card: null,
    selected_attack: null,
    battle_log: battleLog,
    connected,
    loading
  };

  const addLogEntry = useCallback((type: string, message: string, details?: any) => {
    const entry: BattleLogEntry = {
      id: `${Date.now()}-${Math.random()}`,
      timestamp: Date.now(),
      type: type as any,
      message,
      details
    };
    
    setBattleLog(prev => [...prev, entry]);
  }, []);

  const connectToBattle = useCallback((battleId?: string, playerMode: 'human_vs_ai' | 'human_vs_human' | 'ai_vs_ai' = 'human_vs_ai', deckSelections?: { player1Deck: string; player2Deck: string }) => {
    if (socketRef.current?.connected) {
      socketRef.current.disconnect();
    }

    // Clear battle log when starting a new battle
    setBattleLog([]);

    setLoading(true);
    addLogEntry('info', 'Connecting to battle server...', { serverUrl });

    const socket = io(serverUrl, {
      transports: ['polling', 'websocket'], // Try polling first
      timeout: 10000, // Increased timeout to 10 seconds
      forceNew: true,
      reconnection: true,
      reconnectionAttempts: 3,
      reconnectionDelay: 1000
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      setConnected(true);
      setLoading(false);
      addLogEntry('game', 'Connected to battle server', { socketId: socket.id });
      
      // Join or create a battle
      if (battleId) {
        socket.emit('join_battle', { battle_id: battleId });
      } else {
        socket.emit('create_battle', { 
          mode: 'test_battle',
          deck_config: 'default',
          player_mode: playerMode,
          player1_deck: deckSelections?.player1Deck || 'fire',
          player2_deck: deckSelections?.player2Deck || 'water'
        });
      }
    });

    socket.on('disconnect', () => {
      setConnected(false);
      addLogEntry('warning', 'Disconnected from server');
    });

    socket.on('connect_error', (error) => {
      setConnected(false);
      setLoading(false);
      addLogEntry('error', `Connection failed: ${error.message}`, { error });
      console.error('WebSocket connection error:', error);
    });

    // Battle-specific events
    socket.on('battle_created', (data) => {
      addLogEntry('game', `Battle created: ${data.battle_id}`, data);
      setGameState(data.game_state);
    });

    socket.on('battle_joined', (data) => {
      addLogEntry('game', `Joined battle: ${data.battle_id}`, data);
      setGameState(data.game_state);
    });

    socket.on('game_state_update', (data) => {
      const prevGameState = gameState;
      setGameState(data.game_state);
      
      // Check for battle start condition
      const currentPhase = data.game_state.phase;
      const turnNumber = data.game_state.turn_number || data.game_state.current_turn;
      const prevPhase = prevGameState?.phase;
      
      // Detect when battle transitions from setup to actual gameplay
      if (prevPhase && (prevPhase === 'setup' || prevPhase.includes('placement')) && 
          (currentPhase === 'player_turn' || currentPhase === 'main' || currentPhase === 'draw') &&
          turnNumber >= 1) {
        addLogEntry('game', '🚀 Battle Started! Both players are ready.', {
          phase: currentPhase,
          turn: turnNumber
        });
      } else {
        addLogEntry('action', 'Game state updated', { 
          turn: turnNumber,
          phase: currentPhase 
        });
      }
      
      // Log important state changes for debugging
      if (process.env.NODE_ENV === 'development') {
        console.log('🔄 Game state updated:', {
          turn: turnNumber,
          currentPlayer: data.game_state.current_player,
          phase: currentPhase,
          player1Ready: data.game_state.players[0]?.setup_ready,
          player2Ready: data.game_state.players[1]?.setup_ready
        });
      }
    });

    socket.on('battle_action_result', (data) => {
      // Use descriptive log entries if available from the enhanced backend
      if (data.log_entries && data.log_entries.length > 0) {
        data.log_entries.forEach((logEntry: any) => {
          if (logEntry.descriptive_text) {
            // Use the enhanced descriptive text
            addLogEntry('action', logEntry.descriptive_text, {
              turn: logEntry.turn,
              player: logEntry.player,
              action: logEntry.action
            });
          } else if (logEntry.message) {
            // Handle backend messages with proper player numbering
            let displayMessage = logEntry.message;
            
            // Handle system actions (player -1)
            if (logEntry.player === -1) {
              addLogEntry('game', displayMessage, logEntry);
            } else {
              // Convert backend player ID (0-indexed) to display format (1-indexed)
              const displayPlayer = typeof logEntry.player === 'number' ? logEntry.player + 1 : 'Unknown';
              const actionText = logEntry.action ? logEntry.action.replace('_', ' ') : 'unknown action';
              
              // Format message with proper player numbering
              if (displayMessage.includes('Player 0') || displayMessage.includes('Player 1')) {
                displayMessage = displayMessage
                  .replace(/Player 0/g, 'Player 1')
                  .replace(/Player 1/g, 'Player 2');
              } else {
                displayMessage = `Player ${displayPlayer}: ${displayMessage}`;
              }
              
              addLogEntry('action', displayMessage, logEntry);
            }
          } else {
            // Fallback to basic logging with proper player numbering
            const actionText = logEntry.action ? logEntry.action.replace('_', ' ') : 'unknown action';
            const playerNum = typeof logEntry.player === 'number' ? logEntry.player + 1 : 'Unknown';
            addLogEntry('action', `Player ${playerNum}: ${actionText}`, logEntry);
          }
        });
      } else {
        // Fallback for older backend or missing log entries with proper player numbering
        const displayPlayer = typeof data.player_id === 'number' ? data.player_id + 1 : 'Unknown';
        addLogEntry('action', `Player ${displayPlayer}: ${data.action_type}`, {
          result: data.result,
          player: data.player_id
        });
      }
      
      if (data.effects) {
        data.effects.forEach((effect: any) => {
          addLogEntry('effect', `Effect: ${effect.description}`, effect);
        });
      }
    });

    socket.on('battle_ended', (data) => {
      addLogEntry('game', `Battle ended: ${data.winner ? `Player ${data.winner} wins!` : 'Tie!'}`, data);
    });

    socket.on('ai_turn_start', (data) => {
      addLogEntry('info', 'AI turn starting...', data);
    });

    socket.on('ai_turn_needed', (data) => {
      const displayPlayer = typeof data.current_player === 'number' ? data.current_player + 1 : 'Unknown';
      addLogEntry('info', `AI turn needed for Player ${displayPlayer}`, data);
      // Automatically request AI action with a small delay for visual feedback
      if (socket.connected) {
        setTimeout(() => {
          socket.emit('request_ai_action');
        }, 1500); // Slightly longer delay for better visualization
      }
    });

    socket.on('error', (error) => {
      addLogEntry('error', `Server error: ${error.message}`, error);
    });

  }, [serverUrl, addLogEntry]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
    }
    
    setConnected(false);
    setGameState(null);
    addLogEntry('info', 'Disconnected from battle server');
  }, [addLogEntry]);

  const sendAction = useCallback((action: any) => {
    // Handle special UI actions
    if (action.type === 'clear_log') {
      setBattleLog([]);
      return;
    }

    if (action.type === 'set_speed') {
      setAutoSimSpeed(action.speed);
      addLogEntry('info', `Auto-sim speed set to ${action.speed}x`);
      return;
    }

    if (action.type === 'pause_simulation') {
      if (socketRef.current?.connected) {
        socketRef.current.emit('pause_simulation');
        addLogEntry('info', 'Auto-simulation paused');
      }
      return;
    }

    if (action.type === 'step_simulation') {
      if (socketRef.current?.connected) {
        socketRef.current.emit('step_simulation');
        addLogEntry('info', 'Auto-simulation stepped');
      }
      return;
    }

    if (!socketRef.current?.connected) {
      addLogEntry('error', 'Not connected to server');
      return;
    }

    // Send regular battle actions
    socketRef.current.emit('battle_action', action);
    addLogEntry('action', `Sent action: ${action.type}`, action);
  }, [addLogEntry]);

  const toggleMode = useCallback(() => {
    const newMode = mode === 'manual' ? 'auto_sim' : 'manual';
    setMode(newMode);
    addLogEntry('info', `Switched to ${newMode} mode`);
    
    // Notify server of mode change
    if (socketRef.current?.connected) {
      socketRef.current.emit('set_mode', { mode: newMode, speed: autoSimSpeed });
    }
  }, [mode, autoSimSpeed, addLogEntry]);

  // Don't auto-connect or use mock data - wait for user to start battle via setup
  // This prevents duplicate connections and conflicts

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    gameState,
    uiState,
    connected,
    sendAction,
    toggleMode,
    connectToBattle,
    disconnect
  };
};