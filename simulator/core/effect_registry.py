"""
Effect Handler Registry System
Inspired by the AngelFireLA Pokemon TCG Pocket Battle Simulator

This system allows for clean, modular effect handling with a decorator-based registry pattern.
"""

from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging


class EffectCategory(Enum):
    """Categories of effects for organization"""
    DAMAGE = "damage"
    HEALING = "healing"
    STATUS = "status"
    ENERGY = "energy"
    COIN_FLIP = "coin_flip"
    SEARCH = "search"
    DRAW = "draw"
    DISCARD = "discard"
    SPECIAL = "special"


@dataclass
class EffectContext:
    """Context passed to effect handlers"""
    source_pokemon: Any
    target_pokemon: Optional[Any] = None
    battle_context: Dict[str, Any] = None
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.battle_context is None:
            self.battle_context = {}
        if self.parameters is None:
            self.parameters = {}


@dataclass
class EffectResult:
    """Result returned by effect handlers"""
    success: bool
    damage_modifier: int = 0
    healing_amount: int = 0
    status_effects: List[str] = None
    energy_changes: List[Dict] = None
    additional_effects: List[str] = None
    description: str = ""
    
    def __post_init__(self):
        if self.status_effects is None:
            self.status_effects = []
        if self.energy_changes is None:
            self.energy_changes = []
        if self.additional_effects is None:
            self.additional_effects = []


class EffectRegistry:
    """Registry for effect handlers using decorator pattern"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._handlers: Dict[str, Callable] = {}
        self._categories: Dict[str, EffectCategory] = {}
        self._descriptions: Dict[str, str] = {}
    
    def register(self, effect_type: str, category: EffectCategory = EffectCategory.SPECIAL, 
                description: str = "") -> Callable:
        """Decorator to register an effect handler"""
        def decorator(func: Callable[[EffectContext], EffectResult]) -> Callable:
            self._handlers[effect_type] = func
            self._categories[effect_type] = category
            self._descriptions[effect_type] = description or f"Effect: {effect_type}"
            self.logger.debug(f"Registered effect handler: {effect_type} ({category.value})")
            return func
        return decorator
    
    def execute(self, effect_type: str, context: EffectContext) -> EffectResult:
        """Execute an effect by type"""
        handler = self._handlers.get(effect_type)
        if not handler:
            self.logger.warning(f"No handler found for effect type: {effect_type}")
            return EffectResult(
                success=False, 
                description=f"Unknown effect type: {effect_type}"
            )
        
        try:
            self.logger.debug(f"Executing effect: {effect_type}")
            result = handler(context)
            if result.success:
                self.logger.debug(f"Effect {effect_type} executed successfully: {result.description}")
            else:
                self.logger.warning(f"Effect {effect_type} failed: {result.description}")
            return result
            
        except Exception as e:
            self.logger.error(f"Effect handler {effect_type} crashed: {e}")
            return EffectResult(
                success=False,
                description=f"Effect handler error: {e}"
            )
    
    def has_handler(self, effect_type: str) -> bool:
        """Check if a handler exists for an effect type"""
        return effect_type in self._handlers
    
    def get_handlers_by_category(self, category: EffectCategory) -> List[str]:
        """Get all effect types in a category"""
        return [effect_type for effect_type, cat in self._categories.items() 
                if cat == category]
    
    def list_all_handlers(self) -> Dict[str, Dict[str, Any]]:
        """List all registered handlers with metadata"""
        return {
            effect_type: {
                'category': self._categories[effect_type].value,
                'description': self._descriptions[effect_type]
            }
            for effect_type in self._handlers.keys()
        }


# Global registry instance
effect_registry = EffectRegistry()


# Decorator shortcuts for common effect categories
def damage_effect(effect_type: str, description: str = ""):
    """Register a damage effect"""
    return effect_registry.register(effect_type, EffectCategory.DAMAGE, description)


def healing_effect(effect_type: str, description: str = ""):
    """Register a healing effect"""
    return effect_registry.register(effect_type, EffectCategory.HEALING, description)


def status_effect(effect_type: str, description: str = ""):
    """Register a status condition effect"""
    return effect_registry.register(effect_type, EffectCategory.STATUS, description)


def energy_effect(effect_type: str, description: str = ""):
    """Register an energy manipulation effect"""
    return effect_registry.register(effect_type, EffectCategory.ENERGY, description)


def coin_flip_effect(effect_type: str, description: str = ""):
    """Register a coin flip effect"""
    return effect_registry.register(effect_type, EffectCategory.COIN_FLIP, description)


def special_effect(effect_type: str, description: str = ""):
    """Register a special/unique effect"""
    return effect_registry.register(effect_type, EffectCategory.SPECIAL, description)