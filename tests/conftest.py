import pytest

import modmail.utils.time


def pytest_report_header(config) -> str:
    """Pytest headers."""
    return "package: modmail"


# patch the discord_time during initial test start
modmail.utils.time.monkeypatch_discord_time()
