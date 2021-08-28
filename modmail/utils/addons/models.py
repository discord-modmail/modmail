from __future__ import annotations

import re
from enum import Enum
from typing import TYPE_CHECKING, Literal, Optional


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
        githost_api = Optional[GitHost]

    def __init__(self, zip_url: str, type: SourceTypeEnum) -> AddonSource:
        """Initialize the AddonSource."""
        self.zip_url = zip_url
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
        match = re.match(r"^(?:https?:\/\/)?(?P<url>(?P<domain>.*\..+?)\/(?P<path>.*\.zip))", url)
        source = cls(match.group("url"), SourceTypeEnum.ZIP)
        return source

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AddonSource zip_url={self.zip_url} source_type={self.source_type!r}>"


class Addon:
    """Base class of an addon which make the bot extendable."""

    name: str
    description: Optional[str]
    source: AddonSource
    min_version: str

    def __init__(self):
        raise NotImplementedError("Inheriting classes need to implement their own init")


class Plugin(Addon):
    """An addon which is a plugin."""

    def __init__(self, name: str, source: AddonSource, **kw) -> Plugin:
        self.name = name
        self.source = source
        self.description = kw.get("description", None)
        self.min_version = kw.get("min_version", None)
        self.enabled = kw.get("enabled", True)

    @classmethod
    def from_repo(
        cls, addon: str, user: str, repo: str, reflike: str = None, githost: Optional[Host] = "github"
    ) -> Plugin:
        """Create a Plugin from a repository regex match."""
        source = AddonSource.from_repo(user, repo, reflike, githost)
        return cls(addon, source)

    @classmethod
    def from_zip(cls, addon: str, url: str) -> Plugin:
        """Create a Plugin from a zip regex match."""
        source = AddonSource.from_zip(url)
        return cls(addon, source)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Plugin {self.name!r} {self.source!r}>"
