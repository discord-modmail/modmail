import copy
import os
import sys
from collections import OrderedDict
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from _pytest.reports import TestReport
# Reference:
# https://docs.pytest.org/en/latest/writing_plugins.html#hookwrapper-executing-around-other-hooks
# https://docs.pytest.org/en/latest/writing_plugins.html#hook-function-ordering-call-example
# https://docs.pytest.org/en/stable/reference.html#pytest.hookspec.pytest_runtest_makereport
#
# Inspired by:
# https://github.com/pytest-dev/pytest/blob/master/src/_pytest/terminal.py


@pytest.hookimpl(trylast=True)
def pytest_runtest_logreport(report: "TestReport"):
    """Add annotations of test failures or xpassed to github actions."""
    # enable only in a workflow of GitHub Actions
    if os.environ.get("GITHUB_ACTIONS") is None:
        return

    if not report.when == "call":
        return

    skip = not report.failed
    message = "Test Failure."
    if hasattr(report, "wasxfail") and report.outcome == "passed":
        skip = False
        message = "Unexpected test success."

    if skip:
        return

    print(
        "\n::error file={location[0]},line={location[1]},title={location[2]}::{message}".format(
            location=report.location, message=message
        )
    )
