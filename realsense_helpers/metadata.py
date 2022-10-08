from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class RealSenseMetadata:
    name: str
    serial_number: str

    # Width and height of the stream in pixels
    width: int
    height: int

    # Number of depth units per meter
    depth_scale: float

    # 3x3 intrinsic matrix as a list of lists
    intrinsic_matrix: List[List[float]]

    # Distortion coefficients
    distortion_coefficients: List[float]
