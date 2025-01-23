import os
import pytest
from pathlib import Path
from cocotb.runner import get_runner

# DUT parameters
G_DATA_WIDTH = [8, 10, 12, 16]
G_N_COLOR_COMPONENTS = [3]
G_PIXEL_PER_CLOCK = [1, 2, 4]

@pytest.mark.parametrize("g_data_width", G_DATA_WIDTH, ids=[f" G_DATA_WIDTH={i} " for i in G_DATA_WIDTH])
@pytest.mark.parametrize("g_n_color_components", G_N_COLOR_COMPONENTS, ids=[f" G_N_COLOR_COMPONENTS={i} " for i in G_N_COLOR_COMPONENTS])
@pytest.mark.parametrize("g_pixel_per_clock", G_PIXEL_PER_CLOCK, ids=[f" G_PIXEL_PER_CLOCK={i} " for i in G_PIXEL_PER_CLOCK])
def test_axis_design_runner(
    g_data_width,
    g_n_color_components,
    g_pixel_per_clock
):
    sim = os.getenv("SIM", "ghdl")

    proj_path = Path(__file__).resolve().parent

    runner = get_runner(sim)

    hdl_toplevel = "axis_design"

    runner.build(
        sources=[proj_path / "axis_design.vhd"],
        hdl_toplevel=hdl_toplevel,
        parameters={
            "G_DATA_WIDTH": g_data_width,
            "G_N_COLOR_COMPONENTS": g_n_color_components,
            "G_PIXEL_PER_CLOCK": g_pixel_per_clock
        },
        always=True # always run the build step
    )

    runner.test(
        test_module="test_axis_design",
        hdl_toplevel=hdl_toplevel,
        hdl_toplevel_lang="vhdl",
        seed=1871423625,
        plusargs=[
            "--wave=waveform.ghw",
        ],
        extra_env={
            # writes result pnm image to disk if "True"
            # use this in combination with a specified testcase
            "WRITE_IMAGE_OUTPUT": "False"
        },
        # testcase=["run_axi_stream_1_frame_4x3"]
    )


if __name__ == "__main__":

    ## Default, single test case
    # python test_runner.py
    test_axis_design_runner(
        g_data_width = 8,
        g_n_color_components = 3,
        g_pixel_per_clock = 4
    )

    ## Otherwise use pytest for parameterized tests
    # pytest -v test_runner.py
