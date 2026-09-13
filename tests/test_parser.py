"""Tests for Graphix QASM parser."""

import math

import pytest
from graphix import ANGLE_PI, Axis, Instruction, rad_to_angle

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
    assert isinstance(instruction, Instruction.RZ)
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
    assert isinstance(instruction, Instruction.RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, 5 * ANGLE_PI / 4)


def test_parse_all_instructions() -> None:  # noqa: PLR0915
    """Test parse all instructions."""
    s = """
include "qelib1.inc";
qubit[3] q;
ccx q[0], q[1], q[2];
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
    assert isinstance(instruction, Instruction.CCX)
    assert instruction.target == 2
    assert instruction.controls == (0, 1)
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.CNOT)
    assert instruction.target == 1
    assert instruction.control == 0
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.SWAP)
    assert instruction.targets == (0, 1)
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.CZ)
    assert instruction.targets == (0, 1)
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.H)
    assert instruction.target == 0
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.S)
    assert instruction.target == 0
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.X)
    assert instruction.target == 0
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.Y)
    assert instruction.target == 0
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.Z)
    assert instruction.target == 0
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.RX)
    assert instruction.target == 0
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, ANGLE_PI / 4)
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.RY)
    assert instruction.target == 0
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, ANGLE_PI / 4)
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.RZ)
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
    assert isinstance(instruction, Instruction.RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, rad_to_angle(1))
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, rad_to_angle(1.5))
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, rad_to_angle(-1))
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, rad_to_angle(1 + 2))
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, rad_to_angle(1 - 2))
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, rad_to_angle(1 * 2))
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, rad_to_angle(1 / 2))
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, rad_to_angle(1 - (2 + 3)))
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, ANGLE_PI)
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.RZ)
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
    assert isinstance(instruction, Instruction.RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, ANGLE_PI / 4)
    with pytest.raises(StopIteration):
        next(iterator)


def test_gate_definition() -> None:
    """Test gate definition."""
    # Excerpt of https://openqasm.com/language/gates.html#defining-gates
    s = """
qubit[2] q;
gate cphase(θ) a, b
{
  rz(θ / 2) a;
  cx a, b;
  rz(-θ / 2) b;
  cx a, b;
  rz(θ / 2) b;
}
cphase(π / 2) q[0], q[1];
"""
    parser = OpenQASMParser()
    circuit = parser.parse_str(s)
    assert circuit.width == 2
    assert circuit.instruction == [
        Instruction.RZ(0, ANGLE_PI / 4),
        Instruction.CNOT(control=0, target=1),
        Instruction.RZ(1, -ANGLE_PI / 4),
        Instruction.CNOT(control=0, target=1),
        Instruction.RZ(1, ANGLE_PI / 4),
    ]


def test_measurement() -> None:
    """Test measurement."""
    s = """
include "stdgates.inc";
qubit q;
bit b;
b = measure q;
qreg qo;
creg bo;
measure qo -> bo;
qubit[2] qr;
bit[2] br;
br[0] = measure qr[0];
br[1] = measure qr[1];
qreg qr2[2];
creg br2[2];
br2 = measure qr2;
"""
    parser = OpenQASMParser()
    circuit = parser.parse_str(s)
    assert circuit.width == 6
    assert circuit.instruction == [
        Instruction.M(0, Axis.Z),
        Instruction.M(1, Axis.Z),
        Instruction.M(2, Axis.Z),
        Instruction.M(3, Axis.Z),
        Instruction.M(4, Axis.Z),
        Instruction.M(5, Axis.Z),
    ]
