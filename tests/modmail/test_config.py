import inspect
import os
import pathlib
import textwrap
import typing

import atoml
import attr
import desert
import discord
import discord.ext.commands.converter
import dotenv
import marshmallow.utils
import pytest

from modmail import config


def test_config_is_cached():
    """Test configuration is cached, helping keep only one version of the configuration in existance."""
    for _ in range(2):
        assert config.config() == config._CACHED_CONFIG


def test_default_config_is_cached():
    """Test default configuration is cached, helping keep only one version of the config in existance."""
    for _ in range(2):
        assert config.default() == config._CACHED_DEFAULT


class TestConfigLoaders:
    """Test configuration loaders properly read and decode their files."""

    def test_load_env(self, tmp_path: pathlib.Path):
        """
        Ensure an environment variable properly gets loaded.

        This writes a custom .env file and loads them with dotenv.
        """
        token = "NjQzOTQ1MjY0ODY4MDk4MDQ5.342b.4inDLBILY69LOLfyi6jk420dpyjoEVsCoModM"  # noqa: S105
        prefix = "oop"
        dev_mode = True
        env = textwrap.dedent(
            f"""
            MODMAIL_BOT_TOKEN="{token}"
            MODMAIL_BOT_PREFIX="{prefix}"
            MODMAIL_DEV_MODE_DEVELOP={dev_mode}
            """
        )
        test_env = tmp_path / ".env"
        with open(test_env, "w") as f:
            f.write(env + "\n")

        # we have to run this here since we may have the environment vars in our local env
        # but we want to ensure that they are of the above env for the test
        dotenv.load_dotenv(test_env, override=True)
        cfg_dict = config.load_env(test_env)

        assert token == cfg_dict["bot"]["token"]
        assert prefix == cfg_dict["bot"]["prefix"]
        assert dev_mode == bool(cfg_dict["dev"]["mode"]["develop"])

    def test_load_toml(self, tmp_path: pathlib.Path):
        """
        Ensure a toml file is loaded is properly loaded.

        This writes a temporary file to the tempfolder and then parses it, deleting it when done.
        """
        # toml is a little bit different, so we have to convert our bools to strings
        # and then make them lowercase
        prefix = "toml_ftw"
        log_level = 40
        develop = True
        plugin_dev = True
        toml = textwrap.dedent(
            f"""
            [bot]
            prefix = "{prefix}"

            [dev]
            log_level = {log_level}

            [dev.mode]
            develop = {str(develop).lower()}
            plugin_dev = {str(plugin_dev).lower()}
            """
        )
        test_toml = tmp_path / "test.toml"
        with open(test_toml, "w") as f:
            f.write(toml + "\n")

        cfg_dict = config.load_toml(test_toml)

        assert prefix == cfg_dict["bot"]["prefix"]
        assert log_level == cfg_dict["dev"]["log_level"]
        assert develop == bool(cfg_dict["dev"]["mode"]["develop"])
        assert plugin_dev == bool(cfg_dict["dev"]["mode"]["plugin_dev"])

    def test_load_yaml(self, tmp_path: pathlib.Path):
        """
        Ensure a yaml file is loaded is properly loaded.

        This writes a temporary file to the tempfolder and then parses it, deleting it when done.
        """
        # this test requires the yaml library to be installed.
        _ = pytest.importorskip("yaml", reason="Yaml is not installed, unable to test yaml loading.")
        prefix = "toml_ftw"
        log_level = 40
        develop = True
        plugin_dev = True
        yaml = textwrap.dedent(
            f"""
            bot:
                prefix: '{prefix}'
            dev:
                log_level: {log_level}
                mode:
                    develop: {str(develop).lower()}
                    plugin_dev: {str(plugin_dev).lower()}

            """
        )
        test_yaml = tmp_path / "test.yaml"
        with open(test_yaml, "w") as f:
            f.write(yaml + "\n")

        cfg_dict = config.load_yaml(test_yaml)

        assert prefix == cfg_dict["bot"]["prefix"]
        assert log_level == cfg_dict["dev"]["log_level"]
        assert develop == bool(cfg_dict["dev"]["mode"]["develop"])
        assert plugin_dev == bool(cfg_dict["dev"]["mode"]["plugin_dev"])


def test_colour_conversion():
    """
    Test the discord.py converter takes all supported colours.

    Regression test.
    """
    ...


def test_metadata_valid():
    """
    Checks that the metadata for every field is valid.

    This is more of a sanity check than anything.
    """
    ...
