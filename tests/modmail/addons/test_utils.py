from __future__ import annotations

import glob
import io
import pathlib
import zipfile

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses

import tests
import tests.utils
from modmail.addons.models import AddonSource, SourceTypeEnum
from modmail.addons.utils import download_zip_from_source


@pytest.mark.asyncio
@pytest.mark.parametrize("plugin_repo_paths", tests.utils.get_resources_by_regex("modmail-plugins-*"))
@pytest.mark.parametrize(
    "zip_url",
    [
        "https://localhost/some/zip/file/path_and_archive/file.zip",
        "https://github.com/discord-modmail/modmail/tree/main/this-won-t_request.zip",
    ],
)
async def test_download_zip_from_source(
    zip_url: str,
    aioresponse: aioresponses,
    http_session: ClientSession,
    plugin_repo_paths,
):
    """Test that a zip can be successfully downloaded and everything is safe inside."""
    with io.BytesIO() as zip_stream:
        with zipfile.ZipFile(zip_stream, mode="w") as zip_file:
            for path in glob.iglob(f"{plugin_repo_paths!s}/**", recursive=True):
                zip_file.write(path, pathlib.Path(path).relative_to(plugin_repo_paths))
        zip_bytes = zip_stream.getvalue()

    aioresponse.get(zip_url, status=200, body=zip_bytes)

    source = AddonSource.from_zip(zip_url)
    file = await download_zip_from_source(source, http_session)

    assert isinstance(file, zipfile.ZipFile)
    assert file.testzip() is None
