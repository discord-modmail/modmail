import os
import pathlib
import unittest.mock

import dotenv
import pytest


_ORIG_ENVIRON = None

_modmail_env_prefix = "MODMAIL_"


def pytest_report_header(config) -> str:
    """Pytest headers."""
    return "package: modmail"


@pytest.fixture(autouse=True, scope="package")
def patch_embeds():
    """Run the patch embed method. This is normally run by modmail.__main__, which is not run for testing."""
    import modmail.utils.embeds

    modmail.utils.embeds.patch_embed()


def _get_env():
    return pathlib.Path(__file__).parent / "test.env"


def _get_env_vars() -> dict:
    result = {}
    for key, value in os.environ.items():
        # not using upper() here is not a bug since the config system is case sensitive
        if key.startswith(_modmail_env_prefix):
            result[key] = value
    return result


def pytest_configure():
    """Load the test specific environment file, exit if it does not exist."""
    global _ORIG_ENVIRON
    env = _get_env()
    if not env.is_file():
        pytest.exit(f"Testing specific {env} does not exist. Cancelling test run.", 2)
    _ORIG_ENVIRON = _get_env_vars()
    for key in _ORIG_ENVIRON:
        del os.environ[key]

    dotenv.load_dotenv(_get_env(), override=True)


def pytest_unconfigure():
    """Reset os.environ to the original environment before the run."""
    global _ORIG_ENVIRON
    if _ORIG_ENVIRON is None:
        return

    for key in _get_env_vars():
        del os.environ[key]
    os.environ.update(**_ORIG_ENVIRON)
    _ORIG_ENVIRON = None
