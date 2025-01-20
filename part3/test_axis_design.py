
import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock
from cocotbext.axi import (AxiStreamBus, AxiStreamSource, AxiStreamSink, AxiStreamFrame)

from AxiStreamImage import AxiStreamImage
import utility

import logging
import random
import os


async def run_reset_routine(dut):
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.reset_n.value = 1



def pause_generator():
    while True:
        yield bool(random.getrandbits(1))



async def setup(dut, idle_inserter, backpressure_inserter):

    # Set log level. DEBUG=10, INFO=20, WARNING=30, ERROR=40, CRITICAL=50
    dut._log.setLevel(logging.WARNING)

    # Generate a clock
    cocotb.start_soon(Clock(dut.clk, 5, units="ns").start())

    # Generics
    data_width = int(dut.G_DATA_WIDTH.value)
    n_color_components = int(dut.G_N_COLOR_COMPONENTS.value)
    byte_size = n_color_components*data_width
    dut._log.info(f"NOTE: byte size will be set to G_N_COLOR_COMPONENTS*G_DATA_WIDTH = {n_color_components}*{data_width} = {byte_size}")

    # AXI master
    axis_source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis_video"), dut.clk, dut.reset_n, reset_active_level=False, byte_size=byte_size)
    if idle_inserter:
        axis_source.set_pause_generator(idle_inserter)
    # AXI slave
    axis_sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis_video"), dut.clk, dut.reset_n, reset_active_level=False, byte_size=byte_size)
    if backpressure_inserter:
        axis_sink.set_pause_generator(backpressure_inserter)

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

    return axis_source, axis_sink



async def send(dut, axis_source, n_frames, tx_image_data, width, height):
    axis_images = []
    for _ in range(n_frames):
        # create a stream image
        axis_image = AxiStreamImage(tx_image_data, width, height)

        # send stream image
        await axis_image.send(axis_source)
        await axis_source.wait() # wait until axi stream source is idle again i.e. all data has been send

        axis_images.append(axis_image)

    return axis_images



async def recv(dut, axis_sink, n_frames, height):
    rx_axis_images = []
    for _ in range(n_frames):
        rx_frames = []
        for _ in range(height):
            # receive 1 frame i.e. line. compact=False ensures that tuser signal is kept as type <list>
            rx_frame = await axis_sink.recv(compact=False)
            ## await axis_sink.wait()
            rx_frames.append(rx_frame)

        rx_axis_image = AxiStreamImage.from_frames(rx_frames)
        rx_axis_images.append(rx_axis_image)

    await RisingEdge(dut.clk) # optional

    return rx_axis_images



def coco(axis_tx_images):
    coco_images = []
    for image in axis_tx_images:
        coco_frames = []
        for line in range(len(image.axis_frames)):
            #### #### #### #### #### #### #### #### #### #### #### ####

            # simulation co-processing. implements the same operation as HW code
            coco_pixel = [x + 1 for x in image[line].tdata]

            #### #### #### #### #### #### #### #### #### #### #### ####
            coco_frames.append(AxiStreamFrame(tdata=coco_pixel, tuser=image[line].tuser))
        coco_images.append(AxiStreamImage.from_frames(coco_frames))

    return coco_images



def assert_tuser_signal(axis_rx_images):
    for rx_image in axis_rx_images:  # all images (n * width * height)
        for frame_idx, rx_frame in enumerate(rx_image): # all "frames" i.e. lines (width * height)
            # check tuser signal
            if frame_idx == 0:
                assert rx_frame.tuser[0] == 1, "tuser[0] is not 1 for first pixel in first line"
                assert all(x == 0 for x in rx_frame.tuser[1:]), "tuser for subsequent pixels should be 0"
            else:
                assert all(x == 0 for x in rx_frame.tuser), "tuser for subsequent pixels should be 0"



def assert_tdata_signal(coco_images, axis_rx_images):
    for image_idx, (coco_image, rx_image) in enumerate(zip(coco_images, axis_rx_images)):  # all images (n * width * height)
        for frame_idx, (coco_frame, rx_frame) in enumerate(zip(coco_image, rx_image)): # all "frames" i.e. lines (width * height)
            # check tdata signal
            assert list(rx_frame.tdata) == coco_frame.tdata, f"data mismatch in image: {image_idx} line: {frame_idx}"



async def axi_stream(dut, n_frames, size, idle_inserter, backpressure_inserter):

    # SETUP
    axis_source, axis_sink = await setup(dut, idle_inserter, backpressure_inserter)

    # READ FILE
    tx_image_data, width, height, max_value = utility.read_pnm(f"../images/RGBRandom_{size}_{int(dut.G_DATA_WIDTH.value)}bit.pnm")

    # SEND
    axis_tx_images = await send(dut, axis_source, n_frames, tx_image_data, width, height)

    # CO-PROCESSING
    coco_images = coco(axis_tx_images)

    # RECV
    axis_rx_images = await recv(dut, axis_sink, n_frames, height)

    # WRITE FILE
    if os.environ.get('WRITE_IMAGE_OUTPUT') == 'True':
        for idx, rx_image in enumerate(axis_rx_images):
            utility.write_pnm(rx_image.data(), width, height, max_value, f"../images/output/output_{idx:04d}.pnm", format='P3')

    # ASSERT
    assert axis_source.empty(), "AxiStreamMaster (source) not empty"
    assert axis_sink.empty(), "AxiStreamSource (sink) not empty"
    assert_tuser_signal(axis_rx_images)
    assert_tdata_signal(coco_images, axis_rx_images)



# NOTE: In cocotb 2.0 the first 16 tests specified below will be something like this instead:
#
# @cocotb.parametrize(
#     n_frames=[1, 3],
#     size=["4x3", "20x10"],
#     idle_inserter=[None, pause_generator()],
#     backpressure_inserter=[None, pause_generator()],
# )
# @cocotb.test()
# async def run_axi_stream(dut, n_frames, idle_inserter, backpressure_inserter):
#     await axi_stream(dut, idle_inserter, backpressure_inserter)

@cocotb.test()
async def run_axi_stream_1_frame_4x3(dut):
    await axi_stream(dut, 1, "4x3", None, None)

@cocotb.test()
async def run_axi_stream_1_frame_4x3_random_tvalid(dut):
    await axi_stream(dut, 1, "4x3", pause_generator(), None)

@cocotb.test()
async def run_axi_stream_1_frame_4x3_random_tready(dut):
    await axi_stream(dut, 1, "4x3", None, pause_generator())

@cocotb.test()
async def run_axi_stream_1_frame_4x3_random_tvalid_random_tready(dut):
    await axi_stream(dut, 1, "4x3", pause_generator(), pause_generator())

@cocotb.test()
async def run_axi_stream_3_frames_4x3(dut):
    await axi_stream(dut, 3, "4x3", None, None)

@cocotb.test()
async def run_axi_stream_3_frames_4x3_random_tvalid(dut):
    await axi_stream(dut, 3, "4x3", pause_generator(), None)

@cocotb.test()
async def run_axi_stream_3_frames_4x3_random_tready(dut):
    await axi_stream(dut, 3, "4x3", None, pause_generator())

@cocotb.test()
async def run_axi_stream_3_frames_4x3_random_tvalid_random_tready(dut):
    await axi_stream(dut, 3, "4x3", pause_generator(), pause_generator())

@cocotb.test()
async def run_axi_stream_1_frame_20x10(dut):
    await axi_stream(dut, 1, "20x10", None, None)

@cocotb.test()
async def run_axi_stream_1_frame_20x10_random_tvalid(dut):
    await axi_stream(dut, 1, "20x10", pause_generator(), None)

@cocotb.test()
async def run_axi_stream_1_frame_20x10_random_tready(dut):
    await axi_stream(dut, 1, "20x10", None, pause_generator())

@cocotb.test()
async def run_axi_stream_1_frame_20x10_random_tvalid_random_tready(dut):
    await axi_stream(dut, 1, "20x10", pause_generator(), pause_generator())

@cocotb.test()
async def run_axi_stream_3_frames_20x10(dut):
    await axi_stream(dut, 3, "20x10", None, None)

@cocotb.test()
async def run_axi_stream_3_frames_20x10_random_tvalid(dut):
    await axi_stream(dut, 3, "20x10", pause_generator(), None)

@cocotb.test()
async def run_axi_stream_3_frames_20x10_random_tready(dut):
    await axi_stream(dut, 3, "20x10", None, pause_generator())

@cocotb.test()
async def run_axi_stream_3_frames_20x10_random_tvalid_random_tready(dut):
    await axi_stream(dut, 3, "20x10", pause_generator(), pause_generator())

@cocotb.test()
async def generics_range(dut):
    G_DATA_WIDTH = int(dut.G_DATA_WIDTH.value)
    assert G_DATA_WIDTH in [8, 10, 12, 16]

    G_N_COLOR_COMPONENTS = int(dut.G_N_COLOR_COMPONENTS.value)
    assert G_N_COLOR_COMPONENTS in [3]
