"""
Standard Effect Handlers
Common effects implemented using the registry pattern
"""

from typing import List
import random
from simulator.core.effect_registry import (
    effect_registry, EffectContext, EffectResult,
    damage_effect, healing_effect, status_effect, energy_effect, coin_flip_effect, special_effect
)
from simulator.core.status_conditions import StatusCondition


# Damage Effects
@damage_effect("damage_bonus", "Add bonus damage to attack")
def damage_bonus_handler(context: EffectContext) -> EffectResult:
    """Add flat bonus damage"""
    bonus = context.parameters.get('amount', 0)
    return EffectResult(
        success=True,
        damage_modifier=bonus,
        description=f"Damage bonus: +{bonus}"
    )


@damage_effect("energy_scaling_damage", "Damage scales with energy count")
def energy_scaling_damage_handler(context: EffectContext) -> EffectResult:
    """Damage based on energy attached"""
    damage_per_energy = context.parameters.get('damage_per_energy', 10)
    target = context.parameters.get('target', 'opponent_active')
    
    if target == 'opponent_active' and context.target_pokemon:
        energy_count = len(context.target_pokemon.energy_attached)
    elif target == 'self' and context.source_pokemon:
        energy_count = len(context.source_pokemon.energy_attached)
    else:
        energy_count = 0
    
    bonus_damage = energy_count * damage_per_energy
    return EffectResult(
        success=True,
        damage_modifier=bonus_damage,
        description=f"Energy scaling: +{bonus_damage} damage ({energy_count} energy × {damage_per_energy})"
    )


@damage_effect("conditional_damage", "Conditional damage bonus")
def conditional_damage_handler(context: EffectContext) -> EffectResult:
    """Conditional damage based on game state"""
    condition = context.parameters.get('condition')
    bonus = context.parameters.get('bonus_damage', 0)
    
    condition_met = False
    condition_description = ""
    
    if condition == 'special_condition':
        if context.target_pokemon and hasattr(context.target_pokemon, 'status_conditions'):
            condition_met = len(context.target_pokemon.status_conditions) > 0
            condition_description = "target has special condition"
    
    elif condition == 'opponent_is_basic':
        if context.target_pokemon and hasattr(context.target_pokemon.card, 'card_type'):
            condition_met = 'basic' in context.target_pokemon.card.card_type.lower()
            condition_description = "target is Basic Pokemon"
    
    elif condition == 'energy_condition':
        required_energy = context.parameters.get('energy_count', 1)
        actual_energy = len(context.source_pokemon.energy_attached) if context.source_pokemon else 0
        condition_met = actual_energy >= required_energy
        condition_description = f"has {required_energy}+ energy"
    
    elif condition == 'damage_condition':
        if context.source_pokemon:
            condition_met = context.source_pokemon.current_hp < context.source_pokemon.card.hp
            condition_description = "Pokemon has damage"
    
    if condition_met:
        return EffectResult(
            success=True,
            damage_modifier=bonus,
            description=f"Conditional bonus ({condition_description}): +{bonus} damage"
        )
    else:
        return EffectResult(
            success=True,
            damage_modifier=0,
            description=f"Condition not met ({condition_description}): no bonus"
        )


# Healing Effects
@healing_effect("heal", "Heal specific amount of damage")
def heal_handler(context: EffectContext) -> EffectResult:
    """Heal fixed amount of damage"""
    heal_amount = context.parameters.get('amount', 0)
    target = context.parameters.get('target', 'self')
    
    target_pokemon = context.source_pokemon if target == 'self' else context.target_pokemon
    if not target_pokemon:
        return EffectResult(success=False, description="No target for healing")
    
    old_hp = target_pokemon.current_hp
    actual_healed = target_pokemon.heal(heal_amount)
    
    return EffectResult(
        success=True,
        healing_amount=actual_healed,
        description=f"Healed {actual_healed} damage from {target_pokemon.card.name}"
    )


@healing_effect("full_heal", "Remove all damage from Pokemon")
def full_heal_handler(context: EffectContext) -> EffectResult:
    """Fully heal a Pokemon"""
    target = context.parameters.get('target', 'self')
    target_pokemon = context.source_pokemon if target == 'self' else context.target_pokemon
    
    if not target_pokemon:
        return EffectResult(success=False, description="No target for healing")
    
    old_hp = target_pokemon.current_hp
    target_pokemon.current_hp = target_pokemon.card.hp
    actual_healed = target_pokemon.current_hp - old_hp
    
    return EffectResult(
        success=True,
        healing_amount=actual_healed,
        description=f"Fully healed {target_pokemon.card.name} ({actual_healed} damage removed)"
    )


# Status Effects
@status_effect("apply_burn", "Apply burn status condition")
def apply_burn_handler(context: EffectContext) -> EffectResult:
    """Apply burn status to target"""
    target_pokemon = context.target_pokemon
    if not target_pokemon:
        return EffectResult(success=False, description="No target for burn")
    
    # Simulate status manager application
    if not hasattr(target_pokemon, 'status_conditions'):
        target_pokemon.status_conditions = []
    
    # Check if already burned
    for status in target_pokemon.status_conditions:
        if hasattr(status, 'condition') and status.condition == StatusCondition.BURNED:
            return EffectResult(success=False, description="Target already burned")
    
    # Add burn status (simplified)
    from simulator.core.status_conditions import StatusEffect
    burn_status = StatusEffect(
        condition=StatusCondition.BURNED,
        damage_per_turn=20,
        applied_turn=context.battle_context.get('turn', 1)
    )
    target_pokemon.status_conditions.append(burn_status)
    
    return EffectResult(
        success=True,
        status_effects=[f"Applied burn to {target_pokemon.card.name}"],
        description=f"Burned {target_pokemon.card.name}"
    )


@status_effect("apply_poison", "Apply poison status condition")
def apply_poison_handler(context: EffectContext) -> EffectResult:
    """Apply poison status to target"""
    target_pokemon = context.target_pokemon
    if not target_pokemon:
        return EffectResult(success=False, description="No target for poison")
    
    if not hasattr(target_pokemon, 'status_conditions'):
        target_pokemon.status_conditions = []
    
    # Check if already poisoned
    for status in target_pokemon.status_conditions:
        if hasattr(status, 'condition') and status.condition == StatusCondition.POISONED:
            return EffectResult(success=False, description="Target already poisoned")
    
    # Add poison status
    from simulator.core.status_conditions import StatusEffect
    poison_status = StatusEffect(
        condition=StatusCondition.POISONED,
        damage_per_turn=10,
        applied_turn=context.battle_context.get('turn', 1)
    )
    target_pokemon.status_conditions.append(poison_status)
    
    return EffectResult(
        success=True,
        status_effects=[f"Applied poison to {target_pokemon.card.name}"],
        description=f"Poisoned {target_pokemon.card.name}"
    )


@status_effect("apply_sleep", "Apply sleep status condition") 
def apply_sleep_handler(context: EffectContext) -> EffectResult:
    """Apply sleep status to target (like Popplio's Sing ability)"""
    target_pokemon = context.target_pokemon
    if not target_pokemon:
        return EffectResult(success=False, description="No target for sleep")
    
    if not hasattr(target_pokemon, 'status_conditions'):
        target_pokemon.status_conditions = []
    
    # Check if already asleep
    for status in target_pokemon.status_conditions:
        if hasattr(status, 'condition') and status.condition == StatusCondition.ASLEEP:
            return EffectResult(success=False, description="Target already asleep")
    
    # Add sleep status
    from simulator.core.status_conditions import StatusEffect
    sleep_status = StatusEffect(
        condition=StatusCondition.ASLEEP,
        damage_per_turn=0,
        applied_turn=context.battle_context.get('turn', 1)
    )
    target_pokemon.status_conditions.append(sleep_status)
    
    return EffectResult(
        success=True,
        status_effects=[f"Applied sleep to {target_pokemon.card.name}"],
        description=f"{target_pokemon.card.name} is now asleep"
    )


# Coin Flip Effects
@coin_flip_effect("flip_for_bonus", "Flip coin for damage bonus")
def flip_for_bonus_handler(context: EffectContext) -> EffectResult:
    """Flip coin for damage bonus"""
    bonus_damage = context.parameters.get('bonus_damage', 0)
    success = random.random() < 0.5  # 50% chance
    
    if success:
        return EffectResult(
            success=True,
            damage_modifier=bonus_damage,
            description=f"Coin flip: Heads! +{bonus_damage} damage"
        )
    else:
        return EffectResult(
            success=True,
            damage_modifier=0,
            description="Coin flip: Tails! No bonus damage"
        )


@coin_flip_effect("flip_scaling", "Multiple coin flips for scaling damage")
def flip_scaling_handler(context: EffectContext) -> EffectResult:
    """Flip multiple coins for scaling damage"""
    coin_count = context.parameters.get('coin_count', 1)
    damage_per_heads = context.parameters.get('damage_per_heads', 10)
    
    heads_count = 0
    for _ in range(coin_count):
        if random.random() < 0.5:
            heads_count += 1
    
    total_bonus = heads_count * damage_per_heads
    
    return EffectResult(
        success=True,
        damage_modifier=total_bonus,
        description=f"Flipped {coin_count} coins, got {heads_count} heads for {total_bonus} bonus damage"
    )


@coin_flip_effect("flip_variable_count", "Flip coins based on game state")
def flip_variable_count_handler(context: EffectContext) -> EffectResult:
    """Flip variable number of coins based on game state (like bench Pokemon count)"""
    count_source = context.parameters.get('count_source', 'bench_pokemon')
    damage_per_heads = context.parameters.get('damage_per_heads', 10)
    
    # Determine coin count
    coin_count = 0
    if count_source == 'bench_pokemon':
        attacker = context.battle_context.get('attacker')
        if attacker and hasattr(attacker, 'bench'):
            coin_count = sum(1 for pokemon in attacker.bench if pokemon is not None)
    
    if coin_count == 0:
        return EffectResult(
            success=True,
            damage_modifier=0,
            description="No coins to flip (no bench Pokemon)"
        )
    
    # Flip coins
    heads_count = 0
    for _ in range(coin_count):
        if random.random() < 0.5:
            heads_count += 1
    
    total_bonus = heads_count * damage_per_heads
    
    return EffectResult(
        success=True,
        damage_modifier=total_bonus,
        description=f"Flipped {coin_count} coins (one per bench Pokemon), got {heads_count} heads for {total_bonus} bonus damage"
    )


# Energy Effects
@energy_effect("attach_energy", "Attach energy to Pokemon")
def attach_energy_handler(context: EffectContext) -> EffectResult:
    """Attach energy to Pokemon"""
    energy_type = context.parameters.get('energy_type', 'Colorless')
    amount = context.parameters.get('amount', 1)
    target = context.parameters.get('target', 'self')
    
    target_pokemon = context.source_pokemon if target == 'self' else context.target_pokemon
    if not target_pokemon:
        return EffectResult(success=False, description="No target for energy attachment")
    
    # Add to energy_attached list
    if not hasattr(target_pokemon, 'energy_attached'):
        target_pokemon.energy_attached = []
    
    for _ in range(amount):
        target_pokemon.energy_attached.append(energy_type)
    
    return EffectResult(
        success=True,
        energy_changes=[{
            'type': 'attach',
            'target': target,
            'energy_type': energy_type,
            'amount': amount
        }],
        description=f"Attached {amount}x {energy_type} energy to {target_pokemon.card.name}"
    )


@energy_effect("discard_energy", "Remove energy from Pokemon")
def discard_energy_handler(context: EffectContext) -> EffectResult:
    """Remove energy from Pokemon"""
    amount = context.parameters.get('amount', 1)
    target = context.parameters.get('target', 'self')
    
    target_pokemon = context.source_pokemon if target == 'self' else context.target_pokemon
    if not target_pokemon or not hasattr(target_pokemon, 'energy_attached'):
        return EffectResult(success=False, description="No energy to discard")
    
    # Remove energy
    energy_removed = min(amount, len(target_pokemon.energy_attached))
    for _ in range(energy_removed):
        if target_pokemon.energy_attached:
            target_pokemon.energy_attached.pop()
    
    return EffectResult(
        success=True,
        energy_changes=[{
            'type': 'discard',
            'target': target,
            'amount': energy_removed
        }],
        description=f"Discarded {energy_removed} energy from {target_pokemon.card.name}"
    )


# Special Effects
@special_effect("draw_cards", "Draw cards from deck")
def draw_cards_handler(context: EffectContext) -> EffectResult:
    """Draw cards from deck"""
    amount = context.parameters.get('amount', 1)
    
    # This would require game state access to modify hand/deck
    # For now, just return a description
    return EffectResult(
        success=True,
        additional_effects=[f"Draw {amount} cards"],
        description=f"Draw {amount} cards effect triggered"
    )


@special_effect("search_deck", "Search deck for specific cards")
def search_deck_handler(context: EffectContext) -> EffectResult:
    """Search deck for cards"""
    search_type = context.parameters.get('search_type', 'any')
    amount = context.parameters.get('amount', 1)
    
    return EffectResult(
        success=True,
        additional_effects=[f"Search deck for {amount} {search_type} cards"],
        description=f"Search deck effect triggered"
    )


# Trainer Card Effects
@special_effect("professors_research", "Discard hand and draw 7 cards")
def professors_research_handler(context: EffectContext) -> EffectResult:
    """Professor's Research - Discard your hand and draw 7 cards"""
    return EffectResult(
        success=True,
        additional_effects=["Discard hand", "Draw 7 cards"],
        description="Professor's Research: Discard hand and draw 7 cards"
    )


@special_effect("pokeball", "Search deck for a Pokemon")  
def pokeball_handler(context: EffectContext) -> EffectResult:
    """Pokeball - Search your deck for a Pokemon"""
    return EffectResult(
        success=True,
        additional_effects=["Search deck for 1 Pokemon"],
        description="Pokeball: Search deck for a Pokemon"
    )


@special_effect("potion", "Heal 20 damage from a Pokemon")
def potion_handler(context: EffectContext) -> EffectResult:
    """Potion - Heal 20 damage from 1 of your Pokemon"""
    target_pokemon = context.parameters.get('target_pokemon') or context.source_pokemon
    if not target_pokemon:
        return EffectResult(success=False, description="No target for Potion")
    
    old_hp = target_pokemon.current_hp
    actual_healed = target_pokemon.heal(20)
    
    return EffectResult(
        success=True,
        healing_amount=actual_healed,
        description=f"Potion: Healed {actual_healed} damage from {target_pokemon.card.name}"
    )


@special_effect("switch", "Switch your Active Pokemon with a Benched Pokemon")
def switch_handler(context: EffectContext) -> EffectResult:
    """Switch - Switch your Active Pokemon with a Benched Pokemon"""
    return EffectResult(
        success=True,
        additional_effects=["Switch Active Pokemon with Bench Pokemon"],
        description="Switch: Switch Active Pokemon with Benched Pokemon"
    )


@special_effect("energy_search", "Search deck for a basic Energy card")
def energy_search_handler(context: EffectContext) -> EffectResult:
    """Energy Search - Search your deck for a basic Energy card"""
    return EffectResult(
        success=True,
        additional_effects=["Search deck for 1 basic Energy card"],
        description="Energy Search: Search deck for a basic Energy card"
    )


@special_effect("bill", "Draw 2 cards")
def bill_handler(context: EffectContext) -> EffectResult:
    """Bill - Draw 2 cards"""
    return EffectResult(
        success=True,
        additional_effects=["Draw 2 cards"],
        description="Bill: Draw 2 cards"
    )


@special_effect("computer_search", "Search deck for any card")
def computer_search_handler(context: EffectContext) -> EffectResult:
    """Computer Search - Search your deck for any card (discard 2 cards)"""
    return EffectResult(
        success=True,
        additional_effects=["Discard 2 cards from hand", "Search deck for any card"],
        description="Computer Search: Discard 2 cards, search for any card"
    )