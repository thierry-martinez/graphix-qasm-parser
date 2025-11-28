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
from graphix.instruction import CCX, CNOT, CZ, RX, RY, RZ, RZZ, SWAP, H, I, S, X, Y, Z
from openqasm_parser import qasm3Lexer, qasm3Parser, qasm3ParserVisitor

# override introduced in Python 3.12
from typing_extensions import override

if TYPE_CHECKING:
    from pathlib import Path

    from graphix.instruction import Instruction


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


@dataclass
class _Bit(_Value):
    index: int


@dataclass
class _Qubit(_Value):
    index: int


@dataclass
class _Array(_Value):
    values: list[_Value]


class _CircuitVisitor(qasm3ParserVisitor):
    parser: OpenQASMParser
    width: int
    instructions: list[Instruction]
    env: dict[str, _Value]

    def __init__(self, parser: OpenQASMParser) -> None:
        self.parser = parser
        self.width = 0
        self.instructions = []
        self.env = {
            "pi": _Float("pi", math.pi),
            "π": _Float("π", math.pi),
        }

    @override
    def visitOldStyleDeclarationStatement(self, ctx: qasm3Parser.OldStyleDeclarationStatementContext) -> None:
        decl_class: type[_Bit | _Qubit]
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
        designator = ctx.qubitType().designator()  # type: ignore[no-untyped-call]
        identifier = ctx.Identifier().getText()  # type: ignore[no-untyped-call]
        self.declare_registers(ctx, _Qubit, identifier, designator)

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
        instruction: Instruction
        if gate == "ccx":
            # https://openqasm.com/language/standard_library.html#ccx
            instruction = CCX(target=operands[2], controls=(operands[0], operands[1]))
        elif gate == "crz":
            # https://openqasm.com/language/standard_library.html#crz
            instruction = RZZ(target=operands[1], control=operands[0], angle=exprs[0])
        elif gate == "cx":
            # https://openqasm.com/language/standard_library.html#cx
            instruction = CNOT(target=operands[1], control=operands[0])
        elif gate == "swap":
            # https://openqasm.com/language/standard_library.html#swap
            instruction = SWAP(targets=(operands[0], operands[1]))
        elif gate == "cz":
            # https://openqasm.com/language/standard_library.html#cz
            instruction = CZ(targets=(operands[0], operands[1]))
        elif gate == "h":
            # https://openqasm.com/language/standard_library.html#h
            instruction = H(target=operands[0])
        elif gate == "s":
            # https://openqasm.com/language/standard_library.html#s
            instruction = S(target=operands[0])
        elif gate == "x":
            # https://openqasm.com/language/standard_library.html#x
            instruction = X(target=operands[0])
        elif gate == "y":
            # https://openqasm.com/language/standard_library.html#y
            instruction = Y(target=operands[0])
        elif gate == "z":
            # https://openqasm.com/language/standard_library.html#z
            instruction = Z(target=operands[0])
        elif gate == "id":
            # https://openqasm.com/language/standard_library.html#id
            instruction = I(target=operands[0])
        elif gate == "rx":
            # https://openqasm.com/language/standard_library.html#rx
            instruction = RX(target=operands[0], angle=exprs[0])
        elif gate == "ry":
            # https://openqasm.com/language/standard_library.html#ry
            instruction = RY(target=operands[0], angle=exprs[0])
        elif gate == "rz":
            # https://openqasm.com/language/standard_library.html#rz
            instruction = RZ(target=operands[0], angle=exprs[0])
        else:
            msg = f"Unknown gate: {gate}"
            raise NotImplementedError(msg)
        self.instructions.append(instruction)

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
        self, ctx: qasm3Parser.AdditiveExpressionContext | qasm3Parser.MultiplicativeExpressionContext
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
