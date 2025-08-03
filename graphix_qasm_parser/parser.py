"""Graphix OpenQASM parser."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from antlr4 import (  # type: ignore[attr-defined]
    CommonTokenStream,
    FileStream,
    InputStream,
)
from graphix import Circuit
from graphix.instruction import CCX, CNOT, RX, RY, RZ, RZZ, SWAP, H, S, X, Y, Z
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
        visitor = _CircuitVisitor()
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


class _Value:
    pass


@dataclass
class _Creg(_Value):
    index: int


@dataclass
class _Qreg(_Value):
    index: int


@dataclass
class _Array(_Value):
    values: list[_Value]


class _CircuitVisitor(qasm3ParserVisitor):
    width: int
    instructions: list[Instruction]
    env: dict[str, _Value]

    def __init__(self) -> None:
        self.width = 0
        self.instructions = []
        self.env = {}

    @override
    def visitOldStyleDeclarationStatement(self, ctx: qasm3Parser.OldStyleDeclarationStatementContext) -> None:
        decl_class: type[_Creg | _Qreg]
        value: _Value
        kind = ctx.getChild(0)
        if kind.symbol.type == qasm3Parser.QREG:
            decl_class = _Qreg
        elif kind.symbol.type == qasm3Parser.CREG:
            decl_class = _Creg
        else:
            msg = f"Unknown declaration statement kind: {kind}"
            raise NotImplementedError(msg)
        identifier = ctx.Identifier().getText()  # type: ignore[no-untyped-call]
        if designator := ctx.designator():  # type: ignore[no-untyped-call]
            count = self.evaluate_expression_int(designator.expression())
            value = _Array([decl_class(self.width + i) for i in range(count)])
            self.width += count
        else:
            value = decl_class(self.width)
            self.width += 1
        self.env[identifier] = value

    @override
    def visitGateCallStatement(self, ctx: qasm3Parser.GateCallStatementContext) -> None:  # noqa: C901, PLR0912
        gate = ctx.Identifier().getText()  # type: ignore[no-untyped-call]
        operand_list = ctx.gateOperandList()  # type: ignore[no-untyped-call]
        operands = [
            self.convert_qubit_index(operand_list.getChild(i)) for i in range(0, operand_list.getChildCount(), 2)
        ]
        if expr_list := ctx.expressionList():  # type: ignore[no-untyped-call]
            exprs = [
                self.evaluate_expression_float(expr_list.getChild(i)) for i in range(0, expr_list.getChildCount(), 2)
            ]
        else:
            exprs = []
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

    def convert_qubit_index(self, operand: qasm3Parser.GateOperandContext) -> int:
        value = self.evaluate_operand(operand)
        if isinstance(value, _Qreg):
            return value.index
        msg = f"Qubit expected: {operand}"
        raise ValueError(msg)

    def evaluate_operand(self, operand: qasm3Parser.GateOperandContext) -> _Value:
        child = operand.getChild(0)
        if child.getRuleIndex() == qasm3Parser.RULE_indexedIdentifier:
            identifier = child.Identifier().getText()
            array = self.env[identifier]
            if not isinstance(array, _Array):
                msg = f"Array expected: {operand}"
                raise TypeError(msg)
            index = self.evaluate_expression_int(child.getChild(1).getChild(1))
            if index < 0:
                msg = f"Negative index: {operand}"
                raise ValueError(msg)
            if index >= len(array.values):
                msg = f"Index out of bounds: {identifier} has length {len(array.values)}"
                raise ValueError(msg)
            return array.values[index]
        msg = f"Unknown operand: {operand}"
        raise NotImplementedError(msg)

    def evaluate_expression_float(self, expr: qasm3Parser.ExpressionContext) -> float:
        if expr.getChildCount() == 3:
            lhs = self.evaluate_expression_float(expr.getChild(0))
            rhs = self.evaluate_expression_float(expr.getChild(2))
            operator = expr.getChild(1).symbol.type
            if operator == qasm3Parser.SLASH:
                return lhs / rhs
            if operator == qasm3Parser.ASTERISK:
                return lhs * rhs
        else:
            child = expr.getChild(0)
            if child.symbol.type == qasm3Parser.DecimalIntegerLiteral:
                return int(child.symbol.text)
            if child.symbol.type == qasm3Parser.FloatLiteral:
                return float(child.symbol.text)
            if child.symbol.type == qasm3Parser.Identifier:
                identifier = child.symbol.text
                if identifier == "pi":
                    return math.pi
        msg = f"Unknown expression: {expr}"
        raise NotImplementedError(msg)

    def evaluate_expression_int(self, expr: qasm3Parser.ExpressionContext) -> int:
        value = self.evaluate_expression_float(expr)
        if not isinstance(value, int):
            msg = "Integer expected: {value}"
            raise TypeError(msg)
        return value
