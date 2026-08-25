"""Tests for Graphix QASM parser."""

import math
from typing import TYPE_CHECKING

import pytest
from graphix.instruction import CCX, CNOT, RX, RY, RZ, SWAP, H, S, X, Y, Z

from graphix_qasm_parser import OpenQASMParser

if TYPE_CHECKING:
    # Compatibility with graphix <= 0.3.3
    # See https://github.com/TeamGraphix/graphix/pull/379

    from graphix import Instruction

    ANGLE_PI: float

    def rad_to_angle(angle: float) -> float:
        """Prototype for rad_to_angle."""
        ...

    CZ = SWAP
    HAS_CZ = True

    HAS_OPENQASM_GATES = True
else:
    try:
        from graphix.instruction import CZ

        HAS_CZ = True
    except ImportError:
        HAS_CZ = False

        if TYPE_CHECKING:
            import sys

            # We skip type-checking since pyright cannot figure out that
            # tests are skipped in this case.
            sys.exit(1)

    try:
        from graphix.fundamentals import ANGLE_PI, rad_to_angle
    except ImportError:
        from math import pi as ANGLE_PI  # noqa: N812

        if TYPE_CHECKING:
            import sys

            # We skip type-checking since pyright cannot figure out that
            # tests are skipped in this case.
            sys.exit(1)

    try:
        from graphix import Instruction

        _ = Instruction.P

        HAS_OPENQASM_GATES = True
    except ImportError:
        HAS_OPENQASM_GATES = False

        if TYPE_CHECKING:
            import sys

            # We skip type-checking since pyright cannot figure out that
            # tests are skipped in this case.
            sys.exit(1)


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
// cy q[0], q[1];
// cz q[0], q[1];
swap q[0], q[1];
// cswap q[0], q[1], q[2];
h q[0];
s q[0];
// sdg q[0];
// t q[0];
// tdg q[0];
// sx q[0];
// sxdg q[0];
x q[0];
y q[0];
z q[0];
// p(pi/4) q[0];
rx(pi/4) q[0];
ry(pi/4) q[0];
rz(pi/4) q[0];
// U(pi/4, pi/5, pi/6) q[0];
// cp(pi/4) q[0], q[1];
// crx(pi/4) q[0], q[1];
// cry(pi/4) q[0], q[1];
// crz(pi/4) q[0], q[1];
// cu(pi/4, pi/5, pi/6, pi/7) q[0], q[1];
// gphase(pi/3);
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


@pytest.mark.skipif(not HAS_OPENQASM_GATES, reason="OpenQASM gates are not supported by graphix <= 0.4")
def test_parse_openqasm_gates() -> None:  # noqa: PLR0915
    """Test gates introduced for OpenQASM compatibility."""
    s = """
include "qelib1.inc";
qubit[3] q;
cy q[0], q[1];
cswap q[0], q[1], q[2];
sdg q[0];
t q[0];
tdg q[0];
sx q[0];
sxdg q[0];
p(pi/4) q[0];
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
    assert isinstance(instruction, Instruction.CY)
    assert instruction.target == 1
    assert instruction.control == 0
    instruction = next(iterator)
    assert isinstance(instruction, Instruction.CSWAP)
    assert instruction.control == 0
    assert instruction.targets == (1, 2)
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
    assert isinstance(instruction, Instruction.P)
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
