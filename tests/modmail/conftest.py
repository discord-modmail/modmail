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


@pytest.fixture(autouse=True, scope="package")
def standardize_config():
    """Set the configuration paths to this directory."""
    import modmail.config

    _config_directory = modmail.config.CONFIG_DIRECTORY
    _user_config_files = modmail.config.USER_CONFIG_FILES
    try:
        modmail.config.CONFIG_DIRECTORY = pathlib.Path(__file__).parent
        modmail.config.USER_CONFIG_FILES = [
            modmail.config.CONFIG_DIRECTORY / (modmail.config.USER_CONFIG_FILE_NAME + ".yaml"),
            modmail.config.CONFIG_DIRECTORY / (modmail.config.USER_CONFIG_FILE_NAME + ".toml"),
        ]
        yield
    finally:

        modmail.config.CONFIG_DIRECTORY = _config_directory
        modmail.config.USER_CONFIG_FILES = _user_config_files
