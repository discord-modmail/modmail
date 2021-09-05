from __future__ import annotations

import io
import logging
import pathlib
import tempfile
import zipfile
from typing import TYPE_CHECKING

from modmail.addons.models import SourceTypeEnum
from modmail.errors import HTTPError

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from modmail.addons.models import AddonSource
    from modmail.log import ModmailLogger
logger: ModmailLogger = logging.getLogger(__name__)

TEMP_DIR = pathlib.Path(tempfile.gettempdir())


def unpack_zip(zip_file: zipfile.ZipFile, path: pathlib.Path = None) -> pathlib.Path:
    """
    Unpack a zip file and return its new path.

    If path is provided, the zip will be unpacked to that path.
    If path is not provided, a file in the platform's temp directory will be used.
    """
    if path is None:
        path = TEMP_DIR / "modmail-addons" / f"zip-{hash(zip_file)}"

    zip_file.extractall(path=path)
    return path


async def download_zip_from_source(source: AddonSource, session: ClientSession) -> zipfile.ZipFile:
    """
    Download a zip file from a source.

    It is currently required to provide an http session.
    """
    if source.source_type not in (SourceTypeEnum.REPO, SourceTypeEnum.ZIP):
        raise TypeError("Unsupported source detected.")

    async with session.get(f"https://{source.zip_url}") as resp:
        if resp.status != 200:
            raise HTTPError(resp)
        raw_bytes = await resp.read()

    zip_stream = io.BytesIO(raw_bytes)
    zip_stream.write(raw_bytes)

    return zipfile.ZipFile(zip_stream)


async def download_and_unpack_source(
    source: AddonSource, session: ClientSession, path: pathlib.Path = None
) -> pathlib.Path:
    """Downloads and unpacks source."""
    zip_file = await download_zip_from_source(source, session)
    return unpack_zip(zip_file, path)
