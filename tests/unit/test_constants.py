import pytest
from modules.constants import DroneModes, GameMode

def test_drone_modes():
    assert DroneModes.ATTACK == "attack"
    assert DroneModes.SPREAD == "spread"
    assert DroneModes.PATROL == "patrol"
    
def test_game_modes():
    assert GameMode.RTS == "rts"
    assert GameMode.MISSION_PLANNING == "mission_planning"
