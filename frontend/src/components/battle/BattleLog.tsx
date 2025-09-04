import React, { useEffect, useRef, useState, useCallback } from 'react';
import type { BattleLogEntry } from '../../types/battle';
import './BattleLog.css';

interface BattleLogProps {
  entries: BattleLogEntry[];
  maxEntries?: number;
  onClear?: () => void;
}

const BattleLog: React.FC<BattleLogProps> = ({ 
  entries,
  maxEntries = 20,
  onClear
}) => {
  const logEndRef = useRef<HTMLDivElement>(null);
  const logEntriesRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  // Check if user is at bottom of scroll
  const checkIfAtBottom = useCallback(() => {
    if (!logEntriesRef.current) return false;
    const { scrollTop, scrollHeight, clientHeight } = logEntriesRef.current;
    const threshold = 10; // pixels from bottom
    return Math.abs(scrollHeight - scrollTop - clientHeight) < threshold;
  }, []);

  // Handle scroll events to track user position
  const handleScroll = useCallback(() => {
    const atBottom = checkIfAtBottom();
    setIsAtBottom(atBottom);
  }, [checkIfAtBottom]);

  // Smart auto-scroll: only scroll if user is already at bottom
  useEffect(() => {
    if (isAtBottom && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [entries, isAtBottom]);

  // Display all entries (no limit for full history access)
  const displayEntries = entries;

  const formatTime = (timestamp: number): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour12: false,
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getIcon = (type: string): string => {
    const icons: Record<string, string> = {
      'action': '⚡',
      'game': '🎮',
      'error': '❌',
      'warning': '⚠️',
      'info': 'ℹ️'
    };
    return icons[type] || '📝';
  };

  // Copy all logs to clipboard
  const copyAllLogs = useCallback(async () => {
    const logText = entries.map(entry => {
      const time = formatTime(entry.timestamp);
      const icon = getIcon(entry.type);
      return `${time} ${icon} ${entry.message}`;
    }).join('\n');
    
    try {
      await navigator.clipboard.writeText(logText);
      // Could add a toast notification here if desired
    } catch (err) {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = logText;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
    }
  }, [entries, formatTime, getIcon]);

  return (
    <div className="battle-log-simple">
      <div className="log-header">
        <span className="log-title">Battle Log ({entries.length})</span>
        <div className="log-buttons">
          <button 
            className="copy-btn"
            onClick={copyAllLogs}
            title="Copy all logs to clipboard"
            disabled={entries.length === 0}
          >
            Copy All
          </button>
          <button 
            className="clear-btn"
            onClick={onClear}
            title="Clear log"
          >
            Clear
          </button>
        </div>
      </div>

      <div 
        className="log-entries"
        ref={logEntriesRef}
        onScroll={handleScroll}
      >
        {displayEntries.length === 0 ? (
          <div className="empty-message">No events yet...</div>
        ) : (
          displayEntries.map((entry) => (
            <div key={entry.id} className={`log-entry ${entry.type}`}>
              <span className="entry-time">{formatTime(entry.timestamp)}</span>
              <span className="entry-icon">{getIcon(entry.type)}</span>
              <span className="entry-message">{entry.message}</span>
            </div>
          ))
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
};

export default BattleLog;