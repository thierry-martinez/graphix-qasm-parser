# Graphix OpenQASM Parser

This repository provides the Python package `graphix-qasm-parser`,
which is a plugin for the
[`Graphix`](https://github.com/TeamGraphix/graphix/) library.
This package provides a parser to read OpenQASM circuit specifications
into `graphix.transpiler.Circuit`, that can in turn be transpiled
by `Graphix` into MBQC patterns.

This functionality is provided as a plugin since this package relies on the additional dependency
[`openqasm-parser`](https://github.com/qat-inria/openqasm-parser/).

## Getting Started

To use the OpenQASM parser with Graphix:

1. Install the plugin:

```bash
pip install https://github.com/thierry-martinez/graphix-qasm-parser.git
```

2. Instantiate a `OpenQASMParser` and use the `parse_str` method to
   parse a given OpenQASM specification:
```python
s = """
    include "qelib1.inc";
    qreg q[1];
    rz(5*pi/4) q[0];
"""
parser = OpenQASMParser()
circuit = parser.parse_str(s)
pattern = circuit.transpile().pattern
print(pattern)
```
   To parse a file, use the `parse_file` method.

## Specification Support

This package supports the definition of single qubit registers and qubit register arrays.

The following gates are supported:

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
| [rx](https://openqasm.com/language/standard_library.html#rx)     | RX                  |
| [ry](https://openqasm.com/language/standard_library.html#ry)     | RY                  |
| [rz](https://openqasm.com/language/standard_library.html#rz)     | RZ                  |
