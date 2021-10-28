from copy import copy

import pytest

from modmail.extensions.extension_manager import ExtensionConverter
from modmail.utils.extensions import EXTENSIONS as GLOBAL_EXTENSIONS
from modmail.utils.extensions import walk_extensions


# load EXTENSIONS
EXTENSIONS = copy(GLOBAL_EXTENSIONS)
EXTENSIONS.update(walk_extensions())


class TestExtensionConverter:
    """Test the extension converter converts extensions properly."""

    all_extensions = {x: y for x, y in walk_extensions()}

    @pytest.fixture(scope="class", name="converter")
    def converter(self) -> ExtensionConverter:
        """Fixture method for a ExtensionConverter object."""
        return ExtensionConverter()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("extension", [e.rsplit(".", 1)[-1] for e in all_extensions.keys()])
    async def test_conversion_success(self, extension: str, converter: ExtensionConverter) -> None:
        """Test all extensions in the list are properly converted."""
        converter.source_list = self.all_extensions
        converted = await converter.convert(None, extension)

        assert converted.endswith(extension)
