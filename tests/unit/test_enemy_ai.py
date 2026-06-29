import pytest
from unittest.mock import Mock, MagicMock
from modules.enemy_ai import DefendingAI
from modules.constants import DroneModes

def test_defending_ai_initialization():
    mock_swarm = MagicMock()
    mock_preset = MagicMock()
    mock_preset.map_size = 1000
    mock_preset.ai_engage_distance = 200
    mock_preset.ai_agression_threshold = 70
    mock_preset.ai_path_normalized = [(100, 100, 100, None)]
    mock_preset.ai_evaluate_state = 1
    mock_preset.ai_execute_state = 1
    
    ai = DefendingAI(mock_swarm, mock_preset)
    assert ai.state == DroneModes.ATTACK
    assert ai.engage_distance == 200

def test_defending_ai_state_evaluation():
    mock_swarm = MagicMock()
    mock_player_swarm = MagicMock()
    
    mock_preset = MagicMock()
    mock_preset.map_size = 1000
    mock_preset.ai_engage_distance = 200
    mock_preset.ai_agression_threshold = 70
    mock_preset.ai_path_normalized = []
    mock_preset.ai_evaluate_state = 1
    mock_preset.ai_execute_state = 1
    
    ai = DefendingAI(mock_swarm, mock_preset)
    
    # Enemy center
    mock_swarm.get_swarm_center.return_value = [0, 0, 0]
    
    # Player close (distance 100 < engage_distance 200)
    mock_player_swarm.get_swarm_center.return_value = [100, 0, 0]
    
    ai._evaluate_state(mock_player_swarm, 50.0)
    assert ai.state == DroneModes.ATTACK
    
    # Player far (distance 500 > engage_distance), Player territory high -> Spread
    mock_player_swarm.get_swarm_center.return_value = [500, 0, 0]
    ai._evaluate_state(mock_player_swarm, 75.0)  # > aggression_threshold 70
    assert ai.state == DroneModes.SPREAD
    
    # Player far, Player territory low -> Patrol
    ai._evaluate_state(mock_player_swarm, 50.0)
    assert ai.state == DroneModes.PATROL

def test_defending_ai_execute_state():
    mock_swarm = MagicMock()
    mock_player_swarm = MagicMock()
    
    mock_preset = MagicMock()
    mock_preset.map_size = 1000
    mock_preset.ai_engage_distance = 200
    mock_preset.ai_agression_threshold = 70
    mock_preset.ai_path_normalized = []
    mock_preset.ai_evaluate_state = 1
    mock_preset.ai_execute_state = 1
    
    ai = DefendingAI(mock_swarm, mock_preset)
    
    # Test ATTACK execution
    ai.state = DroneModes.ATTACK
    mock_player_swarm.get_swarm_center.return_value = [100, 200, 300]
    ai._execute_state(mock_player_swarm)
    mock_swarm.set_target.assert_called_with(100, 200, 300)
    
    # Test PATROL execution
    ai.state = DroneModes.PATROL
    ai._execute_state(mock_player_swarm)
    mock_swarm.follow_path.assert_called_once()
