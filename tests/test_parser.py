"""Tests for Graphix QASM parser."""

from __future__ import annotations

import math

import pytest
from graphix.instruction import CCX, CNOT, RX, RY, RZ, SWAP, Axis, H, M, S, X, Y, Z

from graphix_qasm_parser import OpenQASMParser
from graphix_qasm_parser.parser import ANGLE_PI, CONDINSTR, CZ, HAS_CONDINSTR, HAS_CZ, rad_to_angle


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


def test_parse_all_instructions() -> None:
    """Test parse all instructions."""
    s = """
include "qelib1.inc";
qubit[3] q;
ccx q[0], q[1], q[2];
cx q[0], q[1];
swap q[0], q[1];
// cz q[0], q[1];
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


@pytest.mark.skipif(not HAS_CZ, reason="CZ instructions are not supported by graphix <= 0.3.3")
def test_parse_cz() -> None:
    """Test parse CZ instructions."""
    s = """
include "qelib1.inc";
qubit[2] q;
cz q[0], q[1];
"""
    parser = OpenQASMParser()
    circuit = parser.parse_str(s)
    assert circuit.width == 2
    iterator = iter(circuit.instruction)
    instruction = next(iterator)
    assert isinstance(instruction, CZ)
    assert instruction.targets == (0, 1)
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
    assert math.isclose(instruction.angle, rad_to_angle(1))
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, rad_to_angle(1.5))
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, rad_to_angle(-1))
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, rad_to_angle(1 + 2))
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, rad_to_angle(1 - 2))
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, rad_to_angle(1 * 2))
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, rad_to_angle(1 / 2))
    instruction = next(iterator)
    assert isinstance(instruction, RZ)
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, rad_to_angle(1 - (2 + 3)))
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
        M(0, Axis.Z),
        M(1, Axis.Z),
        M(2, Axis.Z),
        M(3, Axis.Z),
        M(4, Axis.Z),
        M(5, Axis.Z),
    ]


@pytest.mark.skipif(not HAS_CONDINSTR, reason="CONDINSTR instructions are not supported by graphix <= 0.4")
def test_if_statements() -> None:
    """Test if statements."""
    s = """
include "stdgates.inc";
qubit[3] q;
bit[2] b;
b[0] = measure q[2];
if (b[0]) {
    x q[0];
}
b[1] = measure q[0];
if (b[0] ^ b[1]) {
    x q[1];
    z q[1];
 }
"""
    parser = OpenQASMParser()
    circuit = parser.parse_str(s)
    assert circuit.width == 3
    assert circuit.instruction == [
        M(2, Axis.Z),
        CONDINSTR((X(0),), {2}),
        M(0, Axis.Z),
        CONDINSTR(
            (
                X(1),
                Z(1),
            ),
            {0, 2},
        ),
    ]
