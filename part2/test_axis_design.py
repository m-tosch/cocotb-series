
import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock
from cocotbext.axi import (AxiStreamBus, AxiStreamSource, AxiStreamSink)
import logging

from AxiStreamImage import AxiStreamImage
import utility


async def run_reset_routine(dut):
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.reset_n.value = 1

@cocotb.test()
async def axis_test_case(dut):

    # DEBUG=10, INFO=20, WARNING=30, ERROR=40, CRITICAL=50
    dut._log.setLevel(logging.INFO)

    # Generate a clock
    cocotb.start_soon(Clock(dut.clk, 5, units="ns").start())

    # Generics
    data_width = int(dut.G_DATA_WIDTH.value)
    n_color_components = int(dut.G_N_COLOR_COMPONENTS.value)
    byte_size = data_width * n_color_components
    dut._log.info(f"NOTE: byte size will be set to G_N_COLOR_COMPONENTS*G_DATA_WIDTH = {n_color_components}*{data_width} = {byte_size}")

    # AxiStream
    axis_source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis_video"), dut.clk, dut.reset_n, reset_active_level=False, byte_size=byte_size)
    axis_sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis_video"), dut.clk, dut.reset_n, reset_active_level=False, byte_size=byte_size)

    # Reset DUT reset_n
    dut.reset_n.value = 0

    # Reset AXI stream input signals
    dut.s_axis_video_tvalid.value = 0
    dut.s_axis_video_tuser.value = 0
    dut.s_axis_video_tlast.value = 0
    dut.s_axis_video_tdata.value = 0
    dut.m_axis_video_tready.value = 0

    # Reset the module, wait 3 rising edges then release reset
    cocotb.start_soon(run_reset_routine(dut))
    # wait until reset is released
    await RisingEdge(dut.reset_n)
    # wait until next clock rising edge
    await RisingEdge(dut.clk)

    # all images
    n_frames = 3
    axis_images = []

    # image
    tx_image_data, width, height, max_value = utility.read_pnm(f"../images/RGBRandom_4x3_{data_width}bit.pnm")

    ### SEND ###
    for _ in range(n_frames):
        # create a stream image
        axis_image = AxiStreamImage(tx_image_data, width, height)

        # send stream image
        await axis_image.send(axis_source)
        await axis_source.wait() # wait until axi stream source is idle again i.e. all data has been send

        axis_images.append(axis_image)

    ### RECEIVE ###
    for im_idx,image in enumerate(axis_images): # all images (n * width * height)
        rx_image_data = []
        for fr_idx,frames in enumerate(image): # all "frames" i.e. lines (width * height)
            # receive 1 frame i.e. line. compact=False ensures that tuser signal is kept as type <list> internally
            rx_frame = await axis_sink.recv(compact=False)
            rx_image_data.extend(rx_frame.tdata)

            # check tdata signal
            assert list(rx_frame.tdata) == frames.tdata, f"data mismatch in image: {im_idx} line: {fr_idx}"

            # check tuser signal
            if fr_idx == 0:
                assert rx_frame.tuser[0] == 1, "tuser[0] is not 1 for first pixel in first line"
                assert all(x == 0 for x in rx_frame.tuser[1:]), "tuser for subsequent pixels should be 0"
            else:
                assert all(x == 0 for x in rx_frame.tuser), "tuser for subsequent pixels should be 0"

        # write output image to disk
        utility.write_pnm(rx_image_data, width, height, max_value, f"../images/output/output_{im_idx:04d}.pnm", format='P3')

    assert axis_source.empty(), "AxiStreamMaster (source) not empty"
    assert axis_sink.empty(), "AxiStreamSource (sink) not empty"