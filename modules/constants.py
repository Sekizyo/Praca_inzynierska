from enum import Enum


class DroneModes(str, Enum):
    ATTACK = "attack"
    SPREAD = "spread"
    PATROL = "patrol"
