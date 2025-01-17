
import cocotb
from cocotb.triggers import RisingEdge, Timer
from cocotb.clock import Clock

async def run_reset_routine(dut):
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.reset_n.value = 1

@cocotb.test()
async def my_test_case(dut):

    # Generate a clock
    cocotb.start_soon(Clock(dut.clk, 1, units="ns").start())

    # Reset DUT reset_n
    dut.reset_n.value = 0

    # Set DUT data
    dut.i_Data.value = 0xA

    # Reset the module, wait 3 rising edges then release reset
    cocotb.start_soon(run_reset_routine(dut))

    await Timer(10, units="ns")  # wait a bit

    expected = 0
    dut._log.info("s_signal_1 is %s", dut.s_signal_1.value)
    assert dut.s_signal_2.value[0] == expected, f"Error: s_signal_2[0] is not {expected}!"

    expected = 16
    dut._log.info(f"G_DATA_WIDTH is  {dut.G_DATA_WIDTH.value} in binary and {dut.G_DATA_WIDTH.value.integer} as integer")
    assert dut.G_DATA_WIDTH.value.integer == expected, f"Error: G_DATA_WIDTH is not {expected}!"
