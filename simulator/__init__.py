"""
Pokemon TCG Pocket Battle Simulator

A comprehensive battle simulation system for Pokemon TCG Pocket cards.
Includes game engine, AI players, and analysis tools.

Phase 1: Core battle mechanics and rule-based AI
Phase 2+: Advanced AI strategies and meta analysis
"""

from .core.game import GameState, BattleResult
from .core.player import PlayerState  
from .core.pokemon import BattlePokemon
from .core.energy import EnergyManager
from .core.rules import RulesEngine, BattleRules

__version__ = "1.0.0"
__status__ = "Phase 1 Implementation"

__all__ = [
    "GameState",
    "BattleResult", 
    "PlayerState",
    "BattlePokemon",
    "EnergyManager",
    "RulesEngine",
    "BattleRules"
]