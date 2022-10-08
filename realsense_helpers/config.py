from dataclasses import dataclass
from typing import List, Tuple

import pyrealsense2 as rs


@dataclass(frozen=True)
class RealSenseSettings:
    """
    Settings for the RealSense helpers.

    We use the same settings for each camera, and assume that the
    depth and color resolutions are the same.

    We call these settings, and not configurations as the latter is
    specifically used in the RealSense SDK so we don't want to confuse
    the two.
    """

    width: int = 1280
    height: int = 720
    fps: int = 30

    # TODO: these parameters are not yet supported (and don't really need
    #   to be supported any time soon)
    enable_depth: bool = True
    enable_color: bool = True
    align_depth_to_color: bool = True

    def __post_init__(self):
        if not (self.enable_depth and self.enable_color):
            raise NotImplementedError(
                f"Only streaming both depth and color is supported at the moment."
            )

        if not self.align_depth_to_color:
            raise NotImplementedError(
                f"Only aligning depth to color is supported at the moment."
            )

        # Sanity check that the width, height, fps are positive integers
        for attr in ["width", "height", "fps"]:
            if not isinstance(getattr(self, attr), int):
                raise TypeError(f"{attr} must be an integer.")
            if getattr(self, attr) < 0:
                raise ValueError(f"{attr} must be a positive integer.")

    @property
    def streams(self) -> List[Tuple[rs.stream, int, int, rs.format, int]]:
        """
        Return a tuple of the streams that are enabled in this settings object.

        Returns
        -------
        Tuple[rs.stream, int, int, rs.format, int]
            The stream type, width, height, data type, and fps.
        """
        if not (self.enable_depth and self.enable_color):
            raise NotImplementedError(
                f"Only streaming both depth and color is supported at the moment."
            )

        streams = [
            (rs.stream.depth, self.width, self.height, rs.format.z16, self.fps),
            (rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps),
        ]
        return streams
