import React, { useState, useEffect } from 'react';
import './EffectDisplay.css';

interface EffectDisplayProps {
  effects?: ActiveEffect[];
}

interface ActiveEffect {
  id: string;
  type: 'damage' | 'heal' | 'status' | 'energy' | 'coin_flip' | 'card_draw';
  message: string;
  value?: number;
  duration?: number;
  position?: { x: number; y: number };
  target?: 'player' | 'opponent' | 'active' | 'bench';
}

const EffectDisplay: React.FC<EffectDisplayProps> = ({ effects = [] }) => {
  // For now, just display a static placeholder since we're not using real effects yet
  const displayEffects: ActiveEffect[] = [];

  return (
    <div className="effect-display">
      {/* Central Effect Area - placeholder for major effects */}
      <div className="central-effects">
        <div className="effect-stage">
          <div className="stage-content">
            <div className="stage-placeholder">
              <div className="placeholder-icon">✨</div>
              <div className="placeholder-text">Effects appear here</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EffectDisplay;