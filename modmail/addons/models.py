from __future__ import annotations

import re
from enum import Enum
from typing import TYPE_CHECKING, Literal, Optional, Union

if TYPE_CHECKING:
    import pathlib
    import zipfile


class SourceTypeEnum(Enum):
    """Which source an addon is from."""

    ZIP = 0
    REPO = 1
    LOCAL = 2


class GitHost:
    """Base class for git hosts."""

    headers = {}
    base_api_url: str
    repo_api_url: str
    zip_archive_api_url: str


class Github(GitHost):
    """Github's api."""

    headers = {"Accept": "application/vnd.github.v3+json"}
    base_api_url = "https://api.github.com"
    repo_api_url = f"{base_api_url}/repos/{{user}}/{{repo}}"
    zip_archive_api_url = f"{repo_api_url}/zipball"


class Gitlab(GitHost):
    """Gitlab's api."""

    base_api_url = "https://gitlab.com/api/v4"
    repo_api_url = f"{base_api_url}/projects/{{user}}%2F{{repo}}"
    zip_archive_api_url = f"{repo_api_url}/repository/archive.zip"


Host = Literal["github", "gitlab"]


class AddonSource:
    """
    Represents an AddonSource.

    These could be from github, gitlab, or hosted zip file.
    """

    if TYPE_CHECKING:
        repo: Optional[str]
        user: Optional[str]
        reflike: Optional[str]
        githost: Optional[Host]
        githost_api: Optional[GitHost]

        domain: Optional[str]
        path: Optional[str]

        addon_directory: Optional[str]
        cache_file: Optional[Union[zipfile.Path, pathlib.Path]]

    def __init__(self, zip_url: str, type: SourceTypeEnum) -> AddonSource:
        """Initialize the AddonSource."""
        self.zip_url = zip_url
        if self.zip_url is not None:
            match = re.match(r"^(?:https?:\/\/)?(?P<url>(?P<domain>.*\..+?)\/(?P<path>.*))$", self.zip_url)
            self.zip_url = match.group("url")
            self.domain = match.group("domain")
            self.path = match.group("path")
        else:
            self.domain = None
            self.path = None

        self.source_type = type

    @classmethod
    def from_repo(cls, user: str, repo: str, reflike: str = None, githost: Host = "github") -> AddonSource:
        """Create an AddonSource from a repo."""
        if githost == "github":
            Host = Github  # noqa: N806
        elif githost == "gitlab":
            Host = Gitlab  # noqa: N806
        else:
            raise TypeError(f"{githost} is not a valid host.")
        zip_url = Host.zip_archive_api_url.format(user=user, repo=repo)

        source = cls(zip_url, SourceTypeEnum.REPO)
        source.repo = repo
        source.user = user
        source.reflike = reflike
        source.githost = githost
        source.githost_api = Host
        return source

    @classmethod
    def from_zip(cls, url: str) -> AddonSource:
        """Create an AddonSource from a zip file."""
        match = re.match(r"^(?P<url>(?:https?:\/\/)?(?P<domain>.*\..+?)\/(?P<path>.*\.zip))$", url)
        source = cls(match.group("url"), SourceTypeEnum.ZIP)
        return source

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AddonSource zip_url={self.zip_url} source_type={self.source_type!r}>"


class Addon:
    """Base class of an addon which make the bot extendable."""

    name: str
    description: Optional[str]
    min_version: str

    def __init__(self):
        raise NotImplementedError("Inheriting classes need to implement their own init")


class Plugin(Addon):
    """An addon which is a plugin."""

    if TYPE_CHECKING:
        folder: Union[str, pathlib.Path, zipfile.Path]

    def __init__(self, name: str, **kw) -> Plugin:
        self.name = name
        self.description = kw.get("description", None)
        self.folder = kw.get("folder", None)
        self.min_version = kw.get("min_version", None)
        self.enabled = kw.get("enabled", True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Plugin {self.name!r} description={self.description!r} folder={self.folder!r}>"
