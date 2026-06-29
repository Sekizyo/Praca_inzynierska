"""Pytest configuration and shared fixtures."""

import pytest
import taichi as ti

@pytest.fixture(scope="session", autouse=True)
def taichi_init():
    ti.init(arch=ti.cpu, debug=True)
    yield
