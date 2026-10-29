"""Tests for Graphix QASM parser."""

from __future__ import annotations

import math

import numpy as np
import pytest
from graphix import ANGLE_PI, Axis, Instruction, rad_to_angle
from graphix.sim.statevec import Statevector
from graphix.states import BasicStates

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
cy q[0], q[1];
cz q[0], q[1];
ch q[0], q[1];
swap q[0], q[1];
cswap q[0], q[1], q[2];
h q[0];
s q[0];
sdg q[0];
t q[0];
tdg q[0];
sx q[0];
sxdg q[0];
x q[0];
y q[0];
z q[0];
p(pi/4) q[0];
rx(pi/4) q[0];
ry(pi/4) q[0];
rz(pi/4) q[0];
U(pi/4, pi/5, pi/6) q[0];
cp(pi/4) q[0], q[1];
crx(pi/4) q[0], q[1];
cry(pi/4) q[0], q[1];
crz(pi/4) q[0], q[1];
cu(pi/4, pi/5, pi/6, pi/7) q[0], q[1];
gphase(pi/3);
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
    assert isinstance(instruction, Instruction.CY)
    assert instruction.target == 1
    assert instruction.control == 0
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.CZ)
    assert instruction.target == 1
    assert instruction.control == 0
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.CH)
    assert instruction.target == 1
    assert instruction.control == 0
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.SWAP)
    assert instruction.targets == (0, 1)
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.CSWAP)
    assert instruction.control == 0
    assert instruction.targets == (1, 2)
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.H)
    assert instruction.target == 0
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.S)
    assert instruction.target == 0
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.SDG)
    assert instruction.target == 0
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.T)
    assert instruction.target == 0
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.TDG)
    assert instruction.target == 0
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.SX)
    assert instruction.target == 0
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.SXDG)
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
    assert isinstance(instruction, Instruction.P)
    assert instruction.target == 0
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, ANGLE_PI / 4)
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
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.U)
    assert instruction.target == 0
    assert isinstance(instruction.theta, float)
    assert math.isclose(instruction.theta, ANGLE_PI / 4)
    assert isinstance(instruction.phi, float)
    assert math.isclose(instruction.phi, ANGLE_PI / 5)
    assert isinstance(instruction.lambda_, float)
    assert math.isclose(instruction.lambda_, ANGLE_PI / 6)
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.CP)
    assert instruction.control == 0
    assert instruction.target == 1
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, ANGLE_PI / 4)
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.CRX)
    assert instruction.control == 0
    assert instruction.target == 1
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, ANGLE_PI / 4)
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.CRY)
    assert instruction.control == 0
    assert instruction.target == 1
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, ANGLE_PI / 4)
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.CRZ)
    assert instruction.control == 0
    assert instruction.target == 1
    assert isinstance(instruction.angle, float)
    assert math.isclose(instruction.angle, ANGLE_PI / 4)
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.CU)
    assert instruction.control == 0
    assert instruction.target == 1
    assert isinstance(instruction.theta, float)
    assert math.isclose(instruction.theta, ANGLE_PI / 4)
    assert isinstance(instruction.phi, float)
    assert math.isclose(instruction.phi, ANGLE_PI / 5)
    assert isinstance(instruction.lambda_, float)
    assert math.isclose(instruction.lambda_, ANGLE_PI / 6)
    assert isinstance(instruction.gamma, float)
    assert math.isclose(instruction.gamma, ANGLE_PI / 7)
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.GPHASE)
    assert instruction.angle == ANGLE_PI / 3
    with pytest.raises(StopIteration):
        next(iterator)


def test_u2() -> None:
    """Test parse compatibility gate u2."""
    s = """
qubit q;
u2(pi/3, pi/4) q;
"""
    parser = OpenQASMParser()
    circuit = parser.parse_str(s)
    assert circuit.width == 1
    assert circuit.instruction == [
        Instruction.U(target=0, theta=ANGLE_PI / 2, phi=ANGLE_PI / 3, lambda_=ANGLE_PI / 4),
        Instruction.GPHASE(-ANGLE_PI / 4),
        Instruction.GPHASE(-ANGLE_PI / 6),
        Instruction.GPHASE(-ANGLE_PI / 8),
    ]


def test_u3() -> None:
    """Test parse compatibility gate u3."""
    s = """
qubit q;
u3(pi/2, pi/3, pi/4) q;
"""
    parser = OpenQASMParser()
    circuit = parser.parse_str(s)
    assert circuit.width == 1
    assert circuit.instruction == [
        Instruction.U(target=0, theta=ANGLE_PI / 2, phi=ANGLE_PI / 3, lambda_=ANGLE_PI / 4),
        Instruction.GPHASE(-ANGLE_PI / 4),
        Instruction.GPHASE(-ANGLE_PI / 6),
        Instruction.GPHASE(-ANGLE_PI / 8),
    ]


def test_legacy_cx() -> None:
    """Test parse compatibility gate CX."""
    s = """
qubit[2] q;
CX q[0], q[1];
"""
    parser = OpenQASMParser()
    circuit = parser.parse_str(s)
    assert circuit.width == 2
    assert circuit.instruction == [Instruction.CNOT(control=0, target=1)]


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
gate cphase2(θ) a, b
{
  rz(θ / 2) a;
  CX a, b;
  rz(-θ / 2) b;
  CX a, b;
  rz(θ / 2) b;
}
cphase2(π / 2) q[0], q[1];
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


def test_gate_without_parameters() -> None:
    """Test gate without parameters."""
    s = """
qubit q;
gate fancyid a {
h a;
h a; }
fancyid q;
"""
    parser = OpenQASMParser()
    circuit = parser.parse_str(s)
    assert circuit.width == 1
    assert circuit.instruction == [Instruction.H(0), Instruction.H(0)]


def test_nested_gate_definitions() -> None:
    """Test nested gate definitions."""
    s = """
gate g1 a
{
  gate g2 b
  {
  }
}
"""
    parser = OpenQASMParser()
    with pytest.raises(
        TypeError,
        match="Only built-in gate statements and calls to previously defined gates can appear in body of gate definition or conditional",
    ):
        parser.parse_str(s)


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
        Instruction.M(2, Axis.Z),
        Instruction.CONDINSTR({0}, (Instruction.X(0),)),
        Instruction.M(0, Axis.Z),
        Instruction.CONDINSTR(
            {0, 1},
            (
                Instruction.X(1),
                Instruction.Z(1),
            ),
        ),
    ]


def test_redundant_if_statements() -> None:
    """Test redundant if statements."""
    s = """
include "stdgates.inc";
qubit[3] q;
bit[2] b;
b[0] = measure q[2];
b[1] = measure q[0];
if (b[0] ^ b[1] ^ b[0]) {
    x q[1];
 }
"""
    parser = OpenQASMParser()
    with pytest.warns(UserWarning, match=r"Redundant bits are removed from domains."):
        circuit = parser.parse_str(s)
    assert circuit.width == 3
    assert circuit.instruction == [
        Instruction.M(2, Axis.Z),
        Instruction.M(0, Axis.Z),
        Instruction.CONDINSTR({1}, (Instruction.X(1),)),
    ]


def test_void_if_statements() -> None:
    """Test if statements."""
    s = """
include "stdgates.inc";
qubit[3] q;
bit[2] b;
b[0] = measure q[2];
b[1] = measure q[0];
if (b[1] ^ b[1]) {
    z q[1];
 }
"""
    parser = OpenQASMParser()
    with (
        pytest.warns(UserWarning, match=r"Conditional instruction with empty condition dropped."),
        pytest.warns(UserWarning, match=r"Redundant bits are removed from domains."),
    ):
        circuit = parser.parse_str(s)
    assert circuit.width == 3
    assert circuit.instruction == [
        Instruction.M(2, Axis.Z),
        Instruction.M(0, Axis.Z),
        Instruction.Z(1),
    ]


def test_measurement_without_discard() -> None:
    """Test measurements without discard."""
    s = """
include "stdgates.inc";
qubit[2] q;
bit[2] b;
b[0] = measure q[0];
x q[0];
b[1] = measure q[0];
if (b[1]) {
    x q[1];
}
"""
    parser = OpenQASMParser(discard_measurements=False)
    circuit = parser.parse_str(s)
    assert circuit.width == 2
    assert circuit.instruction == [
        Instruction.M(0, Axis.Z, discard=False),
        Instruction.X(0),
        Instruction.M(0, Axis.Z, discard=False),
        Instruction.CONDINSTR({1}, (Instruction.X(1),)),
    ]
    result = circuit.simulate(input_state=[BasicStates.ZERO, BasicStates.ZERO], rng=np.random.default_rng(42))
    assert result.classical_measures == (0, 1)
    assert result.state.isclose(Statevector(data=[BasicStates.ONE, BasicStates.ONE]))


def test_measured_qubit_discarded() -> None:
    """Test that measured qubits cannot be used afterwards by default."""
    s = """
include "stdgates.inc";
qubit q;
bit b;
b = measure q;
x q;
"""
    parser = OpenQASMParser()
    with pytest.raises(ValueError, match=r"Qubit 0 is not an active qubit."):
        parser.parse_str(s)
