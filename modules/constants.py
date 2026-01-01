from enum import Enum


class DroneModes(str, Enum):
    ATTACK = "attack"
    SPREAD = "spread"
    PATROL = "patrol"


class AIState(str, Enum):
    PATROL = "patrol"
    ATTACK = "attack"
    SPREAD = "spread"