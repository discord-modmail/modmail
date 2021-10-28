import pytest


def pytest_report_header(config) -> str:
    """Pytest headers."""
    return "package: modmail"
