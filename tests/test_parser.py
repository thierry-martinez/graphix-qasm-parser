"""Tests for Graphix QASM parser."""

import math

import pytest
from graphix.instruction import CCX, CNOT, RX, RY, RZ, RZZ, SWAP, H, S, X, Y, Z

from graphix_qasm_parser import OpenQASMParser


def test_parse_simple_circuit() -> None:
    """Test parse simple circuit."""
    s = """
include "qelib1.inc";
qreg q[1];
rz(5*pi/4) q[0];
"""
    parser = OpenQASMParser()
    circuit = parser.parse_str(s)
    assert circuit.width == 1
    assert len(circuit.instruction) == 1
    instruction = circuit.instruction[0]
    assert isinstance(instruction, RZ)
    assert math.isclose(instruction.angle, 5 * math.pi / 4)


def test_parse_all_instructions() -> None:  # noqa: PLR0915
    """Test parse all instructions."""
    s = """
include "qelib1.inc";
qreg q[3];
ccx q[0], q[1], q[2];
crz(pi/3) q[0], q[1];
cx q[0], q[1];
swap q[0], q[1];
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
    assert math.isclose(instruction.angle, math.pi / 3)
    instruction = next(iterator)
    assert isinstance(instruction, CNOT)
    assert instruction.target == 1
    assert instruction.control == 0
    instruction = next(iterator)
    assert isinstance(instruction, SWAP)
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
    assert math.isclose(instruction.angle, math.pi / 4)
    instruction = next(iterator)
    assert isinstance(instruction, RY)
    assert instruction.target == 0
    assert math.isclose(instruction.angle, math.pi / 4)
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert instruction.target == 0
    assert math.isclose(instruction.angle, math.pi / 4)
    with pytest.raises(StopIteration):
        next(iterator)
