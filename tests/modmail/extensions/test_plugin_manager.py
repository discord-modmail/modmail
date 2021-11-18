import unittest.mock
from copy import copy

import pytest

from modmail.addons.plugins import PLUGINS as GLOBAL_PLUGINS
from modmail.addons.plugins import find_plugins
from modmail.extensions.plugin_manager import PluginConverter


# load EXTENSIONS
PLUGINS = copy(GLOBAL_PLUGINS)
PLUGINS.update(find_plugins())


class TestPluginConverter:
    """Test the extension converter converts extensions properly."""

    @pytest.fixture(scope="class", name="converter")
    def converter(self) -> PluginConverter:
        """Fixture method for a PluginConverter object."""
        return PluginConverter()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("plugin", [e.name for e in PLUGINS])
    async def test_conversion_success(self, plugin: str, converter: PluginConverter) -> None:
        """Test all plugins in the list are properly converted."""
        with unittest.mock.patch("modmail.extensions.plugin_manager.PLUGINS", PLUGINS):
            converted = await converter.convert(None, plugin)

        assert plugin == converted.name
