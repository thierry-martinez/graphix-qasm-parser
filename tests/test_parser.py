"""Tests for Graphix QASM parser."""

import math
from math import pi

import pytest
from graphix.fundamentals import ANGLE_PI, angle_of_rad
from graphix.instruction import CCX, CNOT, CZ, RX, RY, RZ, RZZ, SWAP, H, S, X, Y, Z

from graphix_qasm_parser import OpenQASMParser


def test_parse_simple_circuit() -> None:
    """Test parse simple circuit."""
    s = """
include "qelib1.inc";
qubit q;
rz(5*pi/4) q;
"""
    parser = OpenQASMParser()
    circuit = parser.parse_str(s)
    assert circuit.width == 1
    assert len(circuit.instruction) == 1
    instruction = circuit.instruction[0]
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, 5 * ANGLE_PI / 4)


def test_parse_simple_circuit_old_syntax() -> None:
    """Test parse simple circuit."""
    s = """
include "qelib1.inc";
qreg q;
rz(5*pi/4) q;
"""
    parser = OpenQASMParser()
    circuit = parser.parse_str(s)
    assert circuit.width == 1
    assert len(circuit.instruction) == 1
    instruction = circuit.instruction[0]
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, 5 * ANGLE_PI / 4)


def test_parse_all_instructions() -> None:  # noqa: PLR0915
    """Test parse all instructions."""
    s = """
include "qelib1.inc";
qubit[3] q;
ccx q[0], q[1], q[2];
crz(pi/3) q[0], q[1];
cx q[0], q[1];
swap q[0], q[1];
cz q[0], q[1];
h q[0];
s q[0];
x q[0];
y q[0];
z q[0];
rx(pi/4) q[0];
ry(pi/4) q[0];
rz(pi/4) q[0];
"""
    parser = OpenQASMParser()
    circuit = parser.parse_str(s)
    assert circuit.width == 3
    iterator = iter(circuit.instruction)
    instruction = next(iterator)
    assert isinstance(instruction, CCX)
    assert instruction.target == 2
    assert instruction.controls == (0, 1)
    instruction = next(iterator)
    assert isinstance(instruction, RZZ)
    assert instruction.target == 1
    assert instruction.control == 0
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, ANGLE_PI / 3)
    instruction = next(iterator)
    assert isinstance(instruction, CNOT)
    assert instruction.target == 1
    assert instruction.control == 0
    instruction = next(iterator)
    assert isinstance(instruction, SWAP)
    assert instruction.targets == (0, 1)
    instruction = next(iterator)
    assert isinstance(instruction, CZ)
    assert instruction.targets == (0, 1)
    instruction = next(iterator)
    assert isinstance(instruction, H)
    assert instruction.target == 0
    instruction = next(iterator)
    assert isinstance(instruction, S)
    assert instruction.target == 0
    instruction = next(iterator)
    assert isinstance(instruction, X)
    assert instruction.target == 0
    instruction = next(iterator)
    assert isinstance(instruction, Y)
    assert instruction.target == 0
    instruction = next(iterator)
    assert isinstance(instruction, Z)
    assert instruction.target == 0
    instruction = next(iterator)
    assert isinstance(instruction, RX)
    assert instruction.target == 0
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, ANGLE_PI / 4)
    instruction = next(iterator)
    assert isinstance(instruction, RY)
    assert instruction.target == 0
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, ANGLE_PI / 4)
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert instruction.target == 0
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, ANGLE_PI / 4)
    with pytest.raises(StopIteration):
        next(iterator)


def test_parse_all_expressions() -> None:
    """Test parse all expressions."""
    s = """
include "qelib1.inc";
qubit q;
rz((1)) q;
rz(1.5) q;
rz(- 1) q;
rz(1 + 2) q;
rz(1 - 2) q;
rz(1 * 2) q;
rz(1 / 2) q;
rz(1 - (2 + 3)) q;
rz(pi) q;
rz(π) q;
"""
    parser = OpenQASMParser()
    circuit = parser.parse_str(s)
    assert circuit.width == 1
    iterator = iter(circuit.instruction)
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, angle_of_rad(1))
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, angle_of_rad(1.5))
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, angle_of_rad(-1))
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, angle_of_rad(1 + 2))
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, angle_of_rad(1 - 2))
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, angle_of_rad(1 * 2))
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, angle_of_rad(1 / 2))
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, angle_of_rad(1 - (2 + 3)))
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, ANGLE_PI)
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, ANGLE_PI)
    with pytest.raises(StopIteration):
        next(iterator)


def test_const_declarations() -> None:
    """Test constant declarations."""
    s = """
include "qelib1.inc";
const int SIZE = 1;
const angle alpha = pi / 4;
qubit[SIZE] q;
rz(alpha) q[0];
"""
    parser = OpenQASMParser()
    circuit = parser.parse_str(s)
    assert circuit.width == 1
    iterator = iter(circuit.instruction)
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, ANGLE_PI / 4)
    with pytest.raises(StopIteration):
        next(iterator)
