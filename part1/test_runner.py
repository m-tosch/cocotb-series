import os
import pytest
from pathlib import Path
from cocotb.runner import get_runner

G_DATA_WIDTH = [8, 16, 24]

@pytest.mark.parametrize("g_data_width", G_DATA_WIDTH, ids=[f"G_DATA_WIDTH={i}" for i in G_DATA_WIDTH])
def test_my_design_runner(g_data_width):

    sim = os.getenv("SIM", "ghdl")

    proj_path = Path(__file__).resolve().parent

    runner = get_runner(sim)

    hdl_toplevel = "my_design"

    runner.build(
        sources=[proj_path / "my_design.vhd"],
        hdl_toplevel=hdl_toplevel,
        parameters={
            "G_DATA_WIDTH": g_data_width
        },
        always=True # always rebuild on each run
    )

    runner.test(
        test_module="test_my_design,",
        hdl_toplevel=hdl_toplevel,
        hdl_toplevel_lang="vhdl",
        seed=1871423625,
        plusargs=[
            "--wave=waveform.ghw"
        ],
    )


if __name__ == "__main__":

    ## Default, single test case
    # SIM=ghdl python test_runner.py
    test_my_design_runner(g_data_width=16)

    ## Otherwise use pytest for parameterized tests
    # SIM=ghdl pytest test_runner.py
