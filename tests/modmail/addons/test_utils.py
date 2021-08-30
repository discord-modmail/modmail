from __future__ import annotations

import zipfile

import pytest
from aiohttp import ClientSession

from modmail.addons.models import AddonSource, SourceTypeEnum
from modmail.addons.utils import download_zip_from_source

# https://github.com/discord-modmail/modmail/archive/main.zip


@pytest.fixture()
@pytest.mark.asyncio
async def session() -> ClientSession:
    """Fixture function for a aiohttp.ClientSession."""
    return ClientSession()


@pytest.mark.parametrize(
    "source", [AddonSource.from_zip("https://github.com/discord-modmail/modmail/archive/main.zip")]
)
@pytest.mark.asyncio
async def test_download_zip_from_source(source: AddonSource, session: ClientSession):
    """Test that a zip can be successfully downloaded and everything is safe inside."""
    file = await download_zip_from_source(source, session)
    assert isinstance(file, zipfile.ZipFile)
    assert file.testzip() is None
