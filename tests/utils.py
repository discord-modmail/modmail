import glob
import pathlib
import sys
from sys import exc_info


def get_frame_fallback(n):
    """
    Fallback for sys._getframe, which is only implemented on cpython.

    (Not that any other interpreters are officially supported, however!)
    """
    try:
        raise Exception
    except Exception:
        frame = exc_info()[2].tb_frame.f_back
        for _ in range(n):
            frame = frame.f_back
        return frame


if hasattr(sys, "_getframe"):
    get_frame = sys._getframe
else:
    get_frame = get_frame_fallback


def get_test_dir():
    """Return a pathlib.Path of the testing directory."""
    return pathlib.Path(__file__).parent


def get_resources(module: str = None, *, _depth=1):
    """Return the resources folder for the caller's corresponding module."""
    resources = get_test_dir() / "resources"
    if module is not None:
        return resources / module
    else:
        frame = get_frame(_depth)
        return resources / frame.f_globals["__package__"].split(".", 2)[1]


def get_resources_by_glob(*glob_paths: str):
    """
    Provided globs, return the matching resource files.

    Will search the module's corresponding resource folder automatically.
    """
    result = []
    resources = str(get_resources(_depth=2))
    for pattern in glob_paths:
        result.extend(glob.glob(resources + "/" + pattern))
    return result
