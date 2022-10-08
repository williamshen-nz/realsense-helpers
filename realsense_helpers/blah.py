"""
Wrapper around pyrealsense2. Based on:
https://github.com/IntelRealSense/librealsense/issues/8388#issuecomment-782395443
"""
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import pyrealsense2 as rs

__all__ = ["Device", "WindowEvent", "find_devices", "start_pipelines", "stop_pipelines"]

# Note: change these to fit your use case. Assuming USB 3.2 connection.
_NAME_TO_STREAM_CONFIGURATIONS: Dict[str, List[Tuple]] = {
    # Mapping of camera name to a list of streams to enable
    # in the cfg.enable_stream format
    # "Intel RealSense D435": [
    #     (rs.stream.depth, 1280, 720, rs.format.z16, 30),
    #     (rs.stream.color, 1920, 1080, rs.format.bgr8, 30),
    # ],
    # Disabling depth camera as we don't need it right now
    "Intel RealSense L515": [
        # (rs.stream.depth, 1024, 768, rs.format.z16, 30),
        (rs.stream.color, 1920, 1080, rs.format.bgr8, 30),
    ],
}

align_to = rs.stream.color
align = rs.align(align_to)
ctx = rs.context()


class WindowEvent:
    EXIT = "exit"
    SAVE = "save"
    NONE = "none"
    ROBOT = "robot"


@dataclass
class Device:
    name: str
    serial_number: str
    # RealSense pipeline for this device
    pipeline: Optional[rs.pipeline] = None
    counter = 0

    @classmethod
    def from_rs_device(cls, dev: rs.device) -> "Device":
        name = dev.get_info(rs.camera_info.name)
        serial_number = dev.get_info(rs.camera_info.serial_number)
        return cls(name, serial_number)

    @property
    def stream_configurations(self) -> List[Tuple]:
        if self.name not in _NAME_TO_STREAM_CONFIGURATIONS:
            raise RuntimeError(f"Configuration not specified for {self.name}")

        return _NAME_TO_STREAM_CONFIGURATIONS[self.name]

    def start_pipeline(self) -> None:
        """Start RealSense pipeline"""
        if self.pipeline is not None:
            print(f"Pipeline already started for {self}")
            return

        # Setup pipeline and configuration
        pipeline = rs.pipeline(ctx)
        cfg = rs.config()
        cfg.enable_device(self.serial_number)

        for stream_configuration in self.stream_configurations:
            cfg.enable_stream(*stream_configuration)

        try:
            profile = pipeline.start(cfg)
        except RuntimeError as e:
            message = str(e)
            if message == "Couldn't resolve requests":
                # Something wrong with stream configurations probably
                raise RuntimeError(
                    f"{message} for {self}. Check stream configuration and USB connection."
                )
            else:
                raise e

        # Warmup camera
        for _ in range(30):
            pipeline.wait_for_frames()
        print("Camera warmed up!")

        # Set profile
        depth_sensor, color_sensor, *_ = profile.get_device().query_sensors()
        print("Retrieved sensors")

        color_sensor.set_option(rs.option.enable_auto_exposure, False)
        color_sensor.set_option(rs.option.exposure, 800)
        color_sensor.set_option(rs.option.gain, 0)

        # Disable backlight compensation
        # color_sensor.set_option(rs.option.backlight_compensation, 0)

        color_sensor.set_option(rs.option.enable_auto_white_balance, False)
        color_sensor.set_option(rs.option.white_balance, 4000)
        print("Disabled auto exposure and white balance for color sensor")
        self.color_sensor = color_sensor

        # Set the pipeline on the device
        self.pipeline = pipeline
        print(f"Started pipeline for {self}")

    def stop_pipeline(self) -> None:
        """Stop RealSense pipeline"""
        if not self.pipeline:
            print(f"Warning! Device {self} does not have a pipeline initialized")
        else:
            self.pipeline.stop()
            print(f"Stopped pipeline for {self}")

    def capture_images(self) -> Tuple[np.ndarray, np.ndarray]:
        """Capture color and depth images"""
        if self.pipeline is None:
            raise RuntimeError(f"Pipeline for {self} not started!")

        color_sensor = self.color_sensor
        color_sensor.set_option(rs.option.enable_auto_exposure, False)
        color_sensor.set_option(rs.option.exposure, 800)
        color_sensor.set_option(rs.option.gain, 0)
        # color_sensor.set_option(rs.option.backlight_compensation, 1)

        color_sensor.set_option(rs.option.enable_auto_white_balance, False)
        color_sensor.set_option(rs.option.white_balance, 4000)
        # print("Disabled auto exposure and white balance for color sensor")

        # Get frames and align
        frames = self.pipeline.wait_for_frames()
        aligned_frames = align.process(frames)

        # Get color and depth frame
        # depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()

        # if not depth_frame or not color_frame:
        #     print("Warning! Could not capture both color and depth frame.")
        #     return

        # Convert to numpy arrays
        # depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        return color_image, None

    def capture_color_image(self) -> np.ndarray:
        return self.capture_images()[0]

    def capture_depth_image(self) -> np.ndarray:
        return self.capture_images()[1]

    def visualize(
        self,
        save_dir: str = "",
        save_image: bool = False,
        flip_180: bool = True,
    ) -> WindowEvent:
        """
        Visualize color and depth images in a cv2 window.
        Terminates when 'esc' or 'q' key is pressed.

        Saves an image when the 's' key is pressed or if the 'save_image'
        flag is specified.

        Images are saved to the specified save_dir, which we
        assume to already exist.

        Returns a WindowEvent indicating status of cv2.
        """
        color_image, depth_image = self.capture_images()

        # Form heatmap for depth and stack with color image
        # depth_colormap = cv2.applyColorMap(
        #     cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET
        # )
        images = color_image
        # images = np.hstack((color_image, depth_colormap))

        window_name = str(self)
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        if flip_180:
            images = np.rot90(np.rot90(images))
        cv2.imshow(window_name, images)
        # cv2.resizeWindow(window_name, 1280, 720)
        key = cv2.waitKey(1)

        # Exit on 'esc' or 'q'
        if key & 0xFF == ord("q") or key == 27:
            cv2.destroyWindow(window_name)
            return WindowEvent.EXIT

        # Save images if 's' key is pressed
        if key == 115 or save_image:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            # depth_fname = os.path.join(
            #     save_dir, f"{timestamp}-{self.serial_number}-depth.png"
            # )
            color_path = os.path.join(save_dir, f"color-{self.counter}.png")
            # cv2.imwrite(depth_fname, depth_image)
            cv2.imwrite(color_path, images)
            # print(f"Saved depth image for {self} to {depth_fname}")
            print(f"Saved color image to {self} to {color_path}")
            self.counter += 1
            return WindowEvent.SAVE

        if key == 103:
            return WindowEvent.ROBOT

        return WindowEvent.NONE

    def __str__(self) -> str:
        return f"{self.name} ({self.serial_number})"

    def __repr__(self) -> str:
        return str(self)


def find_devices(device_filter: str = "") -> List[Device]:
    """
    Get devices as detected by RealSense and filter devices that only
    contain the provided device_filter string in their name.

    e.g. to filter for D435 only you can call `find_devices("D435")`
    """
    devices = [Device.from_rs_device(dev) for dev in ctx.devices]

    # Filter devices
    if device_filter:
        devices = [d for d in devices if device_filter in d.name.lower()]
        print(f"Found devices (filter={device_filter}): {devices}")
    else:
        print(f"Found devices: {devices}")

    if not devices:
        raise RuntimeError("No devices connected!")
    return devices


def start_pipelines(devices: List[Device]) -> None:
    """Enable each device by starting a stream"""
    for device in devices:
        device.start_pipeline()


def stop_pipelines(devices: List[Device]) -> None:
    """Stop all the pipelines"""
    for device in devices:
        device.stop_pipeline()


def hardware_reset_connected_devices() -> None:
    ctx = rs.context()
    devices = ctx.query_devices()
    for dev in devices:
        dev.hardware_reset()


def visualize_devices(devices: List[Device], save_dir: str = "") -> None:
    """
    Visualizes all the devices in a cv2 window. Press 'q' or 'esc' on any of
    the windows to exit the infinite loop.

    Press the 's' key in a specific window to save the color and depth image
    to disk.

    You can use a similar loop interface in other places where you need
    a live camera feed (e.g. collecting demonstrations).
    """
    print("Beginning visualization loop. Press 'q' or 'esc' to exit.")
    while True:
        exit = False
        save = False

        for device in devices:
            window_event = device.visualize(save_dir, save_image=save)
            if window_event == WindowEvent.SAVE:
                # We use this to propagate a save command across all windows
                save = True

            # Exit all windows
            if window_event == WindowEvent.EXIT:
                exit = True
                break

        if exit:
            print("Exit key pressed.")
            cv2.destroyAllWindows()
            break


if __name__ == "__main__":
    os.makedirs("realsense-demo", exist_ok=True)
    hardware_reset_connected_devices()

    # Detect devices, start pipelines, visualize, and stop pipelines
    devices = find_devices("l515")
    start_pipelines(devices)

    try:
        visualize_devices(devices)
    finally:
        stop_pipelines(devices)
