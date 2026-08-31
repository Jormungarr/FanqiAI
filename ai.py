import random
from typing import Tuple
try:
    from .engine import GameState
except ImportError:
    from engine import GameState


class RandomAgent:
    def __init__(self, color: str, seed: int | None = None):
        self.color = color
        self.rng = random.Random(seed)

    def select(self, state: GameState) -> Tuple:
        acts = state.get_legal_actions(self.color)
        if not acts:
            return None
        return self.rng.choice(acts)


class PreferHighValueAgent(RandomAgent):
    """Prefer flips that reveal high-value pieces and prefer captures by value."""
    def select(self, state: GameState):
        acts = state.get_legal_actions(self.color)
        if not acts:
            return None
        # prefer capture/cannon actions
        capture_acts = [a for a in acts if a[0] in ('capture','cannon')]
        if capture_acts:
            return random.choice(capture_acts)
        # prefer flip that is adjacent to known high-value? simple: random flip
        flip_acts = [a for a in acts if a[0]=='flip']
        if flip_acts:
            return random.choice(flip_acts)
        return random.choice(acts)
