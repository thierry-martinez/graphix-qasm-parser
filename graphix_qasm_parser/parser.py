"""Graphix OpenQASM parser."""

from __future__ import annotations

import enum
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Generic, TypeVar
from warnings import warn

from antlr4 import (  # type: ignore[attr-defined]
    CommonTokenStream,
    FileStream,
    InputStream,
    ParserRuleContext,
)
from graphix import ANGLE_PI, Axis, Circuit, Instruction, rad_to_angle
from graphix.instruction import InstructionVisitor
from graphix.parameter import Placeholder, with_parameters
from openqasm_parser import qasm3Lexer, qasm3Parser, qasm3ParserVisitor

# override introduced in Python 3.12
from typing_extensions import override

if TYPE_CHECKING:
    from collections.abc import Collection
    from pathlib import Path

    from antlr4.token import Token
    from graphix.fundamentals import ParameterizedAngle
    from graphix.instruction import InstructionType
    from graphix.parameters import Expression, Parameter


_T = TypeVar("_T")


class OpenQASMParser:
    """Graphix OpenQASM parser."""

    def parse_stream(self, stream: InputStream, *, stacklevel: int = 1) -> Circuit:
        """
        Parse the OpenQASM circuit described in the given stream.

        Parameters
        ----------
        stream : InputStream
            The input stream to parse.

        stacklevel : int, optional
            Stack level to use for warnings. Defaults to 1, meaning that warnings
            are reported at this function's call site.

        Returns
        -------
        Circuit
            The parsed circuit.

        """
        lexer = qasm3Lexer(stream)
        tokens = CommonTokenStream(lexer)
        parser = qasm3Parser(tokens)
        tree = parser.program()  # type: ignore[no-untyped-call]
        visitor = _CircuitVisitor(self)
        tree.accept(visitor)
        for msg in visitor.warnings:
            warn(msg, stacklevel=stacklevel + 1)
        return Circuit(visitor.width, instr=visitor.instructions)

    def parse_str(self, s: str, *, stacklevel: int = 1) -> Circuit:
        """
        Parse the OpenQASM circuit described in the given string.

        Parameters
        ----------
        s : str
            The input string to parse.

        stacklevel : int, optional
            Stack level to use for warnings. Defaults to 1, meaning that warnings
            are reported at this function's call site.

        Returns
        -------
        Circuit
            The parsed circuit.

        """
        stream = InputStream(s)
        return self.parse_stream(stream, stacklevel=stacklevel + 1)

    def parse_file(self, path: Path | str, *, stacklevel: int = 1) -> Circuit:
        """
        Parse the OpenQASM circuit described in the given file.

        Parameters
        ----------
        path : Path | str
            The path of the input file to parse.

        stacklevel : int, optional
            Stack level to use for warnings. Defaults to 1, meaning that warnings
            are reported at this function's call site.

        Returns
        -------
        Circuit
            The parsed circuit.

        """
        stream = FileStream(str(path))
        return self.parse_stream(stream, stacklevel=stacklevel + 1)


@dataclass
class _Value:
    ctx: ParserRuleContext | str  # type: ignore[valid-type]

    def __neg__(self) -> _Value:
        return NotImplemented  # type: ignore[no-any-return]

    def __add__(self, other: object) -> _Value:
        return NotImplemented

    def __radd__(self, other: object) -> _Value:
        return NotImplemented

    def __sub__(self, other: object) -> _Value:
        return NotImplemented

    def __rsub__(self, other: object) -> _Value:
        return NotImplemented

    def __mul__(self, other: object) -> _Value:
        return NotImplemented

    def __rmul__(self, other: object) -> _Value:
        return NotImplemented

    def __truediv__(self, other: object) -> _Value:
        return NotImplemented

    def __rtruediv__(self, other: object) -> _Value:
        return NotImplemented

    def __mod__(self, other: object) -> _Value:
        return NotImplemented

    def __rmod__(self, other: object) -> _Value:
        return NotImplemented

    def __int__(self) -> int:
        msg = f"Not an integer value: {self.report_ctx()}"
        raise TypeError(msg)

    def __float__(self) -> float:
        msg = f"Not a floating-point value: {self.report_ctx()}"
        raise TypeError(msg)

    def parameterized_angle(self) -> ParameterizedAngle:
        msg = f"Not an angle: {self.report_ctx()}"
        raise TypeError(msg)

    def as_qubit(self) -> _Qubit:
        if not isinstance(self, _Qubit):
            msg = f"Qubit expected: {self.report_ctx()}"
            raise TypeError(msg)
        return self

    def as_bit(self) -> _Bit:
        if not isinstance(self, _Bit):
            msg = f"Bit expected: {self.report_ctx()}"
            raise TypeError(msg)
        return self

    def as_array(self) -> _Array:
        if not isinstance(self, _Array):
            msg = f"Array expected: {self.report_ctx()}"
            raise TypeError(msg)
        return self

    def report_ctx(self) -> str:
        return self.ctx.getText() if isinstance(self.ctx, ParserRuleContext) else self.ctx  # type: ignore[union-attr,arg-type]


@dataclass
class _Int(_Value):
    value: int

    @override
    def __neg__(self) -> _Value:
        return _Int(self.ctx, -self.value)

    @override
    def __add__(self, other: object) -> _Value:
        if isinstance(other, _Int):
            return _Int(self.ctx, self.value + other.value)
        return NotImplemented

    @override
    def __sub__(self, other: object) -> _Value:
        if isinstance(other, _Int):
            return _Int(self.ctx, self.value - other.value)
        return NotImplemented

    @override
    def __mul__(self, other: object) -> _Value:
        if isinstance(other, _Int):
            return _Int(self.ctx, self.value * other.value)
        return NotImplemented

    @override
    def __truediv__(self, other: object) -> _Value:
        if isinstance(other, _Int):
            result = self.value / other.value
            if isinstance(result, int):
                return _Int(self.ctx, result)
            return _Float(self.ctx, result)
        return NotImplemented

    @override
    def __mod__(self, other: object) -> _Value:
        if isinstance(other, _Int):
            return _Int(self.ctx, self.value % other.value)
        return NotImplemented

    @override
    def __int__(self) -> int:
        return self.value

    @override
    def __float__(self) -> float:
        return float(self.value)

    @override
    def parameterized_angle(self) -> ParameterizedAngle:
        return self.value


@dataclass
class _Float(_Value):
    value: float

    @override
    def __neg__(self) -> _Value:
        return _Float(self.ctx, -self.value)

    @override
    def __add__(self, other: object) -> _Value:
        if isinstance(other, (_Int, _Float)):
            return _Float(self.ctx, self.value + other.value)
        return NotImplemented

    @override
    def __radd__(self, other: object) -> _Value:
        if isinstance(other, _Int):
            return _Float(self.ctx, other.value + self.value)
        return NotImplemented

    @override
    def __sub__(self, other: object) -> _Value:
        if isinstance(other, (_Int, _Float)):
            return _Float(self.ctx, self.value - other.value)
        return NotImplemented

    @override
    def __rsub__(self, other: object) -> _Value:
        if isinstance(other, _Int):
            return _Float(self.ctx, other.value - self.value)
        return NotImplemented

    @override
    def __mul__(self, other: object) -> _Value:
        if isinstance(other, (_Int, _Float)):
            return _Float(self.ctx, self.value * other.value)
        return NotImplemented

    @override
    def __rmul__(self, other: object) -> _Value:
        if isinstance(other, _Int):
            return _Float(self.ctx, other.value * self.value)
        return NotImplemented

    @override
    def __truediv__(self, other: object) -> _Value:
        if isinstance(other, (_Int, _Float)):
            return _Float(self.ctx, self.value / other.value)
        return NotImplemented

    @override
    def __rtruediv__(self, other: object) -> _Value:
        if isinstance(other, _Int):
            return _Float(self.ctx, other.value / self.value)
        return NotImplemented

    @override
    def __mod__(self, other: object) -> _Value:
        if isinstance(other, _Float):
            return _Float(self.ctx, self.value % other.value)
        return NotImplemented

    @override
    def __rmod__(self, other: object) -> _Value:
        if isinstance(other, _Float):
            return _Float(self.ctx, other.value % self.value)
        return NotImplemented

    @override
    def __float__(self) -> float:
        return self.value

    @override
    def parameterized_angle(self) -> ParameterizedAngle:
        return self.value


class _DeclKind(Enum):
    Bit = enum.auto()
    Qubit = enum.auto()


@dataclass
class _Bit(_Value):
    index: int | None = None
    """The index of the measurement.

    In Graphix circuits, measurement outcomes are indexed by the rank
    of the measurement (the index of the outcome of the first
    measurement is 0, the index of the outcome of the second
    measurement is 1, etc.). Each time a measurement outcome is stored
    in a bit register in the QASM file, the index of the outcome is
    stored in this field, so that when the bit register is referenced
    subsequently, we can retrieve the index of the corresponding
    measurement.

    ``None`` means that no measurement outcome has been assigned to
    the bit register yet.
    """

    def as_measured(self) -> int:
        if self.index is None:
            msg = f"Bit should have been assigned to a measurement: {self.report_ctx()}"
            raise ValueError(msg)
        return self.index


@dataclass
class _Qubit(_Value):
    index: int


@dataclass
class _Expression(_Value):
    value: Expression | float

    @override
    def __neg__(self) -> _Value:
        return _Expression(self.ctx, -self.value)

    @override
    def __add__(self, other: object) -> _Value:
        if isinstance(other, (_Int, _Float, _Expression)):
            return _Expression(self.ctx, self.value + other.value)
        return NotImplemented

    @override
    def __radd__(self, other: object) -> _Value:
        if isinstance(other, (_Int, _Float)):
            return _Expression(self.ctx, other.value + self.value)
        return NotImplemented

    @override
    def __sub__(self, other: object) -> _Value:
        if isinstance(other, (_Int, _Float, _Expression)):
            return _Expression(self.ctx, self.value - other.value)
        return NotImplemented

    @override
    def __rsub__(self, other: object) -> _Value:
        if isinstance(other, (_Int, _Float)):
            return _Expression(self.ctx, other.value - self.value)
        return NotImplemented

    @override
    def __mul__(self, other: object) -> _Value:
        if isinstance(other, (_Int, _Float)):
            return _Expression(self.ctx, self.value * other.value)
        return NotImplemented

    @override
    def __rmul__(self, other: object) -> _Value:
        if isinstance(other, (_Int, _Float)):
            return _Expression(self.ctx, other.value * self.value)
        return NotImplemented

    @override
    def __truediv__(self, other: object) -> _Value:
        if isinstance(other, (_Int, _Float)):
            return _Expression(self.ctx, self.value / other.value)
        return NotImplemented

    @override
    def parameterized_angle(self) -> ParameterizedAngle:
        return self.value


@dataclass
class _Array(_Value):
    values: list[_Value]


@dataclass(frozen=True)
class _Gate:
    qubit_count: int
    instructions: tuple[InstructionType, ...]
    params: tuple[Parameter, ...] = ()


_Theta = Placeholder("Theta")

_Phi = Placeholder("Phi")

_Gamma = Placeholder("Gamma")

_Lambda = Placeholder("Lambda")


def _u3(
    target: int, theta: ParameterizedAngle, phi: ParameterizedAngle, lambda_: ParameterizedAngle
) -> tuple[InstructionType, ...]:
    return (
        Instruction.U(target=target, theta=theta, phi=phi, lambda_=lambda_),
        # Overcome limitation of placeholders that cannot be summed.
        Instruction.GPHASE(-theta / 2),
        Instruction.GPHASE(-phi / 2),
        Instruction.GPHASE(-lambda_ / 2),
    )


_BuiltinGates: dict[str, _Gate] = {
    "ccx":  # https://openqasm.com/language/standard_library.html#ccx
    _Gate(
        qubit_count=3,
        instructions=(Instruction.CCX(controls=(0, 1), target=2),),
    ),
    "cx":  # https://openqasm.com/language/standard_library.html#cx
    _Gate(
        qubit_count=2,
        instructions=(Instruction.CNOT(control=0, target=1),),
    ),
    "cy":  # https://openqasm.com/language/standard_library.html#cy
    _Gate(
        qubit_count=2,
        instructions=(Instruction.CY(control=0, target=1),),
    ),
    "cz":  # https://openqasm.com/language/standard_library.html#cz
    _Gate(
        qubit_count=2,
        instructions=(Instruction.CZ(targets=(0, 1)),),
    ),
    "swap":  # https://openqasm.com/language/standard_library.html#swap
    _Gate(
        qubit_count=2,
        instructions=(Instruction.SWAP(targets=(0, 1)),),
    ),
    "cswap":  # https://openqasm.com/language/standard_library.html#cswap
    _Gate(
        qubit_count=3,
        instructions=(Instruction.CSWAP(control=0, targets=(1, 2)),),
    ),
    "h":  # https://openqasm.com/language/standard_library.html#h
    _Gate(
        qubit_count=1,
        instructions=(Instruction.H(target=0),),
    ),
    "s":  # https://openqasm.com/language/standard_library.html#s
    _Gate(
        qubit_count=1,
        instructions=(Instruction.S(target=0),),
    ),
    "sdg":  # https://openqasm.com/language/standard_library.html#sdg
    _Gate(
        qubit_count=1,
        instructions=(Instruction.SDG(target=0),),
    ),
    "t":  # https://openqasm.com/language/standard_library.html#t
    _Gate(
        qubit_count=1,
        instructions=(Instruction.T(target=0),),
    ),
    "tdg":  # https://openqasm.com/language/standard_library.html#tdg
    _Gate(
        qubit_count=1,
        instructions=(Instruction.TDG(target=0),),
    ),
    "sx":  # https://openqasm.com/language/standard_library.html#sx
    _Gate(
        qubit_count=1,
        instructions=(Instruction.SX(target=0),),
    ),
    "sxdg":  # https://openqasm.com/language/standard_library.html#sxdg
    _Gate(
        qubit_count=1,
        instructions=(Instruction.SXDG(target=0),),
    ),
    "x":  # https://openqasm.com/language/standard_library.html#x
    _Gate(
        qubit_count=1,
        instructions=(Instruction.X(target=0),),
    ),
    "y":  # https://openqasm.com/language/standard_library.html#y
    _Gate(
        qubit_count=1,
        instructions=(Instruction.Y(target=0),),
    ),
    "z":  # https://openqasm.com/language/standard_library.html#z
    _Gate(
        qubit_count=1,
        instructions=(Instruction.Z(target=0),),
    ),
    "id":  # https://openqasm.com/language/standard_library.html#id
    _Gate(
        qubit_count=1,
        instructions=(Instruction.I(target=0),),
    ),
    "p":  # https://openqasm.com/language/standard_library.html#p
    _Gate(
        params=(_Theta,),
        qubit_count=1,
        instructions=(Instruction.P(target=0, angle=rad_to_angle(_Theta)),),
    ),
    "u1":  # https://openqasm.com/language/standard_library.html#u1
    _Gate(
        params=(_Theta,),
        qubit_count=1,
        instructions=(Instruction.P(target=0, angle=rad_to_angle(_Theta)),),
    ),
    "rx":  # https://openqasm.com/language/standard_library.html#rx
    _Gate(
        params=(_Theta,),
        qubit_count=1,
        instructions=(Instruction.RX(target=0, angle=rad_to_angle(_Theta)),),
    ),
    "ry":  # https://openqasm.com/language/standard_library.html#ry
    _Gate(
        params=(_Theta,),
        qubit_count=1,
        instructions=(Instruction.RY(target=0, angle=rad_to_angle(_Theta)),),
    ),
    "rz":  # https://openqasm.com/language/standard_library.html#rz
    _Gate(
        params=(_Theta,),
        qubit_count=1,
        instructions=(Instruction.RZ(target=0, angle=rad_to_angle(_Theta)),),
    ),
    "U":  # https://openqasm.com/language/gates.html#U
    _Gate(
        params=(_Theta, _Phi, _Lambda),
        qubit_count=1,
        instructions=(
            Instruction.U(target=0, theta=rad_to_angle(_Theta), phi=rad_to_angle(_Phi), lambda_=rad_to_angle(_Lambda)),
        ),
    ),
    "cp":  # https://openqasm.com/language/standard_library.html#cp
    _Gate(
        params=(_Theta,),
        qubit_count=2,
        instructions=(Instruction.CP(control=0, target=1, angle=rad_to_angle(_Theta)),),
    ),
    "crx":  # https://openqasm.com/language/standard_library.html#crx
    _Gate(
        params=(_Theta,),
        qubit_count=2,
        instructions=(Instruction.CRX(control=0, target=1, angle=rad_to_angle(_Theta)),),
    ),
    "cry":  # https://openqasm.com/language/standard_library.html#cry
    _Gate(
        params=(_Theta,),
        qubit_count=2,
        instructions=(Instruction.CRY(control=0, target=1, angle=rad_to_angle(_Theta)),),
    ),
    "crz":  # https://openqasm.com/language/standard_library.html#crz
    _Gate(
        params=(_Theta,),
        qubit_count=2,
        instructions=(Instruction.CRZ(control=0, target=1, angle=rad_to_angle(_Theta)),),
    ),
    "cu":  # https://openqasm.com/language/standard_library.html#cu
    _Gate(
        params=(_Theta, _Phi, _Lambda, _Gamma),
        qubit_count=2,
        instructions=(
            Instruction.CU(
                control=0,
                target=1,
                theta=rad_to_angle(_Theta),
                phi=rad_to_angle(_Phi),
                lambda_=rad_to_angle(_Lambda),
                gamma=rad_to_angle(_Gamma),
            ),
        ),
    ),
    "u2":  # https://openqasm.com/language/standard_library.html#u2
    _Gate(
        params=(_Phi, _Lambda),
        qubit_count=1,
        instructions=_u3(target=0, theta=ANGLE_PI / 2, phi=rad_to_angle(_Phi), lambda_=rad_to_angle(_Lambda)),
    ),
    "u3":  # https://openqasm.com/language/standard_library.html#u3
    _Gate(
        params=(_Theta, _Phi, _Lambda),
        qubit_count=1,
        instructions=_u3(target=0, theta=rad_to_angle(_Theta), phi=rad_to_angle(_Phi), lambda_=rad_to_angle(_Lambda)),
    ),
}


@dataclass
class _SubstGate(InstructionVisitor):
    subst_params: dict[Parameter, ParameterizedAngle]
    subst_qubits: dict[int, int]

    @override
    def visit_angle(self, angle: ParameterizedAngle) -> ParameterizedAngle:
        if isinstance(angle, float):
            return angle
        return with_parameters(angle, self.subst_params)

    @override
    def visit_qubit(self, qubit: int) -> int:
        return self.subst_qubits[qubit]


class _CircuitVisitor(qasm3ParserVisitor):
    parser: OpenQASMParser
    width: int
    measurement_count: int
    instructions: list[InstructionType]
    env: dict[str, _Value]
    warnings: list[str]
    user_defined_gates: dict[str, _Gate]
    inside_gate_definition: bool

    def __init__(self, parser: OpenQASMParser) -> None:
        self.parser = parser
        self.width = 0
        self.measurement_count = 0
        self.instructions = []
        self.env = {
            "pi": _Float("pi", math.pi),
            "π": _Float("π", math.pi),
        }
        self.warnings = []
        self.user_defined_gates = {}
        self.inside_gate_definition = False

    def check_not_inside_gate_definition(self, ctx: ParserRuleContext) -> None:  # type: ignore[valid-type]
        if self.inside_gate_definition:
            msg = f"Only built-in gate statements and calls to previously defined gates can appear in body of gate definition: {ctx}"
            raise ValueError(msg)

    @override
    def visitOldStyleDeclarationStatement(self, ctx: qasm3Parser.OldStyleDeclarationStatementContext) -> None:
        self.check_not_inside_gate_definition(ctx)
        kind = ctx.getChild(0)
        if kind.symbol.type == qasm3Parser.QREG:
            decl_kind = _DeclKind.Qubit
        elif kind.symbol.type == qasm3Parser.CREG:
            decl_kind = _DeclKind.Bit
        else:
            msg = f"Unknown declaration statement kind: {kind}"
            raise NotImplementedError(msg)
        identifier = ctx.Identifier().getText()  # type: ignore[no-untyped-call]
        designator = ctx.designator()  # type: ignore[no-untyped-call]
        self.declare_registers(ctx, decl_kind, identifier, designator)

    @override
    def visitQuantumDeclarationStatement(self, ctx: qasm3Parser.QuantumDeclarationStatementContext) -> None:
        self.check_not_inside_gate_definition(ctx)
        designator = ctx.qubitType().designator()  # type: ignore[no-untyped-call]
        identifier = ctx.Identifier().getText()  # type: ignore[no-untyped-call]
        self.declare_registers(ctx, _DeclKind.Qubit, identifier, designator)

    @override
    def visitClassicalDeclarationStatement(self, ctx: qasm3Parser.ClassicalDeclarationStatementContext) -> None:
        scalar_type = ctx.scalarType()  # type: ignore[no-untyped-call]
        if scalar_type is None or scalar_type.BIT() is None:
            msg = "Only bit type is supported."
            raise NotImplementedError(msg)
        identifier = ctx.Identifier().getText()  # type: ignore[no-untyped-call]
        designator = scalar_type.designator()
        self.declare_registers(ctx, _DeclKind.Bit, identifier, designator)

    @override
    def visitConstDeclarationStatement(self, ctx: qasm3Parser.ConstDeclarationStatementContext) -> None:
        self.check_not_inside_gate_definition(ctx)
        identifier = ctx.Identifier().getText()  # type: ignore[no-untyped-call]
        value = ctx.declarationExpression()  # type: ignore[no-untyped-call]
        expr = self.evaluate_expression(value)
        self.env[identifier] = expr

    @override
    def visitGateCallStatement(self, ctx: qasm3Parser.GateCallStatementContext) -> None:
        if expr_list := ctx.expressionList():  # type: ignore[no-untyped-call]
            exprs = [
                self.evaluate_expression(expr_list.getChild(i)).parameterized_angle()
                for i in range(0, expr_list.getChildCount(), 2)
            ]
        else:
            exprs = []
        if ctx.GPHASE():  # type: ignore[no-untyped-call]
            # https://openqasm.com/language/gates.html#gphase

            # `gphase` is parsed as a keyword rather than as an
            # identifier name (`ctx.Identifier()` returns `None` in
            # this case), so it should be handled specially.
            instruction: InstructionType = Instruction.GPHASE(angle=rad_to_angle(exprs[0]))
            self.instructions.append(instruction)
            return
        gate_name = ctx.Identifier().getText()  # type: ignore[no-untyped-call]
        operand_list = ctx.gateOperandList()  # type: ignore[no-untyped-call]
        operands = [
            self.convert_qubit_index(operand_list.getChild(i)) for i in range(0, operand_list.getChildCount(), 2)
        ]
        gate = _BuiltinGates.get(gate_name)
        if gate is None:
            gate = self.user_defined_gates.get(gate_name)
            if gate is None:
                msg = f"Unknown gate {gate_name}: {ctx}"
                raise ValueError(msg)
        if len(exprs) != len(gate.params):
            param_names = ", ".join(map(str, gate.params))
            msg = f"Gate {gate_name} expect {len(gate.params)} parameters ({param_names}) but {len(exprs)} given: {ctx}"
            raise ValueError(msg)
        if len(operands) != gate.qubit_count:
            msg = f"Gate {gate_name} expect {gate.qubit_count} qubits but {len(operands)} given: {ctx}"
            raise ValueError(msg)
        subst_params = dict(zip(gate.params, exprs, strict=True))
        subst_qubits = dict(enumerate(operands))
        subst_gate = _SubstGate(subst_params, subst_qubits)
        for instruction in gate.instructions:
            local_instruction = instruction.visit(subst_gate, copy=True)
            self.instructions.append(local_instruction)

    @override
    def visitGateStatement(self, ctx: qasm3Parser.GateStatementContext) -> None:
        self.check_not_inside_gate_definition(ctx)
        name = ctx.Identifier().getText()  # type: ignore[no-untyped-call]
        param_identifiers: Collection[Token] = ctx.params.Identifier() if ctx.params else ()
        qubit_identifiers: Collection[Token] = ctx.qubits.Identifier() if ctx.qubits else ()
        scope = ctx.scope()  # type: ignore[no-untyped-call]
        parent_instructions = self.instructions
        parent_env = self.env
        self.instructions = []
        params = tuple(Placeholder(param.getText()) for param in param_identifiers)
        self.env = {}
        for param_ctx, param in zip(param_identifiers, params, strict=True):
            self.env[param.name] = _Expression(param_ctx, param)
        for qubit_index, qubit_identifier in enumerate(qubit_identifiers):
            self.env[qubit_identifier.getText()] = _Qubit(qubit_identifier, qubit_index)
        self.inside_gate_definition = True
        scope.accept(self)
        self.inside_gate_definition = False
        self.user_defined_gates[name] = _Gate(
            params=params, qubit_count=len(qubit_identifiers), instructions=tuple(self.instructions)
        )
        self.instructions = parent_instructions
        self.env = parent_env

    @override
    def visitAssignmentStatement(self, ctx: qasm3Parser.AssignmentStatementContext) -> None:
        measure_expression = ctx.measureExpression()  # type: ignore[no-untyped-call]
        if measure_expression is None:
            msg = "Only measure assignments are supported."
            raise NotImplementedError(msg)
        indexed_identifier = ctx.indexedIdentifier()  # type: ignore[no-untyped-call]
        self.add_measurement_statement(indexed_identifier, measure_expression)

    @override
    def visitMeasureArrowAssignmentStatement(self, ctx: qasm3Parser.MeasureArrowAssignmentStatementContext) -> None:
        indexed_identifier = ctx.indexedIdentifier()  # type: ignore[no-untyped-call]
        measure_expression = ctx.measureExpression()  # type: ignore[no-untyped-call]
        self.add_measurement_statement(indexed_identifier, measure_expression)

    @override
    def visitIfStatement(self, ctx: qasm3Parser.IfStatementContext) -> None:
        expression = ctx.expression()  # type: ignore[no-untyped-call]
        if ctx.ELSE():  # type: ignore[no-untyped-call]
            msg = "If-else statements are not yet supported."
            raise NotImplementedError(msg)
        statement_or_scope = ctx.statementOrScope(0)
        domain = self.evaluate_domain(expression)
        parent_instructions = self.instructions
        self.instructions = []
        statement_or_scope.accept(self)
        body = self.instructions
        self.instructions = parent_instructions
        if domain:
            instruction = Instruction.CONDINSTR(tuple(body), domain)
            self.instructions.append(instruction)
        else:
            self.warnings.append("Conditional instruction with empty condition dropped.")
            self.instructions.extend(body)

    def add_measurement_statement(
        self,
        indexed_identifier: qasm3Parser.IndexedIdentifierContext,
        measure_expression: qasm3Parser.MeasureExpressionContext,
    ) -> None:
        target_bit = self.evaluate_indexed_identifier(indexed_identifier)
        gate_operand = measure_expression.gateOperand()  # type: ignore[no-untyped-call]
        target_qubit = self.evaluate_operand(gate_operand)
        if isinstance(target_bit, _Array) or isinstance(target_qubit, _Array):
            if not isinstance(target_bit, _Array) or not isinstance(target_qubit, _Array):
                msg = "Both arguments must be registers, or both must be bit/qubit types."
                raise TypeError(msg)
            if len(target_bit.values) != len(target_qubit.values):
                msg = "Both registers must have the same size."
                raise ValueError(msg)
            for bit, qubit in zip(target_bit.values, target_qubit.values, strict=True):
                self.add_measurement(bit, qubit)
            return
        self.add_measurement(target_bit, target_qubit)

    def add_measurement(self, target_bit: _Value, target_qubit: _Value) -> None:
        if not isinstance(target_bit, _Bit):
            msg = f"Only assignment to bit is supported: {target_bit} unexpected."
            raise NotImplementedError(msg)
        qubit_index = target_qubit.as_qubit().index
        instruction = Instruction.M(qubit_index, Axis.Z)
        self.instructions.append(instruction)
        target_bit.index = qubit_index
        self.measurement_count += 1

    def declare_register(self, ctx: ParserRuleContext, decl_kind: _DeclKind) -> _Value:  # type: ignore[valid-type]
        match decl_kind:
            case _DeclKind.Bit:
                value: _Value = _Bit(ctx)
            case _DeclKind.Qubit:
                value = _Qubit(ctx, self.width)
                self.width += 1
        return value

    def declare_registers(
        self,
        ctx: ParserRuleContext,  # type: ignore[valid-type]
        decl_kind: _DeclKind,
        identifier: str,
        designator: qasm3Parser.DesignatorContext | None,
    ) -> None:
        value: _Value
        if designator:
            expression = designator.expression()  # type: ignore[no-untyped-call]
            count = int(self.evaluate_expression(expression))
            value = _Array(ctx, [self.declare_register(ctx, decl_kind) for i in range(count)])
        else:
            value = self.declare_register(ctx, decl_kind)
        self.env[identifier] = value

    def convert_qubit_index(self, operand: qasm3Parser.GateOperandContext) -> int:
        value = self.evaluate_operand(operand)
        return value.as_qubit().index

    def evaluate_operand(self, operand: qasm3Parser.GateOperandContext) -> _Value:
        child = operand.getChild(0)
        if child.getRuleIndex() == qasm3Parser.RULE_indexedIdentifier:
            return self.evaluate_indexed_identifier(child)
        msg = f"Unknown operand: {operand}"
        raise NotImplementedError(msg)

    def evaluate_indexed_identifier(self, indexed_identifier: qasm3Parser.IndexedIdentifierContext) -> _Value:
        identifier = indexed_identifier.Identifier().getText()  # type: ignore[no-untyped-call]
        value = self.env.get(identifier)
        if value is None:
            msg = f"name {identifier} is not defined"
            raise NameError(msg)
        for operator in indexed_identifier.indexOperator():
            array = value.as_array()
            index = int(self.evaluate_expression(operator.expression(0)))
            identifier = _check_index(index, identifier, len(array.values))
            value = array.values[index]
        return value

    def evaluate_expression(self, expr: qasm3Parser.ExpressionContext) -> _Value:
        return _ValueVisitor(self).parse(expr)

    def evaluate_domain(self, expr: qasm3Parser.ExpressionContext) -> set[int]:
        return _DomainVisitor(self).parse(expr)


def _check_index(index: int, identifier: str, length: int) -> str:
    if index < 0:
        msg = f"Negative index: {identifier}"
        raise IndexError(msg)
    if index >= length:
        msg = f"Index out of bounds: {identifier} has length {length}"
        raise IndexError(msg)
    return f"{identifier}[index]"


class _ExpressionVisitor(ABC, qasm3ParserVisitor, Generic[_T]):
    def __init__(self, circuit: _CircuitVisitor) -> None:
        self.circuit = circuit

    def parse(self, expr: qasm3Parser.ExpressionContext) -> _T:
        value: _T | None = expr.accept(self)
        if value is None:
            msg = f"Cannot parse value: {expr.getText()}"
            raise NotImplementedError(msg)
        return value

    @override
    def visitParenthesisExpression(self, ctx: qasm3Parser.ParenthesisExpressionContext) -> _T:
        expr: qasm3Parser.ExpressionContext = ctx.expression()  # type: ignore[no-untyped-call]
        return self.parse(expr)

    @override
    def visitAdditiveExpression(self, ctx: qasm3Parser.AdditiveExpressionContext) -> _T:
        return self.parse_binary_operator(ctx)

    @override
    def visitMultiplicativeExpression(self, ctx: qasm3Parser.MultiplicativeExpressionContext) -> _T:
        return self.parse_binary_operator(ctx)

    @override
    def visitBitshiftExpressionExpression(self, ctx: qasm3Parser.BitshiftExpressionContext) -> _T:
        return self.parse_binary_operator(ctx)

    @override
    def visitComparisonExpression(self, ctx: qasm3Parser.ComparisonExpressionContext) -> _T:
        return self.parse_binary_operator(ctx)

    @override
    def visitEqualityExpression(self, ctx: qasm3Parser.EqualityExpressionContext) -> _T:
        return self.parse_binary_operator(ctx)

    @override
    def visitBitwiseAndExpression(self, ctx: qasm3Parser.BitwiseAndExpressionContext) -> _T:
        return self.parse_binary_operator(ctx)

    @override
    def visitBitwiseXorExpression(self, ctx: qasm3Parser.BitwiseXorExpressionContext) -> _T:
        return self.parse_binary_operator(ctx)

    @override
    def visitBitwiseOrExpression(self, ctx: qasm3Parser.BitwiseOrExpressionContext) -> _T:
        return self.parse_binary_operator(ctx)

    @override
    def visitLogicalAndExpression(self, ctx: qasm3Parser.LogicalAndExpressionContext) -> _T:
        return self.parse_binary_operator(ctx)

    @override
    def visitLogicalOrExpression(self, ctx: qasm3Parser.LogicalOrExpressionContext) -> _T:
        return self.parse_binary_operator(ctx)

    @abstractmethod
    def parse_binary_operator(
        self,
        ctx: qasm3Parser.AdditiveExpressionContext
        | qasm3Parser.MultiplicativeExpressionContext
        | qasm3Parser.BitshiftExpressionContext
        | qasm3Parser.ComparisonExpressionContext
        | qasm3Parser.EqualityExpressionContext
        | qasm3Parser.BitwiseAndExpressionContext
        | qasm3Parser.BitwiseXorExpressionContext
        | qasm3Parser.BitwiseOrExpressionContext,
    ) -> _T: ...


class _ValueVisitor(_ExpressionVisitor[_Value]):
    # Needed for mypy to instantiate `_T`
    def __init__(self, circuit: _CircuitVisitor) -> None:
        super().__init__(circuit)

    @override
    def visitUnaryExpression(self, ctx: qasm3Parser.UnaryExpressionContext) -> _Value:
        operand_expr: qasm3Parser.ExpressionContext = ctx.expression()  # type: ignore[no-untyped-call]
        operand = self.parse(operand_expr)
        operator = ctx.getChild(0).symbol.type
        if operator == qasm3Parser.MINUS:
            result = -operand
            result.ctx = ctx
            return result
        msg = f"Unknown operator: {ctx.getChild(0).symbol.text}"
        raise NotImplementedError(msg)

    @override
    def visitAdditiveExpression(self, ctx: qasm3Parser.AdditiveExpressionContext) -> _Value:
        return self.parse_binary_operator(ctx)

    @override
    def visitMultiplicativeExpression(self, ctx: qasm3Parser.MultiplicativeExpressionContext) -> _Value:
        return self.parse_binary_operator(ctx)

    @override
    def visitIndexExpression(self, ctx: qasm3Parser.IndexExpressionContext) -> _Value:
        expression = ctx.expression()  # type: ignore[no-untyped-call]
        identifier = expression.getText()
        value = self.parse(expression)
        index_operator = ctx.indexOperator()  # type: ignore[no-untyped-call]
        for index_expr in index_operator.expression():
            array = value.as_array()
            index = int(self.parse(index_expr))
            identifier = _check_index(index, identifier, len(array.values))
            value = array.values[index]
        return value

    @override
    def visitLiteralExpression(self, ctx: qasm3Parser.LiteralExpressionContext) -> _Value:
        literal = ctx.getChild(0)
        if literal.symbol.type == qasm3Parser.DecimalIntegerLiteral:
            return _Int(ctx, int(literal.symbol.text))
        if literal.symbol.type == qasm3Parser.FloatLiteral:
            return _Float(ctx, float(literal.symbol.text))
        if literal.symbol.type == qasm3Parser.Identifier:
            identifier = literal.symbol.text
            if value := self.circuit.env.get(identifier):
                return value
        msg = f"Unknown literal: {literal.symbol.text}"
        raise NotImplementedError(msg)

    @override
    def parse_binary_operator(
        self,
        ctx: qasm3Parser.AdditiveExpressionContext
        | qasm3Parser.MultiplicativeExpressionContext
        | qasm3Parser.BitshiftExpressionContext
        | qasm3Parser.ComparisonExpressionContext
        | qasm3Parser.EqualityExpressionContext
        | qasm3Parser.BitwiseAndExpressionContext
        | qasm3Parser.BitwiseXorExpressionContext
        | qasm3Parser.BitwiseOrExpressionContext,
    ) -> _Value:
        lhs_expr: qasm3Parser.ExpressionContext = ctx.getChild(0)
        rhs_expr: qasm3Parser.ExpressionContext = ctx.getChild(2)
        lhs = self.parse(lhs_expr)
        rhs = self.parse(rhs_expr)
        operator = ctx.getChild(1).symbol.type
        if operator == qasm3Parser.ASTERISK:
            result = lhs * rhs
        elif operator == qasm3Parser.SLASH:
            result = lhs / rhs
        elif operator == qasm3Parser.PERCENT:
            result = lhs % rhs
        elif operator == qasm3Parser.PLUS:
            result = lhs + rhs
        elif operator == qasm3Parser.MINUS:
            result = lhs - rhs
        else:
            msg = f"Unknown operator: {ctx.getChild(1).symbol.text}"
            raise NotImplementedError(msg)
        result.ctx = ctx
        return result


class _DomainVisitor(_ExpressionVisitor[set[int]]):
    # Needed for mypy to instantiate `_T`
    def __init__(self, circuit: _CircuitVisitor) -> None:
        super().__init__(circuit)

    @override
    def visitUnaryExpression(self, ctx: qasm3Parser.UnaryExpressionContext) -> set[int]:
        msg = f"Unknown operator: {ctx.getChild(0).symbol.text}"
        raise NotImplementedError(msg)

    @override
    def visitLiteralExpression(self, ctx: qasm3Parser.LiteralExpressionContext) -> set[int]:
        value = _ValueVisitor(self.circuit).visitLiteralExpression(ctx)
        return {value.as_bit().as_measured()}

    @override
    def visitIndexExpression(self, ctx: qasm3Parser.IndexExpressionContext) -> set[int]:
        value = _ValueVisitor(self.circuit).visitIndexExpression(ctx)
        return {value.as_bit().as_measured()}

    @override
    def parse_binary_operator(
        self,
        ctx: qasm3Parser.AdditiveExpressionContext
        | qasm3Parser.MultiplicativeExpressionContext
        | qasm3Parser.BitshiftExpressionContext
        | qasm3Parser.ComparisonExpressionContext
        | qasm3Parser.EqualityExpressionContext
        | qasm3Parser.BitwiseAndExpressionContext
        | qasm3Parser.BitwiseXorExpressionContext
        | qasm3Parser.BitwiseOrExpressionContext,
    ) -> set[int]:
        lhs_expr: qasm3Parser.ExpressionContext = ctx.getChild(0)
        rhs_expr: qasm3Parser.ExpressionContext = ctx.getChild(2)
        lhs = self.parse(lhs_expr)
        rhs = self.parse(rhs_expr)
        operator = ctx.getChild(1).symbol.type
        if operator == qasm3Parser.CARET:
            if lhs & rhs:
                self.circuit.warnings.append("Redundant bits are removed from domains.")
            result = lhs ^ rhs
        else:
            msg = f"Unknown operator: {ctx.getChild(1).symbol.text}"
            raise NotImplementedError(msg)
        return result
