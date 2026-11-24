"""
Calculator Core Module.
Provides basic and advanced arithmetic operations with input validation.
"""
import math

class Calculator:
    def add(self, a: float, b: float) -> float:
        return a + b

    def subtract(self, a: float, b: float) -> float:
        return a - b

    def multiply(self, a: float, b: float) -> float:
        return a * b

    def divide(self, a: float, b: float) -> float:
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero.")
        return a / b

    def power(self, base: float, exponent: float) -> float:
        return math.pow(base, exponent)

    def square_root(self, val: float) -> float:
        if val < 0:
            raise ValueError("Cannot calculate square root of a negative number.")
        return math.sqrt(val)

    def factorial(self, n: int) -> int:
        if n < 0:
            raise ValueError("Factorial is not defined for negative numbers.")
        return math.factorial(n)
