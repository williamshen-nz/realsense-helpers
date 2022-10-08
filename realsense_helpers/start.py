import pyrealsense2 as rs

from realsense_helpers.config import RealSenseSettings


def main(settings: RealSenseSettings):
    ctx = rs.context()
    if not ctx.devices:
        raise RuntimeError("No RealSense devices were found.")

    # Create pipeline for each device
    devices = ctx.devices
    pipelines = [rs.pipeline(ctx) for _ in devices]


if __name__ == "__main__":
    settings_ = RealSenseSettings()
    main(settings_)
