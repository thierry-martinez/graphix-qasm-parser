"""Graphix OpenQASM parser."""

from __future__ import annotations

import enum
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Generic, TypeVar

from antlr4 import (  # type: ignore[attr-defined]
    CommonTokenStream,
    FileStream,
    InputStream,
    ParserRuleContext,
)
from graphix import Circuit, Instruction
from graphix.fundamentals import Axis, rad_to_angle
from openqasm_parser import qasm3Lexer, qasm3Parser, qasm3ParserVisitor

# override introduced in Python 3.12
from typing_extensions import override

if TYPE_CHECKING:
    from pathlib import Path

    from graphix.instruction import InstructionType


_T = TypeVar("_T")


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
        msg = f"Not an integer value: {self.report_ctx()}"
        raise TypeError(msg)

    def __float__(self) -> float:
        msg = f"Not a floating-point value: {self.report_ctx()}"
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

    Note that bit registers cannot be referenced yet, since we do not
    support conditional instructions yet. Support for conditional
    instructions will be introduced in
    https://github.com/TeamGraphix/graphix-qasm-parser/pull/17.
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
class _Array(_Value):
    values: list[_Value]


class _CircuitVisitor(qasm3ParserVisitor):
    parser: OpenQASMParser
    width: int
    measurement_count: int
    instructions: list[InstructionType]
    env: dict[str, _Value]

    def __init__(self, parser: OpenQASMParser) -> None:
        self.parser = parser
        self.width = 0
        self.measurement_count = 0
        self.instructions = []
        self.env = {
            "pi": _Float("pi", math.pi),
            "π": _Float("π", math.pi),
        }

    @override
    def visitOldStyleDeclarationStatement(self, ctx: qasm3Parser.OldStyleDeclarationStatementContext) -> None:
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
        identifier = ctx.Identifier().getText()  # type: ignore[no-untyped-call]
        value = ctx.declarationExpression()  # type: ignore[no-untyped-call]
        expr = self.evaluate_expression(value)
        self.env[identifier] = expr

    @override
    def visitGateCallStatement(self, ctx: qasm3Parser.GateCallStatementContext) -> None:  # noqa: C901, PLR0912
        gate = ctx.Identifier().getText()  # type: ignore[no-untyped-call]
        operand_list = ctx.gateOperandList()  # type: ignore[no-untyped-call]
        operands = [
            self.convert_qubit_index(operand_list.getChild(i)) for i in range(0, operand_list.getChildCount(), 2)
        ]
        if expr_list := ctx.expressionList():  # type: ignore[no-untyped-call]
            exprs = [
                float(self.evaluate_expression(expr_list.getChild(i))) for i in range(0, expr_list.getChildCount(), 2)
            ]
        else:
            exprs = []
        instruction: InstructionType
        if gate == "ccx":
            # https://openqasm.com/language/standard_library.html#ccx
            instruction = Instruction.CCX(target=operands[2], controls=(operands[0], operands[1]))
        elif gate == "cx":
            # https://openqasm.com/language/standard_library.html#cx
            instruction = Instruction.CNOT(target=operands[1], control=operands[0])
        elif gate == "swap":
            # https://openqasm.com/language/standard_library.html#swap
            instruction = Instruction.SWAP(targets=(operands[0], operands[1]))
        elif gate == "cz":
            # https://openqasm.com/language/standard_library.html#cz
            instruction = Instruction.CZ(targets=(operands[0], operands[1]))
        elif gate == "h":
            # https://openqasm.com/language/standard_library.html#h
            instruction = Instruction.H(target=operands[0])
        elif gate == "s":
            # https://openqasm.com/language/standard_library.html#s
            instruction = Instruction.S(target=operands[0])
        elif gate == "x":
            # https://openqasm.com/language/standard_library.html#x
            instruction = Instruction.X(target=operands[0])
        elif gate == "y":
            # https://openqasm.com/language/standard_library.html#y
            instruction = Instruction.Y(target=operands[0])
        elif gate == "z":
            # https://openqasm.com/language/standard_library.html#z
            instruction = Instruction.Z(target=operands[0])
        elif gate == "id":
            # https://openqasm.com/language/standard_library.html#id
            instruction = Instruction.I(target=operands[0])
        elif gate == "rx":
            # https://openqasm.com/language/standard_library.html#rx
            instruction = Instruction.RX(target=operands[0], angle=rad_to_angle(exprs[0]))
        elif gate == "ry":
            # https://openqasm.com/language/standard_library.html#ry
            instruction = Instruction.RY(target=operands[0], angle=rad_to_angle(exprs[0]))
        elif gate == "rz":
            # https://openqasm.com/language/standard_library.html#rz
            instruction = Instruction.RZ(target=operands[0], angle=rad_to_angle(exprs[0]))
        else:
            msg = f"Unknown gate: {gate}"
            raise NotImplementedError(msg)
        self.instructions.append(instruction)

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
        body = tuple(self.instructions)
        instruction = Instruction.CONDINSTR(body, domain)
        self.instructions = parent_instructions
        self.instructions.append(instruction)

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
            result = lhs | rhs
        else:
            msg = f"Unknown operator: {ctx.getChild(1).symbol.text}"
            raise NotImplementedError(msg)
        return result
