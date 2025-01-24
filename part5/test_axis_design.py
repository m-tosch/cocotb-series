
import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer, ClockCycles
from cocotb.clock import Clock
from cocotbext.axi import (AxiStreamBus, AxiStreamSource, AxiStreamSink, AxiStreamMonitor, AxiStreamFrame)
from cocotbext.axi import (AxiLiteMaster, AxiLiteBus)
from AxiStreamImage import AxiStreamImage
import utility

from pathlib import Path
import logging
import random
import math
import os

async def run_reset_routine(dut):
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.reset_n.value = 1


def pause_generator():
    while True:
        yield bool(random.getrandbits(1))


async def setup_sim(dut):

    # Set log level. DEBUG=10, INFO=20, WARNING=30, ERROR=40, CRITICAL=50
    dut._log.setLevel(logging.WARNING)

    # Generate a clock
    cocotb.start_soon(Clock(dut.clk, 5, units="ns").start())

    # Reset DUT reset_n
    dut.reset_n.value = 0

    # Reset AXI stream input signals
    dut.s_axis_video_tvalid.value = 0
    dut.s_axis_video_tuser.value = 0
    dut.s_axis_video_tlast.value = 0
    dut.s_axis_video_tdata.value = 0
    dut.m_axis_video_tready.value = 0
    # Reset AXI lite input signals
    dut.s_axi_ctrl_awaddr.value = 0
    dut.s_axi_ctrl_awvalid.value = 0
    dut.s_axi_ctrl_wdata.value = 0
    dut.s_axi_ctrl_wstrb.value = 0
    dut.s_axi_ctrl_wvalid.value = 0
    dut.s_axi_ctrl_araddr.value = 0
    dut.s_axi_ctrl_arvalid.value = 0
    dut.s_axi_ctrl_rready.value = 0
    dut.s_axi_ctrl_bready.value = 0

    # Reset the module, wait 3 rising edges then release reset
    cocotb.start_soon(run_reset_routine(dut))

    # wait until reset is released
    await RisingEdge(dut.reset_n)
    # wait until next clock rising edge
    await RisingEdge(dut.clk)


async def setup_axis(dut, idle_inserter, backpressure_inserter):
    # Generics
    data_width = int(dut.G_DATA_WIDTH.value)
    n_color_components = int(dut.G_N_COLOR_COMPONENTS.value)
    pixel_per_clock = int(dut.G_PIXEL_PER_CLOCK.value)
    #
    byte_size = pixel_per_clock*n_color_components*data_width
    dut._log.info(f"NOTE: byte size will be set to G_PIXEL_PER_CLOCK*G_N_COLOR_COMPONENTS*G_DATA_WIDTH = {pixel_per_clock}*{n_color_components}*{data_width} = {byte_size}")
    dut._log.info(f"NOTE: Running simulation with RANDOM_SEED: {cocotb.RANDOM_SEED}")

    # AXI master
    axis_source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "s_axis_video"), dut.clk, dut.reset_n, reset_active_level=False, byte_size=byte_size)
    if idle_inserter:
        axis_source.set_pause_generator(idle_inserter)
    # AXI slave
    axis_sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "m_axis_video"), dut.clk, dut.reset_n, reset_active_level=False, byte_size=byte_size)
    if backpressure_inserter:
        axis_sink.set_pause_generator(backpressure_inserter)

    return axis_source, axis_sink


async def setup_axilite(dut, idle_inserter, backpressure_inserter):
    # AXI lite master
    # NOTE By default, AxiLiteMaster assumes a 32-bit data width
    axilite_master = AxiLiteMaster(AxiLiteBus.from_prefix(dut, "s_axi_ctrl"), dut.clk, dut.reset_n, reset_active_level=False)
    if idle_inserter:
        axilite_master.write_if.aw_channel.set_pause_generator(pause_generator())
        axilite_master.write_if.w_channel.set_pause_generator(pause_generator())
        axilite_master.read_if.ar_channel.set_pause_generator(pause_generator())
    if backpressure_inserter:
        axilite_master.write_if.b_channel.set_pause_generator(pause_generator())
        axilite_master.read_if.r_channel.set_pause_generator(pause_generator())

    return axilite_master


async def send(dut, axis_source, n_frames, tx_data, width, height):
    # generics
    pixel_per_clock = int(dut.G_PIXEL_PER_CLOCK.value)
    data_width = int(dut.G_DATA_WIDTH.value)
    n_color_components = int(dut.G_N_COLOR_COMPONENTS.value)
    # >1 PPC parameters
    bit_shift = data_width*n_color_components

    # send images
    axis_images = []
    for _ in range(n_frames):
        # 1 PPC
        if pixel_per_clock == 1:
            axis_image = AxiStreamImage(tx_data, width, height)
        # 2 PPC
        elif pixel_per_clock == 2:
            data = [(tx_data[i+1] << (1 * bit_shift) |
                     tx_data[i]) for i in range(0, len(tx_data), 2)]
            axis_image = AxiStreamImage(data, width//pixel_per_clock, height)
        # 4 PPC
        elif pixel_per_clock == 4:
            data = [(tx_data[i+3] << (3 * bit_shift) |
                     tx_data[i+2] << (2 * bit_shift) |
                     tx_data[i+1] << (1 * bit_shift) |
                     tx_data[i]) for i in range(0, len(tx_data), 4)]
            axis_image = AxiStreamImage(data, width//pixel_per_clock, height)
        else:
            dut._log.critical("Error in send(): {pixel_per_clock} PPC processing is not supported. Supported values are 1,2,4")
            raise ValueError

        # send stream image
        await axis_image.send(axis_source)
        await axis_source.wait() # wait until axi stream source is idle again i.e. all data has been send

        # NOTE: always add pixel-by-pixel image data regardless of pixel per clock
        axis_images.append(AxiStreamImage(tx_data, width, height))

    return axis_images


async def recv(dut, axis_sink, n_frames, height):
    pixel_per_clock = int(dut.G_PIXEL_PER_CLOCK.value)
    data_width = int(dut.G_DATA_WIDTH.value)
    n_color_components = int(dut.G_N_COLOR_COMPONENTS.value)
    # >1 PPC parameters
    bit_mask = 2**(data_width*n_color_components)-1
    bit_shift = data_width*n_color_components

    # receive images
    rx_axis_images = []
    for _ in range(n_frames):
        rx_frames = []
        for _ in range(height):
            # receive 1 frame i.e. line. compact=False ensures that tuser signal is kept as type <list>
            rx_frame = await axis_sink.recv(compact=False)
            ## await axis_sink.wait()

            result_tdata = []
            result_tuser = []

            # 1 PPC
            if pixel_per_clock == 1:
                # cast recv data to int (avoids list of 8-bit values being interpreted as byte array by AxiStreamFrame)
                result_tdata = [int(num) for num in rx_frame.tdata]
                result_tuser = [int(num) for num in rx_frame.tuser]
            # 2 PPC
            elif pixel_per_clock == 2:
                result_tdata = []
                for num in rx_frame.tdata:
                    result_tdata.extend([
                        num & bit_mask,
                        (num >> (1 * bit_shift)) & bit_mask,
                    ])
                result_tuser = [value for num in rx_frame.tuser for value in [num, 0]]
            # 4 PPC
            elif pixel_per_clock == 4:
                result_tdata = []
                for num in rx_frame.tdata:
                    result_tdata.extend([
                        num & bit_mask,
                        (num >> (1 * bit_shift)) & bit_mask,
                        (num >> (2 * bit_shift)) & bit_mask,
                        (num >> (3 * bit_shift))
                    ])
                result_tuser = [value for num in rx_frame.tuser for value in [num, 0, 0, 0]]
            else:
                dut._log.critical("Error in send(): {pixel_per_clock} PPC processing is not supported. Supported values are 1,2,4")
                raise ValueError

            # collect frame
            rx_frames.append(AxiStreamFrame(tdata=result_tdata, tuser=result_tuser))

        # NOTE: always add pixel-by-pixel image data regardless of pixel per clock
        rx_axis_images.append(AxiStreamImage.from_frames(rx_frames))

    # wait one more clock cycle before ending simulation (optional)
    await RisingEdge(dut.clk)

    return rx_axis_images


def coco(n_frames, tx_data, width, height):
    coco_images = []
    for _ in range(n_frames):
        coco_frames = []
        for line in range(height):
            coco_pixels = []
            for pixel in range(width):
                #### #### #### #### #### #### #### #### #### #### #### ####

                # n = random.choices([0, 1], weights=[1, 99], k=1)[0]
                # simulation co-processing. implements the same operation as HW code
                coco_pixel = tx_data[line*width+pixel] + 1

                #### #### #### #### #### #### #### #### #### #### #### ####
                coco_pixels.append(coco_pixel)
            tuser = [1 if line == 0 else 0] + [0] * (width - 1)
            coco_frames.append(AxiStreamFrame(tdata=coco_pixels, tuser=tuser))
        coco_images.append(AxiStreamImage.from_frames(coco_frames))
    return coco_images


def assert_tuser_signal(axis_rx_images):
    for rx_image in axis_rx_images:  # all images (n * width * height)
        for frame_idx, rx_frame in enumerate(rx_image): # all "frames" i.e. lines (width * height)
            for pixel_idx, rx_tuser in enumerate(rx_frame.tuser): # all pixel in a line
                # check tuser signal
                if frame_idx == 0 and pixel_idx == 0:
                    assert rx_tuser == 1, "tuser is not 1 for first pixel in first line"
                else:
                    assert rx_tuser == 0, f"tuser is not 0 for line: {frame_idx} pixel: {pixel_idx}"


def assert_tdata_signal(coco_images, axis_rx_images):
    for image_idx, (coco_image, rx_image) in enumerate(zip(coco_images, axis_rx_images)):  # all images (n * width * height)
        for frame_idx, (coco_frame, rx_frame) in enumerate(zip(coco_image, rx_image)): # all "frames" i.e. lines (width * height)
            for pixel_idx, (coco_data, rx_tdata) in enumerate(zip(coco_frame, rx_frame.tdata)): # all pixel in a line
                # check tdata signal
                assert rx_tdata == coco_data, f"data mismatch in image: {image_idx} line: {frame_idx} pixel: {pixel_idx}"


async def axi_stream(dut, n_frames, size, idle_inserter, backpressure_inserter):

    # SETUP
    axis_source, axis_sink = await setup_axis(dut, idle_inserter, backpressure_inserter)
    axilite_master = await setup_axilite(dut, None, None)
    await setup_sim(dut)

    # READ FILE
    tx_data, width, height, max_value = utility.read_pnm(f"{Path(__file__).resolve().parent}/images/RGBRandom_{size}_{int(dut.G_DATA_WIDTH.value)}bit.pnm")

    # SEND
    axis_tx_images = await send(dut, axis_source, n_frames, tx_data, width, height)

    # CO-PROCESSING
    coco_images = coco(n_frames, tx_data, width, height)

    # RECV
    axis_rx_images = await recv(dut, axis_sink, n_frames, height)

    # WRITE FILE
    if os.environ.get('WRITE_IMAGE_OUTPUT') == 'True':
        for idx, rx_image in enumerate(axis_rx_images):
            utility.write_pnm(rx_image.data(), width, height, max_value, f"{Path(__file__).resolve().parent}/images/output/output_{idx:04d}.pnm", format='P3')

    # ASSERT
    assert axis_source.empty(), "AxiStreamMaster (source) not empty"
    assert axis_sink.empty(), "AxiStreamSource (sink) not empty"
    assert_tuser_signal(axis_rx_images)
    assert_tdata_signal(coco_images, axis_rx_images)


async def axi_lite(dut, idle_inserter, backpressure_inserter):

    # SETUP
    axilite_master = await setup_axilite(dut, idle_inserter, backpressure_inserter)
    await setup_sim(dut)

    # WRITE
    write_value_register2 =0x01234567
    bytevalue = write_value_register2.to_bytes(4, byteorder='little')
    await axilite_master.write(address=0x08, data=bytevalue)
    write_value_register3 =0x89ABCDEF
    bytevalue = write_value_register3.to_bytes(4, byteorder='little')
    await axilite_master.write(address=0x0C, data=bytevalue)

    # wait for transactions to complete
    await axilite_master.wait()

    # READ
    registers = []
    for i in range(0, 0x0C+1, 0x04): # 0x00, 0x04, 0x08, 0x0C
        value = await axilite_master.read(address=0x00 + i, length=4)
        value_int = int.from_bytes(bytes(value), byteorder='little')
        registers.append(value_int)

    # wait for transactions to complete
    await axilite_master.wait()

    # PRINT
    for idx, reg in enumerate(registers):
        dut._log.debug(f"AxiLite register 0x{(idx*0x04):02X}: 0x{reg:08X}")

    # wait one more clock cycle before ending simulation (optional)
    await RisingEdge(dut.clk)

    # ASSERT
    # check read-only registers
    assert registers[0] == 0xDEAD
    assert registers[1] == 0xBEEF
    # check write registers were successfully written to
    assert registers[2] == write_value_register2
    assert registers[3] == write_value_register3


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
async def run_axi_lite(dut):
    await axi_lite(dut, None, None)

@cocotb.test()
async def run_axi_lite_random_tvalid(dut):
    await axi_lite(dut, pause_generator(), None)

@cocotb.test()
async def run_axi_lite_random_tready(dut):
    await axi_lite(dut, None, pause_generator())

@cocotb.test()
async def run_axi_lite_random_tvalid_random_tready(dut):
    await axi_lite(dut, pause_generator(), pause_generator())

@cocotb.test()
async def run_toplevel_generics_range(dut):
    G_DATA_WIDTH = int(dut.G_DATA_WIDTH.value)
    assert G_DATA_WIDTH in [8, 10, 12, 16]

    G_N_COLOR_COMPONENTS = int(dut.G_N_COLOR_COMPONENTS.value)
    assert G_N_COLOR_COMPONENTS in [3]

    G_PIXEL_PER_CLOCK = int(dut.G_PIXEL_PER_CLOCK.value)
    assert G_PIXEL_PER_CLOCK in [1, 2, 4]

@cocotb.test()
async def run_axi_lite_generics_sanity(dut):
    G_S_AXI_CTRL_NUMBER_OF_REGISTERS = dut.inst_axilite_ctrl.G_S_AXI_CTRL_NUMBER_OF_REGISTERS.value.integer

    G_S_AXI_CTRL_DATA_WIDTH = dut.inst_axilite_ctrl.G_S_AXI_CTRL_DATA_WIDTH.value.integer
    assert G_S_AXI_CTRL_DATA_WIDTH == 32

    G_S_AXI_CTRL_ADDR_WIDTH = dut.inst_axilite_ctrl.G_S_AXI_CTRL_ADDR_WIDTH.value.integer
    assert G_S_AXI_CTRL_ADDR_WIDTH == (math.ceil(math.log2(G_S_AXI_CTRL_NUMBER_OF_REGISTERS)) + 2)

    # NOTE: unfortunately "complex" generic types like std_logic_vector cannot be accessed
    # print(dut.inst_axilite_ctrl.G_S_AXI_CTRL_WRITE_REGISTER)

