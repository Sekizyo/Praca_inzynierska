import pytest
from modules.utils import run_every_n_calls

def test_run_every_n_calls():
    call_count = 0

    @run_every_n_calls(3)
    def my_func():
        nonlocal call_count
        call_count += 1
        return call_count

    assert my_func() == 1
    assert my_func() == 1
    assert my_func() == 2
    assert my_func() == 2
    assert my_func() == 2
    assert my_func() == 3
    
    