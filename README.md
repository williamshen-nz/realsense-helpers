# realsense_helpers

[![PyPI - Version](https://img.shields.io/pypi/v/realsense-helpers.svg)](https://pypi.org/project/realsense-helpers)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/realsense-helpers.svg)](https://pypi.org/project/realsense-helpers)
[![PyPI - License](https://img.shields.io/pypi/l/realsense-helpers.svg)](https://pypi.org/project/realsense-helpers)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/realsense-helpers.svg)](https://pypistats.org/packages/realsense-helpers)

Helpers for using Intel RealSense Cameras in Python. Wraps around `pyrealsense2`.

-----

**Table of Contents**

- [Installation](#installation)
- [Features](#features)
- [License](#license)

## Installation
```console
pip install realsense-helpers
```

**Note:** if you're on a Mac, you will need to install `pyrealsense2-macosx`

## Features
These are proposed features we are planning to build:

- Streaming multiple RealSense cameras
  - With multiprocessing and threading if required
- Saving to disk, PNG blobs, etc. 
- Point Clouds


**Assumptions:**
1. We are streaming both color and depth images for each camera.

## License

`realsense-helpers` is distributed under the terms of the [MIT license](LICENSE).
