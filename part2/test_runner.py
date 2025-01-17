import os
import pytest
from pathlib import Path
from cocotb.runner import get_runner

G_DATA_WIDTH = [8, 10, 12, 16]
G_N_COLOR_COMPONENTS = [3]

@pytest.mark.parametrize("g_data_width", G_DATA_WIDTH, ids=[f"G_DATA_WIDTH={i}" for i in G_DATA_WIDTH])
@pytest.mark.parametrize("g_n_color_components", G_N_COLOR_COMPONENTS, ids=[f"G_N_COLOR_COMPONENTS={i}" for i in G_N_COLOR_COMPONENTS])
def test_axis_design_runner(g_data_width, g_n_color_components):

    sim = os.getenv("SIM", "ghdl")

    proj_path = Path(__file__).resolve().parent

    runner = get_runner(sim)

    hdl_toplevel = "axis_design"

    runner.build(
        sources=[proj_path / "axis_design.vhd"],
        hdl_toplevel=hdl_toplevel,
        parameters={
            "G_DATA_WIDTH": g_data_width,
            "G_N_COLOR_COMPONENTS": g_n_color_components
        },
        always=True # always rebuild on each run
    )

    runner.test(
        test_module="test_axis_design,",
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
    test_axis_design_runner(
        g_data_width = 8,
        g_n_color_components = 3
    )

    ## Otherwise use pytest for parameterized tests
    # SIM=ghdl pytest test_runner.py
