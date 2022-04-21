import os
import pathlib
import unittest.mock

import dotenv
import pytest


_ORIG_ENVIRON = None


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


def pytest_configure():
    """Load the test specific environment file, exit if it does not exist."""
    env = _get_env()
    if not env.is_file():
        pytest.exit(f"Testing specific {env} does not exist. Cancelling test run.", 2)
    os.environ.clear()
    dotenv.load_dotenv(_get_env(), override=True)


def pytest_unconfigure():
    """Reset os.environ to the original environment before the run."""
    if _ORIG_ENVIRON is not None:
        os.environ.clear()
        os.environ.update(**_ORIG_ENVIRON)
