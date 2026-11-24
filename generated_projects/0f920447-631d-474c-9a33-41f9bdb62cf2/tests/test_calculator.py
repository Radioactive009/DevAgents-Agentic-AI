"""
Comprehensive Pytest Suite for Calculator.
"""
import pytest
from calculator import Calculator

@pytest.fixture
def calc():
    return Calculator()

def test_add(calc):
    assert calc.add(2, 3) == 5
    assert calc.add(-1, 1) == 0
    assert calc.add(0.5, 0.5) == 1.0

def test_subtract(calc):
    assert calc.subtract(10, 4) == 6
    assert calc.subtract(0, 5) == -5

def test_multiply(calc):
    assert calc.multiply(3, 4) == 12
    assert calc.multiply(-2, 3) == -6
    assert calc.multiply(5, 0) == 0

def test_divide(calc):
    assert calc.divide(10, 2) == 5.0
    assert calc.divide(7, 2) == 3.5

def test_divide_by_zero(calc):
    with pytest.raises(ZeroDivisionError):
        calc.divide(5, 0)

def test_power(calc):
    assert calc.power(2, 3) == 8.0
    assert calc.power(5, 0) == 1.0

def test_square_root(calc):
    assert calc.square_root(16) == 4.0
    assert calc.square_root(0) == 0.0
    with pytest.raises(ValueError):
        calc.square_root(-4)

def test_factorial(calc):
    assert calc.factorial(0) == 1
    assert calc.factorial(5) == 120
    with pytest.raises(ValueError):
        calc.factorial(-1)
