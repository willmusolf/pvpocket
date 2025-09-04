"""
Strategic Board State Evaluator for Pokemon TCG Pocket AI

Provides sophisticated evaluation of game states to enable intelligent AI decision making.
Analyzes position, threats, opportunities, and win conditions.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Import core components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class GamePhase(Enum):
    """Game phases for strategic evaluation"""
    EARLY_GAME = "early"    # Turns 1-5, setup focused
    MID_GAME = "mid"        # Turns 6-15, position battles
    LATE_GAME = "late"      # Turns 16+, win condition push


class ThreatLevel(Enum):
    """Threat assessment levels"""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class BoardPosition:
    """Represents the current board position for evaluation"""
    # Player states
    my_active_hp_ratio: float
    my_bench_count: int
    my_prize_points: int
    my_hand_size: int
    my_energy_available: int
    
    # Opponent states  
    opponent_active_hp_ratio: float
    opponent_bench_count: int
    opponent_prize_points: int
    opponent_hand_size: int
    
    # Game state
    turn_number: int
    current_player: int
    my_player_id: int


@dataclass 
class ThreatAssessment:
    """Assessment of threats and opportunities"""
    immediate_ko_threat: bool
    opponent_can_ko_next_turn: bool
    i_can_ko_next_turn: bool
    prize_point_pressure: ThreatLevel
    board_control: float  # -1.0 (opponent control) to 1.0 (my control)
    tempo_advantage: float  # -1.0 (behind) to 1.0 (ahead)


@dataclass
class EvaluationResult:
    """Complete board evaluation result"""
    position_score: float  # Overall position evaluation (-1000 to 1000)
    threat_assessment: ThreatAssessment
    recommended_strategy: str
    key_factors: List[str]  # Human-readable explanation


class StrategicBoardEvaluator:
    """Advanced board state evaluator for strategic AI decision making"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Evaluation weights for different factors
        self.weights = {
            # Core position factors
            "hp_advantage": 0.25,
            "prize_point_pressure": 0.30, 
            "board_presence": 0.20,
            "hand_advantage": 0.15,
            "tempo": 0.10,
            
            # Threat factors
            "ko_threat_multiplier": 2.0,
            "setup_potential": 0.5,
            "win_condition_proximity": 1.5
        }
        
        # Phase-specific adjustments
        self.phase_weights = {
            GamePhase.EARLY_GAME: {
                "setup_priority": 1.5,
                "aggression_penalty": 0.8,
                "resource_priority": 1.3
            },
            GamePhase.MID_GAME: {
                "board_control": 1.2,
                "position_advantage": 1.1,
                "threat_response": 1.3
            },
            GamePhase.LATE_GAME: {
                "win_condition_focus": 1.8,
                "risk_tolerance": 1.4,
                "decisive_action": 1.6
            }
        }
    
    def evaluate_position(self, game_state) -> EvaluationResult:
        """
        Perform comprehensive evaluation of current board position
        
        Args:
            game_state: Current GameState object
            
        Returns:
            EvaluationResult with scoring and strategic recommendations
        """
        try:
            # Extract board position data
            position = self._extract_position_data(game_state)
            
            # Determine current game phase
            phase = self._determine_game_phase(position)
            
            # Calculate core position factors
            hp_score = self._evaluate_hp_advantage(position)
            prize_score = self._evaluate_prize_pressure(position) 
            board_score = self._evaluate_board_control(position)
            hand_score = self._evaluate_hand_advantage(position)
            tempo_score = self._evaluate_tempo(position)
            
            # Assess threats and opportunities
            threat_assessment = self._assess_threats(game_state, position)
            
            # Calculate weighted position score
            base_score = (
                hp_score * self.weights["hp_advantage"] +
                prize_score * self.weights["prize_point_pressure"] +
                board_score * self.weights["board_presence"] +
                hand_score * self.weights["hand_advantage"] +
                tempo_score * self.weights["tempo"]
            )
            
            # Apply threat modifiers
            threat_modifier = self._calculate_threat_modifier(threat_assessment)
            position_score = base_score * threat_modifier
            
            # Apply phase-specific adjustments
            position_score = self._apply_phase_adjustments(position_score, phase)
            
            # Generate strategic recommendation
            strategy = self._recommend_strategy(position, threat_assessment, phase)
            
            # Generate key factors explanation
            key_factors = self._identify_key_factors(
                position, threat_assessment, 
                hp_score, prize_score, board_score, hand_score, tempo_score
            )
            
            result = EvaluationResult(
                position_score=position_score,
                threat_assessment=threat_assessment,
                recommended_strategy=strategy,
                key_factors=key_factors
            )
            
            self.logger.debug(f"Board evaluation: {position_score:.1f} | Strategy: {strategy}")
            return result
            
        except Exception as e:
            self.logger.error(f"Board evaluation failed: {e}")
            # Return neutral evaluation on error
            return EvaluationResult(
                position_score=0.0,
                threat_assessment=ThreatAssessment(
                    immediate_ko_threat=False,
                    opponent_can_ko_next_turn=False,
                    i_can_ko_next_turn=False,
                    prize_point_pressure=ThreatLevel.MEDIUM,
                    board_control=0.0,
                    tempo_advantage=0.0
                ),
                recommended_strategy="balanced",
                key_factors=["Evaluation error - using default strategy"]
            )
    
    def _extract_position_data(self, game_state) -> BoardPosition:
        """Extract relevant position data from game state"""
        my_player = game_state.players[game_state.current_player]
        opponent_player = game_state.players[1 - game_state.current_player]
        
        # Calculate HP ratios
        my_hp_ratio = 1.0
        if my_player.active_pokemon:
            my_hp_ratio = my_player.active_pokemon.current_hp / max(my_player.active_pokemon.max_hp, 1)
        
        opponent_hp_ratio = 1.0  
        if opponent_player.active_pokemon:
            opponent_hp_ratio = opponent_player.active_pokemon.current_hp / max(opponent_player.active_pokemon.max_hp, 1)
        
        return BoardPosition(
            my_active_hp_ratio=my_hp_ratio,
            my_bench_count=my_player.get_bench_pokemon_count(),
            my_prize_points=my_player.prize_points,
            my_hand_size=len(my_player.hand),
            my_energy_available=self._count_available_energy(my_player),
            
            opponent_active_hp_ratio=opponent_hp_ratio,
            opponent_bench_count=opponent_player.get_bench_pokemon_count(),
            opponent_prize_points=opponent_player.prize_points,
            opponent_hand_size=len(opponent_player.hand),
            
            turn_number=game_state.turn_number,
            current_player=game_state.current_player,
            my_player_id=game_state.current_player
        )
    
    def _count_available_energy(self, player) -> int:
        """Count total energy available across all Pokemon"""
        total_energy = 0
        if player.active_pokemon:
            total_energy += len(player.active_pokemon.energy_attached)
        
        for bench_pokemon in player.bench:
            if bench_pokemon and not bench_pokemon.is_knocked_out():
                total_energy += len(bench_pokemon.energy_attached)
        
        return total_energy
    
    def _determine_game_phase(self, position: BoardPosition) -> GamePhase:
        """Determine current game phase based on turn and prize points"""
        # Early game: First 5 turns or low prize counts
        if position.turn_number <= 5 or (position.my_prize_points == 0 and position.opponent_prize_points == 0):
            return GamePhase.EARLY_GAME
        
        # Late game: High prize counts or turn 16+
        if position.turn_number >= 16 or position.my_prize_points >= 2 or position.opponent_prize_points >= 2:
            return GamePhase.LATE_GAME
        
        return GamePhase.MID_GAME
    
    def _evaluate_hp_advantage(self, position: BoardPosition) -> float:
        """Evaluate HP advantage (-100 to 100)"""
        hp_diff = position.my_active_hp_ratio - position.opponent_active_hp_ratio
        return hp_diff * 100  # Scale to -100 to 100
    
    def _evaluate_prize_pressure(self, position: BoardPosition) -> float:
        """Evaluate prize point pressure (-100 to 100)"""
        # Negative score if behind on prize points (bad position)
        prize_diff = position.opponent_prize_points - position.my_prize_points
        
        # Scale based on proximity to victory (3 prize points)
        max_prizes = 3
        pressure_factor = 1.0
        
        if position.opponent_prize_points >= 2:
            pressure_factor = 2.0  # High pressure if opponent close to winning
        elif position.my_prize_points >= 2:
            pressure_factor = -2.0  # Good position if I'm close to winning
            
        return prize_diff * 40 * pressure_factor  # Scale to meaningful range
    
    def _evaluate_board_control(self, position: BoardPosition) -> float:
        """Evaluate board presence and control (-100 to 100)"""
        # Bench advantage
        bench_diff = position.my_bench_count - position.opponent_bench_count
        bench_score = bench_diff * 20  # 20 points per bench Pokemon advantage
        
        # Hand size advantage (indicates resource availability)
        hand_diff = position.my_hand_size - position.opponent_hand_size
        hand_score = hand_diff * 10  # 10 points per card advantage
        
        return bench_score + hand_score
    
    def _evaluate_hand_advantage(self, position: BoardPosition) -> float:
        """Evaluate hand size advantage (-100 to 100)"""
        hand_diff = position.my_hand_size - position.opponent_hand_size
        return hand_diff * 15  # 15 points per card advantage
    
    def _evaluate_tempo(self, position: BoardPosition) -> float:
        """Evaluate tempo/momentum (-100 to 100)"""
        tempo_score = 0.0
        
        # Energy advantage indicates better setup
        energy_ratio = position.my_energy_available / max(position.opponent_bench_count + 1, 1)
        if energy_ratio > 1.5:
            tempo_score += 30  # Good energy advantage
        elif energy_ratio < 0.7:
            tempo_score -= 30  # Behind on energy
        
        # Prize point momentum
        if position.my_prize_points > position.opponent_prize_points:
            tempo_score += 20  # Winning on points
        elif position.my_prize_points < position.opponent_prize_points:
            tempo_score -= 20  # Behind on points
            
        return tempo_score
    
    def _assess_threats(self, game_state, position: BoardPosition) -> ThreatAssessment:
        """Assess immediate threats and opportunities"""
        my_player = game_state.players[position.my_player_id]
        opponent_player = game_state.players[1 - position.my_player_id]
        
        # Check for immediate KO threats
        immediate_ko_threat = False
        opponent_can_ko = False
        i_can_ko = False
        
        # Assess if opponent can KO my active Pokemon
        if my_player.active_pokemon and opponent_player.active_pokemon:
            opponent_attacks = opponent_player.get_available_attacks()
            for attack in opponent_attacks:
                damage = opponent_player.active_pokemon.calculate_attack_damage(
                    attack, my_player.active_pokemon
                )
                if damage >= my_player.active_pokemon.current_hp:
                    opponent_can_ko = True
                    if position.current_player != position.my_player_id:
                        immediate_ko_threat = True
                    break
        
        # Assess if I can KO opponent's active Pokemon
        if my_player.active_pokemon and opponent_player.active_pokemon:
            my_attacks = my_player.get_available_attacks()
            for attack in my_attacks:
                damage = my_player.active_pokemon.calculate_attack_damage(
                    attack, opponent_player.active_pokemon
                )
                if damage >= opponent_player.active_pokemon.current_hp:
                    i_can_ko = True
                    break
        
        # Assess prize point pressure
        prize_pressure = ThreatLevel.LOW
        if position.opponent_prize_points >= 2:
            prize_pressure = ThreatLevel.CRITICAL
        elif position.opponent_prize_points == 1:
            prize_pressure = ThreatLevel.HIGH
        elif position.my_prize_points >= 2:
            prize_pressure = ThreatLevel.LOW  # I'm winning
        
        # Calculate board control
        bench_control = (position.my_bench_count - position.opponent_bench_count) / 6.0  # Max 3 bench each
        hand_control = (position.my_hand_size - position.opponent_hand_size) / 20.0  # Reasonable hand size range
        board_control = (bench_control + hand_control) / 2.0
        
        # Calculate tempo advantage
        hp_tempo = position.my_active_hp_ratio - position.opponent_active_hp_ratio
        prize_tempo = (position.opponent_prize_points - position.my_prize_points) / 3.0
        tempo_advantage = (hp_tempo - prize_tempo) / 2.0
        
        return ThreatAssessment(
            immediate_ko_threat=immediate_ko_threat,
            opponent_can_ko_next_turn=opponent_can_ko,
            i_can_ko_next_turn=i_can_ko,
            prize_point_pressure=prize_pressure,
            board_control=max(-1.0, min(1.0, board_control)),
            tempo_advantage=max(-1.0, min(1.0, tempo_advantage))
        )
    
    def _calculate_threat_modifier(self, threat_assessment: ThreatAssessment) -> float:
        """Calculate position score modifier based on threats (0.5 to 2.0)"""
        modifier = 1.0
        
        # Immediate threats significantly impact evaluation
        if threat_assessment.immediate_ko_threat:
            modifier *= 0.5  # Very bad position
        elif threat_assessment.i_can_ko_next_turn:
            modifier *= 1.5  # Good opportunity
        elif threat_assessment.opponent_can_ko_next_turn:
            modifier *= 0.7  # Dangerous position
        
        # Prize pressure impacts
        if threat_assessment.prize_point_pressure == ThreatLevel.CRITICAL:
            modifier *= 0.6  # Opponent about to win
        elif threat_assessment.prize_point_pressure == ThreatLevel.LOW and threat_assessment.board_control > 0:
            modifier *= 1.3  # I'm in control and winning
        
        return max(0.5, min(2.0, modifier))  # Clamp to reasonable range
    
    def _apply_phase_adjustments(self, score: float, phase: GamePhase) -> float:
        """Apply phase-specific score adjustments"""
        phase_multiplier = 1.0
        
        if phase == GamePhase.EARLY_GAME:
            # Early game: prioritize setup over aggression
            if score > 0:
                phase_multiplier = 0.9  # Slight discount on positive positions
        elif phase == GamePhase.LATE_GAME:
            # Late game: amplify position advantages/disadvantages
            if abs(score) > 50:
                phase_multiplier = 1.2  # Amplify strong positions
        
        return score * phase_multiplier
    
    def _recommend_strategy(self, position: BoardPosition, 
                          threat_assessment: ThreatAssessment, 
                          phase: GamePhase) -> str:
        """Recommend overall strategy based on evaluation"""
        # Handle critical situations first
        if threat_assessment.immediate_ko_threat:
            return "defensive"
        
        if threat_assessment.i_can_ko_next_turn:
            return "aggressive"
        
        if threat_assessment.prize_point_pressure == ThreatLevel.CRITICAL:
            return "desperate_defense"
        
        # Phase-based recommendations
        if phase == GamePhase.EARLY_GAME:
            if position.my_bench_count < 2:
                return "setup_focused"
            return "balanced_development"
        
        elif phase == GamePhase.LATE_GAME:
            if position.my_prize_points >= 2:
                return "close_out"
            elif position.opponent_prize_points >= 2:
                return "comeback_attempt"
            return "position_for_win"
        
        else:  # MID_GAME
            if threat_assessment.board_control > 0.3:
                return "press_advantage"
            elif threat_assessment.board_control < -0.3:
                return "stabilize_board"
            return "balanced"
    
    def _identify_key_factors(self, position: BoardPosition, 
                            threat_assessment: ThreatAssessment,
                            hp_score: float, prize_score: float, 
                            board_score: float, hand_score: float, 
                            tempo_score: float) -> List[str]:
        """Identify key factors affecting the position"""
        factors = []
        
        # Threat factors
        if threat_assessment.immediate_ko_threat:
            factors.append("IMMEDIATE KO THREAT")
        elif threat_assessment.i_can_ko_next_turn:
            factors.append("KO opportunity available")
        elif threat_assessment.opponent_can_ko_next_turn:
            factors.append("Opponent can KO next turn")
        
        # Position factors (only mention significant ones)
        if abs(hp_score) > 30:
            factors.append(f"HP advantage: {hp_score:+.0f}")
        
        if abs(prize_score) > 40:
            factors.append(f"Prize pressure: {prize_score:+.0f}")
        
        if abs(board_score) > 25:
            factors.append(f"Board control: {board_score:+.0f}")
        
        if abs(hand_score) > 20:
            factors.append(f"Hand advantage: {hand_score:+.0f}")
        
        if abs(tempo_score) > 25:
            factors.append(f"Tempo: {tempo_score:+.0f}")
        
        # General state factors
        if position.turn_number >= 20:
            factors.append("Late game - decisive actions needed")
        
        if position.my_bench_count == 0:
            factors.append("No bench Pokemon - vulnerable")
        
        return factors if factors else ["Balanced position"]