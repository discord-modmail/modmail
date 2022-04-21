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


@pytest.fixture(scope="package")
def reroute_plugins():
    """Reroute the plugin directory."""
    import modmail.plugins
    from tests.modmail import plugins

    modmail.plugins.__file__ = plugins.__file__

    import modmail.addons.plugins

    modmail.addons.plugins.BASE_PLUGIN_PATH = pathlib.Path(plugins.__file__).parent.resolve()

    modmail.addons.plugins.LOCAL_PLUGIN_TOML = modmail.addons.plugins.BASE_PLUGIN_PATH / "test1.toml"
    yield


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
