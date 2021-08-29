from __future__ import annotations

import logging
import os
import pathlib
import zipfile
from typing import TYPE_CHECKING, Union

from modmail.addons.models import SourceTypeEnum
from modmail.addons.plugins import BASE_PATH
from modmail.errors import HTTPError

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from modmail.addons.models import AddonSource
    from modmail.log import ModmailLogger
logger: ModmailLogger = logging.getLogger(__name__)


def move_zip_contents_up_a_level(zip_path: Union[str, pathlib.Path], folder: str = None) -> None:
    """
    Assuming that there is only one folder, move everything up a level.

    If a folder is provided, it will attempt to use that folder. This folder *must* be located in the root
    of the zip folder.
    """
    file = zipfile.ZipFile(zip_path)
    temp_archive = BASE_PATH / ".tmp.zip"  # temporary folder for moving
    temp_archive = zipfile.ZipFile(temp_archive, mode="w")
    for path in file.infolist():
        logger.trace(f"File name: {path.filename}")
        if (new_name := path.filename.split("/", 1)[-1]) == "":
            continue
        temp_archive.writestr(new_name, file.read(path))
    temp_archive.close()
    os.replace(temp_archive.filename, file.filename)


async def download_zip_from_source(source: AddonSource, session: ClientSession) -> zipfile.ZipFile:
    """
    Download a zip file from a source.

    It is currently required to provide an http session.
    """
    async with session.get(f"https://{source.zip_url}") as resp:
        if resp.status != 200:
            raise HTTPError(resp)
        raw_bytes = await resp.read()
    if source.source_type is SourceTypeEnum.REPO:
        file_name = f"{source.githost}/{source.user}/{source.repo}"
    elif source.source_type is SourceTypeEnum.ZIP:
        file_name = source.path.rstrip(".zip")
    else:
        raise TypeError("Unsupported source detected.")

    zipfile_path = BASE_PATH / ".cache" / f"{file_name}.zip"

    source.addon_directory = file_name
    source.cache_file = zipfile_path

    if not zipfile_path.exists():
        zipfile_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        # overwriting an existing file
        logger.info("Zip file already exists, overwriting it.")

    with zipfile_path.open("wb") as f:
        f.write(raw_bytes)

    return zipfile.ZipFile(zipfile_path)
