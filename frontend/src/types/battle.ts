// Battle Simulator Types
// Corresponds to the Python battle simulator backend

export interface BattleCard {
  id: number;
  name: string;
  card_type: string;
  energy_type: string;
  hp: number | null;
  attacks: Attack[];
  abilities: Ability[];
  weakness: string | null;
  retreat_cost: number | null;
  evolution_stage: number | null;
  evolves_from: string | null;
  is_ex: boolean;
  rarity: string;
  set_name: string;
  firebase_image_url?: string;
}

export interface Attack {
  name: string;
  cost: string[];
  damage: number;
  effect_text: string;
  parsed_effects: ParsedEffect[];
}

export interface Ability {
  name: string;
  effect_text: string;
  parsed_effects: ParsedEffect[];
  type: string;
}

export interface ParsedEffect {
  type: string;
  confidence: number;
  parameters: Record<string, any>;
  raw_text: string;
}

export interface BattlePokemon {
  card: BattleCard;
  current_hp: number;
  max_hp: number;
  status_conditions: StatusCondition[];
  attached_energy: string[];
  damage_taken: number;
}

export interface StatusCondition {
  condition: 'burned' | 'poisoned' | 'asleep' | 'paralyzed' | 'confused';
  turns_remaining: number | null;
  damage_per_turn: number;
  applied_turn: number;
}

export interface GameState {
  battle_id: string;
  current_turn: number;
  current_player: 0 | 1;
  phase: 'setup' | 'draw' | 'main' | 'attack' | 'end' | 'finished';
  players: PlayerState[];
  winner: number | null;
  is_tie: boolean;
}

export interface PlayerState {
  player_id: number;
  active_pokemon: BattlePokemon | null;
  bench: BattlePokemon[];
  hand: BattleCard[];
  deck: BattleCard[];
  discard: BattleCard[];
  prize_points: number;
  energy_attached_this_turn: boolean;
  setup_ready: boolean;
  energy_per_turn: number;
}

export interface BattleAction {
  type: 'attack' | 'switch' | 'pass_turn' | 'attach_energy' | 'use_ability' | 'setup_ready' | 'play_pokemon' | 'start_game' | 'draw_card';
  player_id: number;
  data: Record<string, any>;
}

export interface EffectResult {
  success: boolean;
  total_damage: number;
  coin_results: string[];
  description: string;
  status_applied?: string;
  energy_generated?: number;
  requires_distribution?: boolean;
}

// UI-specific types
export interface BattleUIState {
  mode: 'manual' | 'auto_sim';
  auto_sim_speed: 1 | 2 | 4 | 8;
  selected_card: BattleCard | null;
  selected_attack: number | null;
  battle_log: BattleLogEntry[];
  connected: boolean;
  loading: boolean;
}

export interface BattleLogEntry {
  id: string;
  timestamp: number;
  type: 'action' | 'effect' | 'damage' | 'status' | 'game';
  message: string;
  details?: Record<string, any>;
}

export interface DeckConfiguration {
  name: string;
  energy_type: string;
  cards: BattleCard[];
}