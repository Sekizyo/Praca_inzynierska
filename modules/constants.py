from enum import Enum


class DroneModes(str, Enum):
    ATTACK = "attack"
    SPREAD = "spread"

class GameMode(str, Enum):
    RTS = "rts"
    MISSION_PLANNING = "mission_planning"