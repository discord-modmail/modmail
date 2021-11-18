from __future__ import annotations

import unittest.mock
from copy import copy

import pytest

from modmail.addons.models import Plugin
from modmail.addons.plugins import PLUGINS as GLOBAL_PLUGINS
from modmail.addons.plugins import find_plugins, parse_plugin_toml_from_string
from tests import mocks


pytestmark = pytest.mark.usefixtures("reroute_plugins")


VALID_PLUGIN_TOML = """
[[plugins]]
name = "Planet"
folder = "planet"
description = "Planet. Tells you which planet you are probably on."
min_bot_version = "v0.2.0"
"""


@pytest.mark.parametrize(
    "toml, name, folder, description, min_bot_version",
    [
        (
            VALID_PLUGIN_TOML,
            "Planet",
            "planet",
            "Planet. Tells you which planet you are probably on.",
            "v0.2.0",
        )
    ],
)
def test_parse_plugin_toml_from_string(
    toml: str, name: str, folder: str, description: str, min_bot_version: str
) -> None:
    """Make sure that a plugin toml file is correctly parsed."""
    plugs = parse_plugin_toml_from_string(toml)
    plug = plugs[0]
    print(plug.__repr__())
    assert isinstance(plug, Plugin)
    assert plug.name == name
    assert plug.folder_name == folder
    assert plug.description == description
    assert plug.min_bot_version == min_bot_version


class TestPluginConversion:
    """Test the extension converter converts extensions properly."""

    @classmethod
    def setup_class(cls):
        """Set the class plugins var to the scanned plugins."""
        cls.plugins = set(find_plugins())

    @pytest.mark.asyncio
    async def test_conversion_success(self) -> None:
        """Test all plugins in the list are properly converted."""
        with unittest.mock.patch("modmail.addons.plugins.PLUGINS", self.plugins):

            for plugin in self.plugins:
                print(f"Current plugin: {plugin}")
                converted = await Plugin.convert(mocks.MockContext(), plugin)

                assert plugin.name == converted.name
