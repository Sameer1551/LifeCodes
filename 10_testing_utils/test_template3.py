#!/usr/bin/env python3
"""
test_template.py
----------------
Modern testing template using Pytest.
This template covers Fixtures, Parametrization, Mocking, and Temporary Files.

Usage:
    pip install pytest pytest-mock requests
    pytest test_template.py -v
"""

import pytest
import json
from pathlib import Path

# --- Example Code Under Test ---

class Calculator:
    def add(self, a, b): return a + b
    def div(self, a, b):
        if b == 0: raise ValueError("Cannot divide by zero")
        return a / b

class UserService:
    def __init__(self, api_client):
        self.client = api_client
    
    def get_user(self, user_id):
        resp = self.client.get(f"/users/{user_id}")
        if resp.status_code == 200:
            return resp.json()
        return None

# --- Fixtures ---

@pytest.fixture
def calc():
    """Provides a fresh Calculator instance for each test."""
    return Calculator()

@pytest.fixture
def temp_config_file(tmp_path):
    """
    Pytest's tmp_path fixture provides a temporary directory unique to this test invocation.
    Perfect for file I/O tests.
    """
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"debug": True, "version": "1.0"}))
    return config_path

# --- Basic Tests ---

def test_addition(calc):
    assert calc.add(2, 3) == 5
    assert calc.add(-1, 1) == 0

def test_division(calc):
    assert calc.div(10, 2) == 5.0

def test_division_by_zero(calc):
    # Pytest context manager for exceptions
    with pytest.raises(ValueError) as excinfo:
        calc.div(1, 0)
    assert "divide by zero" in str(excinfo.value)

# --- Parametrized Tests ---
# Run the same test logic with multiple inputs

@pytest.mark.parametrize("a,b,expected", [
    (2, 3, 5),
    (0, 0, 0),
    (-1, -5, -6),
    (100, 200, 300),
])
def test_addition_various(calc, a, b, expected):
    assert calc.add(a, b) == expected

# --- Mocking Tests ---
# Use pytest-mock (wrapper around unittest.mock) for patching

def test_get_user_success(mocker):
    # Create a mock for the API client
    mock_client = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 1, "name": "Alice"}
    
    # Configure the mock's get method to return our mock response
    mock_client.get.return_value = mock_response

    service = UserService(mock_client)
    user = service.get_user(1)

    assert user == {"id": 1, "name": "Alice"}
    mock_client.get.assert_called_once_with("/users/1")

def test_get_user_failure(mocker):
    mock_client = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.status_code = 404
    
    mock_client.get.return_value = mock_response
    
    service = UserService(mock_client)
    user = service.get_user(999)
    
    assert user is None

# --- File I/O Tests ---

def test_read_config(temp_config_file):
    # This test uses the fixture created above
    data = json.loads(temp_config_file.read_text())
    assert data["debug"] == True
    assert data["version"] == "1.0"

def test_write_config(temp_config_file):
    # We can write to the same temp file
    new_data = {"debug": False, "version": "2.0"}
    temp_config_file.write_text(json.dumps(new_data))
    
    content = json.loads(temp_config_file.read_text())
    assert content["version"] == "2.0"
