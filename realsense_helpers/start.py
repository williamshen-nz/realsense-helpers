"""
Modified from various sources including:
- Yen-Chen Lin's custom RealSense code
- https://github.com/anthonysimeonov/realsense_lcm
- https://github.com/IntelRealSense/librealsense/issues/8388#issuecomment-782395443
"""
import asyncio
import time
from typing import Collection

import aiofiles
import numpy as np
import pyrealsense2 as rs
from loguru import logger

from realsense_helpers.config import RealSenseSettings
from realsense_helpers.metadata import RealSenseMetadata

ctx = rs.context()
align_to = rs.stream.color
align = rs.align(align_to)


def refresh_context():
    """
    Refresh the singleton global context object.
    """
    global ctx
    ctx = rs.context()


def start_device(device: rs.device, settings: RealSenseSettings) -> rs.pipeline:
    """
    Start a device with the given settings and return a pipeline object.
    """
    device_name = device.get_info(rs.camera_info.name)
    serial_number = device.get_info(rs.camera_info.serial_number)
    pipeline = rs.pipeline(ctx)
    config = rs.config()

    # Enable device and streams
    config.enable_device(device.get_info(rs.camera_info.serial_number))
    for stream in settings.streams:
        config.enable_stream(*stream)

    # Start and return the pipeline
    pipeline.start(config)
    logger.debug(f"Started pipeline for {device_name}, Serial Number: {serial_number}")
    return pipeline


def get_metadata(device: rs.device, pipeline: rs.pipeline) -> RealSenseMetadata:
    """
    Get the metadata for the given device.
    """
    name = device.get_info(rs.camera_info.name)
    serial_number = device.get_info(rs.camera_info.serial_number)
    depth_scale = device.first_depth_sensor().get_depth_scale()

    # Get the intrinsics for the color stream (as we will align the depth to color)
    profile = pipeline.get_active_profile()
    assert align_to == rs.stream.color, "Only aligning to color is supported."
    intrinsics = profile.get_stream(align_to).as_video_stream_profile().get_intrinsics()
    intrinsic_matrix = [
        [intrinsics.fx, 0, intrinsics.ppx],
        [0, intrinsics.fy, intrinsics.ppy],
        [0, 0, 1],
    ]

    metadata = RealSenseMetadata(
        name=name,
        serial_number=serial_number,
        width=intrinsics.width,
        height=intrinsics.height,
        depth_scale=depth_scale,
        intrinsic_matrix=intrinsic_matrix,
        distortion_coefficients=intrinsics.coeffs,
    )
    logger.info(metadata)
    return metadata


def warmup(pipelines: Collection[rs.pipeline], frames: int = 30) -> None:
    """Warmup the devices by waiting for a few frames to be ready."""
    for pipeline in pipelines:
        for _ in range(frames):
            pipeline.wait_for_frames()
    logger.debug(f"Warmed up {len(pipelines)} pipelines for {frames} frames each.")


def hardware_reset(devices: Collection[rs.device], sleep_time: float = 3.0) -> None:
    """
    Hardware reset the given devices. The USB connection on the RealSense devices
    are unreliable, so try resetting the devices if you aren't getting any frames.
    """
    for device in devices:
        device.hardware_reset()
    # The hardware reset is asynchronous, so sleep for a bit
    time.sleep(sleep_time)
    logger.debug(f"Hardware reset {len(devices)} devices.")


async def capture_frames(
    pipeline: rs.pipeline,
    device_label: str,
    wait_timeout: int = 100,
    write_to_disk: bool = True,
):
    try:
        # Get frameset of color and depth
        frames = pipeline.wait_for_frames(wait_timeout)
    except RuntimeError:
        logger.critical(f"Couldn't get frame for {device_label} in {wait_timeout} ms.")
        return

    # Align the depth frame to color frame
    aligned_frames = align.process(frames)

    # Get aligned depth and color frames
    depth_frame = aligned_frames.get_depth_frame()
    color_frame = aligned_frames.get_color_frame()

    # Validate that both frames are valid
    if not depth_frame or not color_frame:
        logger.error(f"Could not get either color or depth frame for {device_label}")
        return

    # Convert to numpy arrays
    depth_image = np.asanyarray(depth_frame.get_data())
    color_image = np.asanyarray(color_frame.get_data())

    if write_to_disk:
        async with aiofiles.open(f"{device_label}_depth.npy", "wb") as f:
            await f.write(depth_image)
        async with aiofiles.open(f"{device_label}_color.npy", "wb") as f:
            await f.write(color_image)
        logger.debug(f"Saved {device_label} frames to disk.")


async def async_main(settings: RealSenseSettings):
    if not ctx.devices:
        raise RuntimeError("No RealSense devices were found.")

    # Create pipeline for each device
    devices = ctx.devices
    pipelines = [start_device(device, settings) for device in devices]

    # Get metadata and form labels for debug purposes
    metadata = [
        get_metadata(device, pipeline) for device, pipeline in zip(devices, pipelines)
    ]
    device_labels = [f"{meta.name} {meta.serial_number}" for meta in metadata]

    # TODO: auto exposure, white balance, etc. per camera settings
    rs.option.enable_auto_exposure = True

    # Warmup the devices
    warmup(pipelines)

    async_tasks = []

    for device_label, pipeline in zip(device_labels, pipelines):
        async_tasks.append(
            asyncio.create_task(
                capture_frames(pipeline, device_label, write_to_disk=False)
            )
        )
    await asyncio.gather(*async_tasks)


def main(settings: RealSenseSettings):
    return asyncio.run(async_main(settings))


if __name__ == "__main__":
    settings_ = RealSenseSettings()
    main(settings_)
