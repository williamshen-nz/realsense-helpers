from typing import NamedTuple, List


class RealSenseMetadata(NamedTuple):

    name: str
    serial_number: str

    # Width and height of the stream in pixels
    width: int
    height: int

    # Number of depth units per meter
    depth_scale: float

    # 3x3 intrinsic matrix as a list of lists
    intrimsic_matrix: List[List[float]]
