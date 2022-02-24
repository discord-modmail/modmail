from __future__ import annotations

import logging
import urllib.parse
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Literal, NoReturn, Optional, Set, Union

from discord.ext import commands
from rapidfuzz import fuzz, process

from modmail.utils.extensions import ModuleDict


if TYPE_CHECKING:
    import pathlib
    import zipfile

    from modmail.log import ModmailLogger

logger: ModmailLogger = logging.getLogger(__name__)

PLUGINS = None

SCORE_CUTOFF = 69


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
    zip_archive_api_url_with_ref: str


class Github(GitHost):
    """Github's api."""

    headers = {"Accept": "application/vnd.github.v3+json"}
    base_api_url = "https://api.github.com"
    repo_api_url = f"{base_api_url}/repos/{{user}}/{{repo}}"
    zip_archive_api_url = f"{repo_api_url}/zipball"
    zip_archive_api_url_with_ref = f"{zip_archive_api_url}/{{ref}}"


class Gitlab(GitHost):
    """Gitlab's api."""

    base_api_url = "https://gitlab.com/api/v4"
    repo_api_url = f"{base_api_url}/projects/{{user}}%2F{{repo}}"
    zip_archive_api_url = f"{repo_api_url}/repository/archive.zip"
    zip_archive_api_url_with_ref = f"{zip_archive_api_url}?sha={{ref}}"


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

        cache_file: Optional[Union[zipfile.Path, pathlib.Path]]

    def __init__(self, zip_url: str, type: SourceTypeEnum):
        """Initialize the AddonSource."""
        self.zip_url = zip_url
        if self.zip_url is not None:
            parsed_url = urllib.parse.urlparse(self.zip_url)
            self.zip_url = urllib.parse.urlunparse(parsed_url)
            self.domain = parsed_url.netloc
            self.path = parsed_url.path
        else:
            self.domain = None
            self.path = None

        self.source_type = type

    @classmethod
    def from_repo(cls, user: str, repo: str, reflike: str = None, githost: Host = "github") -> AddonSource:
        """Create an AddonSource from a repo."""
        if githost == "github":
            Host = Github()  # noqa: N806
        elif githost == "gitlab":
            Host = Gitlab()  # noqa: N806
        else:
            raise TypeError(f"{githost} is not a valid host.")
        if reflike is not None:
            zip_url = Host.zip_archive_api_url_with_ref.format(user=user, repo=repo, ref=reflike)
        else:
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
        source = cls(url, SourceTypeEnum.ZIP)
        return source

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AddonSource zip_url={self.zip_url} source_type={self.source_type!r}>"


class Addon:
    """Base class of an addon which make the bot extendable."""

    if TYPE_CHECKING:
        name: str
        description: Optional[str]
        min_bot_version: str

    def __init__(self) -> NoReturn:
        raise NotImplementedError("Inheriting classes need to implement their own init")

    def __hash__(self):
        return hash(self.name)


class Plugin(Addon):
    """An addon which is a plugin."""

    if TYPE_CHECKING:
        folder_name: str
        folder_path: Optional[pathlib.Path]
        extra_kwargs: Dict[str, Any]
        installed_path: Optional[pathlib.Path]
        extension_files: List[pathlib.Path]
        modules: ModuleDict

    def __init__(
        self,
        folder: str,
        description: Optional[str] = None,
        *,
        dependencies: Optional[List[str]] = None,
        enabled: bool = True,
        folder_path: Optional[pathlib.Path] = None,
        local: bool = False,
        min_bot_version: Optional[str] = None,
        name: Optional[str] = None,
        **kw,
    ):
        self.folder_name = folder
        self.description = description
        self.name = self.folder_name if name is None else name
        self.folder_path = folder_path
        self.min_bot_version = min_bot_version
        self.local = local
        self.enabled = enabled

        self.dependencies = dependencies or []

        self.modules = {}

        # store any extra kwargs here
        # this is to ensure backwards compatiablilty with plugins that support older versions,
        # but want to use newer toml options
        self.extra_kwargs = kw

    def __str__(self):
        return self.name

    def __repr__(self):  # pragma: no cover
        return (
            f"<Plugin {self.name!r} description={self.description!r} "
            f"folder_name={self.folder_name!r} folder_path={self.folder_path!r}>"
        )

    def __hash__(self):
        return hash(self.folder_name)

    def __eq__(self, other: Any):
        return hash(self) == hash(other)

    @classmethod
    async def convert(cls, ctx: commands.Context, argument: str) -> Plugin:
        """Converts a plugin into a full plugin with a path and all other attributes."""
        # have to do this here to prevent a recursive import
        global PLUGINS
        if PLUGINS is None:
            logger.debug("Lazy import of global PLUGINS from modmail.addons.plugins")
            from modmail.addons.plugins import PLUGINS

        loaded_plugs: Set[Plugin] = PLUGINS

        # its possible to have a plugin with the same name as a folder of a plugin
        # folder names are the priority
        secondary_names = {}
        for plug in loaded_plugs:
            if argument == plug.name:
                return plug
            secondary_names[plug.folder_name] = plug

        if argument in secondary_names:
            return secondary_names[argument]

        # Determine close plugins
        # Using a dict to prevent duplicates
        arg_mapping: Dict[str, Plugin] = {}
        for plug in loaded_plugs:
            for name in plug.name, plug.folder_name:
                arg_mapping[name] = plug

        result = process.extract(
            argument,
            arg_mapping.keys(),
            scorer=fuzz.ratio,
            score_cutoff=SCORE_CUTOFF,
        )
        logger.debug(f"{result = }")

        if not len(result):
            raise commands.BadArgument(f"`{argument}` is not in list of installed plugins.")

        all_fully_matched_plugins: Set[Plugin] = set()
        all_partially_matched_plugins: Dict[Plugin, float] = dict()
        for res in result:
            all_partially_matched_plugins[arg_mapping[res[0]]] = res[1]

            if res[1] == 100:
                all_fully_matched_plugins.add(arg_mapping[res[0]])

        if len(all_fully_matched_plugins) != 1:
            suggested = ""
            for plug, percent in all_partially_matched_plugins.items():
                suggested += f"`{plug.name}` ({round(percent)}%)\n"
            raise commands.BadArgument(
                f"`{argument}` is not in list of installed plugins."
                f"\n\n**Suggested plugins**:\n{suggested}"
                if len(suggested)
                else ""
            )

        return await cls.convert(ctx, all_fully_matched_plugins.pop().name)
