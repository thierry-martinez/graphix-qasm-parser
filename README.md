# Graphix OpenQASM Parser

`graphix-qasm-parser` is a plugin for the
[Graphix](https://github.com/TeamGraphix/graphix) library that parses
OpenQASM circuit specifications into
`graphix.transpiler.Circuit` objects, which can then be transpiled
into MBQC patterns.

It is distributed as a separate plugin because it depends on
[`openqasm-parser`](https://github.com/qat-inria/openqasm-parser/).

## Installation

```bash
pip install https://github.com/TeamGraphix/graphix-qasm-parser.git
```

## Usage

### Parsing a string:

```python
from graphix_qasm_parser import OpenQASMParser

s = """
    include "qelib1.inc";
    qubit q;
    rz(5*pi/4) q;
"""
parser = OpenQASMParser()
circuit = parser.parse_str(s)
pattern = circuit.transpile().pattern
print(pattern)
```

### Parsing a file:

```python
circuit = parser.parse_file("my_circuit.qasm")
```

## Supported Specification

### [Qubits](https://openqasm.com/language/types.html#qubits)

- Single-qubit registers: `qubit q`, or the old syntax `qreg q`.

- Qubit register arrays: `qubit[n] q`, or the old syntax `qreg q[n]`.

### Supported Gates

| OpenQASM gate                                                    | Graphix instruction |
|------------------------------------------------------------------|---------------------|
| [ccx](https://openqasm.com/language/standard_library.html#ccx)   | CCX                 |
| [crz](https://openqasm.com/language/standard_library.html#crz)   | RZZ                 |
| [cx](https://openqasm.com/language/standard_library.html#cx)     | CX                  |
| [swap](https://openqasm.com/language/standard_library.html#swap) | SWAP                |
| [h](https://openqasm.com/language/standard_library.html#h)       | H                   |
| [s](https://openqasm.com/language/standard_library.html#s)       | S                   |
| [x](https://openqasm.com/language/standard_library.html#x)       | X                   |
| [y](https://openqasm.com/language/standard_library.html#y)       | Y                   |
| [z](https://openqasm.com/language/standard_library.html#z)       | Z                   |
| [id](https://openqasm.com/language/standard_library.html#id)     | I                   |
| [rx](https://openqasm.com/language/standard_library.html#rx)     | RX                  |
| [ry](https://openqasm.com/language/standard_library.html#ry)     | RY                  |
| [rz](https://openqasm.com/language/standard_library.html#rz)     | RZ                  |

### Expressions

Expressions with arithmetic operators (`+`, `-`, `*`, `/`, `%`) are supported.
The constant `pi` (or `π`) is defined.

[Compile-time constants](https://openqasm.com/language/types.html#compile-time-constants)
can be defined and used in expressions.


