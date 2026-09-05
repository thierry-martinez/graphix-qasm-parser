"""Graphix OpenQASM parser."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from antlr4 import (  # type: ignore[attr-defined]
    CommonTokenStream,
    FileStream,
    InputStream,
    ParserRuleContext,
)
from graphix import Circuit
from graphix.instruction import CCX, CNOT, RX, RY, RZ, SWAP, H, I, InstructionVisitor, S, X, Y, Z
from graphix.parameter import Placeholder, with_parameters
from openqasm_parser import qasm3Lexer, qasm3Parser, qasm3ParserVisitor

# override introduced in Python 3.12
from typing_extensions import override

if TYPE_CHECKING:
    from pathlib import Path

    from graphix.fundamentals import ParameterizedAngle
    from graphix.instruction import InstructionType
    from graphix.parameter import Expression, Parameter

    # Compatibility with graphix <= 0.3.3
    # See https://github.com/TeamGraphix/graphix/pull/379

    ANGLE_PI: float

    def rad_to_angle(angle: ParameterizedAngle) -> ParameterizedAngle:
        """Prototype for rad_to_angle."""
        ...

    CZ = SWAP
else:
    try:
        from graphix.instruction import CZ
    except ImportError:

        def CZ(_q0: int, _q1: int) -> None:  # noqa: N802
            """In older versions of graphix (<= 0.3.3), CZ instructions were not supported."""
            msg = "CZ instructions are not supported by graphix <= 0.3.3"
            raise NotImplementedError(msg)

    try:
        from graphix.fundamentals import ANGLE_PI, rad_to_angle
    except ImportError:
        # Compatibility with graphix <= 0.3.3
        # See https://github.com/TeamGraphix/graphix/pull/399
        ANGLE_PI = math.pi

        def rad_to_angle(angle: ParameterizedAngle) -> ParameterizedAngle:
            """In older versions of graphix (<= 0.3.3), instruction angles were expressed in radians."""
            return angle


class OpenQASMParser:
    """Graphix OpenQASM parser."""

    def parse_stream(self, stream: InputStream) -> Circuit:
        """Parse the OpenQASM circuit described in the given stream."""
        lexer = qasm3Lexer(stream)
        tokens = CommonTokenStream(lexer)
        parser = qasm3Parser(tokens)
        tree = parser.program()  # type: ignore[no-untyped-call]
        visitor = _CircuitVisitor(self)
        tree.accept(visitor)
        return Circuit(visitor.width, instr=visitor.instructions)

    def parse_str(self, s: str) -> Circuit:
        """Parse the OpenQASM circuit described in the given string."""
        stream = InputStream(s)
        return self.parse_stream(stream)

    def parse_file(self, path: Path | str) -> Circuit:
        """Parse the OpenQASM circuit described in the given file."""
        stream = FileStream(str(path))
        return self.parse_stream(stream)


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
        msg = "Not an integer value: {ctx.getText() if isinstance(ctx, ParserRuleContext) else ctx}"
        raise TypeError(msg)

    def __float__(self) -> float:
        msg = "Not a floating-point value: {ctx.getText() if isinstance(ctx, ParserRuleContext) else ctx}"
        raise TypeError(msg)

    def parameterized_angle(self) -> ParameterizedAngle:
        msg = f"Not an angle: {self.report_ctx()}"
        raise TypeError(msg)

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


@dataclass
class _Bit(_Value):
    index: int


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


_BuiltinGates: dict[str, _Gate] = {
    "ccx":  # https://openqasm.com/language/standard_library.html#ccx
    _Gate(
        qubit_count=3,
        instructions=(CCX(controls=(0, 1), target=2),),
    ),
    "cx":  # https://openqasm.com/language/standard_library.html#cx
    _Gate(
        qubit_count=2,
        instructions=(CNOT(control=0, target=1),),
    ),
    "swap":  # https://openqasm.com/language/standard_library.html#swap
    _Gate(
        qubit_count=2,
        instructions=(SWAP(targets=(0, 1)),),
    ),
    "cz":  # https://openqasm.com/language/standard_library.html#cz
    _Gate(
        qubit_count=2,
        instructions=(CZ(targets=(0, 1)),),
    ),
    "h":  # https://openqasm.com/language/standard_library.html#h
    _Gate(
        qubit_count=1,
        instructions=(H(target=0),),
    ),
    "s":  # https://openqasm.com/language/standard_library.html#s
    _Gate(
        qubit_count=1,
        instructions=(S(target=0),),
    ),
    "x":  # https://openqasm.com/language/standard_library.html#x
    _Gate(
        qubit_count=1,
        instructions=(X(target=0),),
    ),
    "y":  # https://openqasm.com/language/standard_library.html#y
    _Gate(
        qubit_count=1,
        instructions=(Y(target=0),),
    ),
    "z":  # https://openqasm.com/language/standard_library.html#z
    _Gate(
        qubit_count=1,
        instructions=(Z(target=0),),
    ),
    "id":  # https://openqasm.com/language/standard_library.html#id
    _Gate(
        qubit_count=1,
        instructions=(I(target=0),),
    ),
    "rx":  # https://openqasm.com/language/standard_library.html#rx
    _Gate(
        params=(_Theta,),
        qubit_count=1,
        instructions=(RX(target=0, angle=rad_to_angle(_Theta)),),
    ),
    "ry":  # https://openqasm.com/language/standard_library.html#ry
    _Gate(
        params=(_Theta,),
        qubit_count=1,
        instructions=(RY(target=0, angle=rad_to_angle(_Theta)),),
    ),
    "rz":  # https://openqasm.com/language/standard_library.html#rz
    _Gate(
        params=(_Theta,),
        qubit_count=1,
        instructions=(RZ(target=0, angle=rad_to_angle(_Theta)),),
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
    instructions: list[InstructionType]
    env: dict[str, _Value]
    user_defined_gates: dict[str, _Gate]
    inside_gate_definition: bool

    def __init__(self, parser: OpenQASMParser) -> None:
        self.parser = parser
        self.width = 0
        self.instructions = []
        self.env = {
            "pi": _Float("pi", math.pi),
            "π": _Float("π", math.pi),
        }
        self.user_defined_gates = {}
        self.inside_gate_definition = False

    def check_not_inside_gate_definition(self, ctx: ParserRuleContext) -> None:  # type: ignore[valid-type]
        if self.inside_gate_definition:
            msg = f"Only built-in gate statements and calls to previously defined gates can appear in body of gate definition: {ctx}"
            raise ValueError(msg)

    @override
    def visitOldStyleDeclarationStatement(self, ctx: qasm3Parser.OldStyleDeclarationStatementContext) -> None:
        decl_class: type[_Bit | _Qubit]
        self.check_not_inside_gate_definition(ctx)
        kind = ctx.getChild(0)
        if kind.symbol.type == qasm3Parser.QREG:
            decl_class = _Qubit
        elif kind.symbol.type == qasm3Parser.CREG:
            decl_class = _Bit
        else:
            msg = f"Unknown declaration statement kind: {kind}"
            raise NotImplementedError(msg)
        identifier = ctx.Identifier().getText()  # type: ignore[no-untyped-call]
        designator = ctx.designator()  # type: ignore[no-untyped-call]
        self.declare_registers(ctx, decl_class, identifier, designator)

    @override
    def visitQuantumDeclarationStatement(self, ctx: qasm3Parser.QuantumDeclarationStatementContext) -> None:
        self.check_not_inside_gate_definition(ctx)
        designator = ctx.qubitType().designator()  # type: ignore[no-untyped-call]
        identifier = ctx.Identifier().getText()  # type: ignore[no-untyped-call]
        self.declare_registers(ctx, _Qubit, identifier, designator)

    @override
    def visitConstDeclarationStatement(self, ctx: qasm3Parser.ConstDeclarationStatementContext) -> None:
        self.check_not_inside_gate_definition(ctx)
        identifier = ctx.Identifier().getText()  # type: ignore[no-untyped-call]
        value = ctx.declarationExpression()  # type: ignore[no-untyped-call]
        expr = self.evaluate_expression(value)
        self.env[identifier] = expr

    @override
    def visitGateCallStatement(self, ctx: qasm3Parser.GateCallStatementContext) -> None:
        gate_name = ctx.Identifier().getText()  # type: ignore[no-untyped-call]
        operand_list = ctx.gateOperandList()  # type: ignore[no-untyped-call]
        operands = [
            self.convert_qubit_index(operand_list.getChild(i)) for i in range(0, operand_list.getChildCount(), 2)
        ]
        if expr_list := ctx.expressionList():  # type: ignore[no-untyped-call]
            exprs = [
                self.evaluate_expression(expr_list.getChild(i)).parameterized_angle()
                for i in range(0, expr_list.getChildCount(), 2)
            ]
        else:
            exprs = []
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
        param_identifiers = ctx.identifierList(0).Identifier()
        qubit_identifiers = ctx.identifierList(1).Identifier()
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
        scope.accept(self)
        self.user_defined_gates[name] = _Gate(
            params=params, qubit_count=len(qubit_identifiers), instructions=tuple(self.instructions)
        )
        self.instructions = parent_instructions
        self.env = parent_env

    def declare_registers(
        self,
        ctx: ParserRuleContext,  # type: ignore[valid-type]
        decl_class: type[_Bit | _Qubit],
        identifier: str,
        designator: qasm3Parser.DesignatorContext | None,
    ) -> None:
        value: _Value
        if designator:
            expression = designator.expression()  # type: ignore[no-untyped-call]
            count = int(self.evaluate_expression(expression))
            value = _Array(ctx, [decl_class(ctx, self.width + i) for i in range(count)])
            self.width += count
        else:
            value = decl_class(ctx, self.width)
            self.width += 1
        self.env[identifier] = value

    def convert_qubit_index(self, operand: qasm3Parser.GateOperandContext) -> int:
        value = self.evaluate_operand(operand)
        if isinstance(value, _Qubit):
            return value.index
        msg = f"Qubit expected: {operand}"
        raise ValueError(msg)

    def evaluate_operand(self, operand: qasm3Parser.GateOperandContext) -> _Value:
        child = operand.getChild(0)
        if child.getRuleIndex() == qasm3Parser.RULE_indexedIdentifier:
            identifier = child.Identifier().getText()
            value = self.env.get(identifier)
            if value is None:
                msg = f"name {identifier} is not defined"
                raise NameError(msg)
            for operator in child.indexOperator():
                if not isinstance(value, _Array):
                    msg = f"Array expected: {identifier}"
                    raise TypeError(msg)
                index = int(self.evaluate_expression(operator.expression(0)))
                if index < 0:
                    msg = f"Negative index: {identifier}"
                    raise IndexError(msg)
                if index >= len(value.values):
                    msg = f"Index out of bounds: {identifier} has length {len(value.values)}"
                    raise IndexError(msg)
                value = value.values[index]
            return value
        msg = f"Unknown operand: {operand}"
        raise NotImplementedError(msg)

    def evaluate_expression(self, expr: qasm3Parser.ExpressionContext) -> _Value:
        return _ExpressionVisitor(self).parse(expr)


class _ExpressionVisitor(qasm3ParserVisitor):
    circuit: _CircuitVisitor

    def __init__(self, circuit: _CircuitVisitor) -> None:
        self.circuit = circuit

    def parse(self, expr: qasm3Parser.ExpressionContext) -> _Value:
        value: _Value | None = expr.accept(self)
        if value is None:
            msg = f"Cannot parse value: {expr.getText()}"
            raise NotImplementedError(msg)
        return value

    @override
    def visitParenthesisExpression(self, ctx: qasm3Parser.ParenthesisExpressionContext) -> _Value:
        expr: qasm3Parser.ExpressionContext = ctx.expression()  # type: ignore[no-untyped-call]
        return self.parse(expr)

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

    def parse_binary_operator(
        self,
        ctx: qasm3Parser.AdditiveExpressionContext | qasm3Parser.MultiplicativeExpressionContext,
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
