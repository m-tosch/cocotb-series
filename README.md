# cocotb-series

Educational tutorial series to learn FPGA verification framework cocotb

# Scope

This series dives into the FPGA verification framework cocotb using hands-on examples. The main use case that is presented is AXI image transfer and processing. Each chapter of the series builds upon the previous one consecutively. 

Central topics

- Parameterized tests (generics, data inputs...etc.)
- Simulation co-processing
- AXI4-stream, AXI4-Lite bus interface support
- Random AXI4-stream handshake toggling
- command line execution for tests
- waveform analysis

DISCLAIMER: The series is designed for educational purposes. It was authored at a specific point in time using particular versions of tools, which quite possibly have since been updated or changed.

# Prerequisites

A working Linux environment with python, cocotb, ghdl and gtkwave installed.

# Chapters

<div align="center">

| Part    | Description |
| -------- | ------- |
| [Part 1](https://github.com/m-tosch/cocotb-series/tree/main/part1) <br> "The beginning"  | Intro. Simple DUT with parameterized cocotb testbench. Waveform viewer.   |
| [Part 2](https://github.com/m-tosch/cocotb-series/tree/main/part2) <br> "AXI-stream images" |  Using AXI-stream master/slave to stream data through a DUT. 1 PPC. Assert image data. Read and write RGB pnm images.    |
| [Part 3](https://github.com/m-tosch/cocotb-series/tree/main/part3) <br> "More tests and simulation co-processing"    |  Parameterization for cocotb tests. Multiple cocotb test functions. Select test cases. Simulation co-processing. Environment variables.   |
| Part 4 <br> "Debugging a design error"    |   Improve test asserts. Support for 2 and 4 PPC AXI-stream. Debug error in design through test cases, waveform and Python debugger.  |
| Part 5 <br> "AXI-lite register access"    |   AXI-lite implementation to r/w registers. Random handshake toggling. VHDL 2008 sources. More simulator arguments. Specialized setup functions.  |

</div>
