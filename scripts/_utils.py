"""Utility functions and variables which are useful for all scripts."""
import difflib
import importlib.util
import os
import pathlib
import typing


MODMAIL_DIR = pathlib.Path(importlib.util.find_spec("modmail").origin).parent
PROJECT_DIR = MODMAIL_DIR.parent
try:
    import pygments
except ModuleNotFoundError:
    pygments = None
else:
    from pygments.formatters import Terminal256Formatter
    from pygments.lexers.diff import DiffLexer


class CheckFileEdit:
    """Check if a file is edited within the body of this class."""

    def __init__(self, *files: os.PathLike):
        self.files: typing.List[pathlib.Path] = []
        for f in files:
            self.files.append(pathlib.Path(f))
        self.return_value: typing.Optional[int] = None
        self.edited_files: typing.Dict[pathlib.Path] = {}

    def __enter__(self):
        self.file_contents = {}
        for file in self.files:
            try:
                with open(file, "r") as f:
                    self.file_contents[file] = f.readlines()
            except FileNotFoundError:
                self.file_contents[file] = None
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):  # noqa: ANN001
        for file in self.files:
            with open(file, "r") as f:
                original_contents = self.file_contents[file]
                new_contents = f.readlines()
                if original_contents != new_contents:
                    # construct a diff
                    diff = difflib.unified_diff(
                        original_contents, new_contents, fromfile="before", tofile="after"
                    )
                    try:
                        diff = "".join(diff)
                    except TypeError:
                        diff = None
                    else:
                        if pygments is not None:
                            diff = pygments.highlight(diff, DiffLexer(), Terminal256Formatter())
                    self.edited_files[file] = diff

    def write(self, path: str, contents: typing.Union[str, bytes], *, force: bool = False, **kwargs) -> bool:
        """
        Write to the provided path with contents. Must be within the context manager.

        Returns False if contents are not edited, True if they are.
        If force is True, will modify the files even if the contents match.

        Any extras kwargs are passed to open()
        """
        path = pathlib.Path(path)
        if path not in self.files:
            raise AssertionError(f"{path} must have been passed to __init__")

        if not force:
            try:
                with open(path, "r") as f:
                    if contents == f.read():
                        return False
            except FileNotFoundError:
                pass
        if isinstance(contents, str):
            contents = contents.encode()

        with open(path, "wb") as f:
            f.write(contents)

        return True
