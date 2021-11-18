import os
import pathlib
import unittest.mock

import dotenv
import pytest


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
    """Check that the test specific env file exists, and cancel the run if it does not exist."""
    env = _get_env()
    if not env.is_file():
        pytest.exit(f"Testing specific {env} does not exist. Cancelling test run.", 2)


@pytest.fixture(autouse=True, scope="package")
def standardize_environment():
    """Clear environment variables except for the test.env file."""
    env = _get_env()
    with unittest.mock.patch.dict(os.environ, clear=True):
        dotenv.load_dotenv(env)
        yield
