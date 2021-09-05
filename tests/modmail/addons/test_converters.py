from __future__ import annotations

from typing import Optional

import pytest
from discord.ext.commands.errors import BadArgument

from modmail.addons.converters import (
    REPO_REGEX,
    ZIP_REGEX,
    AddonConverter,
    SourceAndPluginConverter,
    SourceTypeEnum,
)


@pytest.mark.asyncio
async def test_converter() -> None:
    """Convert a user input into a Source."""
    with pytest.raises(NotImplementedError):
        addon = await AddonConverter().convert(None, "github")  # noqa: F841


# fmt: off
@pytest.mark.parametrize(
    "entry, user, repo, addon, reflike, githost",
    [
        (
            "onerandomusername/addons planet",
            "onerandomusername", "addons", "planet", None, None,
        ),
        (
            "github onerandomusername/addons planet @master",
            "onerandomusername", "addons", "planet", "master", "github",
        ),
        (
            "gitlab onerandomusername/repo planet @v1.0.2",
            "onerandomusername", "repo", "planet", "v1.0.2", "gitlab",
        ),
        (
            "github onerandomusername/repo planet @master",
            "onerandomusername", "repo", "planet", "master", "github",
        ),
        (
            "github onerandomusername/repo planet @bad-toml",
            "onerandomusername", "repo", "planet", "bad-toml", "github",
        ),
        (
            "gitlab onerandomusername/repo planet @main",
            "onerandomusername", "repo", "planet", "main", "gitlab",
        ),
        (
            "https://github.com/onerandomusername/repo planet",
            "onerandomusername", "repo", "planet", None, "github",
        ),
        (
            "https://gitlab.com/onerandomusername/repo planet",
            "onerandomusername", "repo", "planet", None, "gitlab",
        ),
        (
            "https://github.com/psf/black black @21.70b",
            "psf", "black", "black", "21.70b", "github",
        )
    ],
)
@pytest.mark.dependency(name="repo_regex")
# fmt: on
def test_repo_regex(
    entry: str, user: str, repo: str, addon: str, reflike: Optional[str], githost: Optional[str]
) -> None:
    """Test the repo regex to ensure that it matches what it should."""
    match = REPO_REGEX.fullmatch(entry)
    assert match is not None
    assert match.group("user") == user
    assert match.group("repo") == repo
    assert match.group("addon") == addon
    assert match.group("reflike") or None == reflike  # noqa: E711
    assert match.group("githost") == githost


# fmt: off
@pytest.mark.parametrize(
    "entry, url, domain, path, addon",
    [
        (
            "https://github.com/onerandomusername/modmail-addons/archive/main.zip planet",
            "github.com/onerandomusername/modmail-addons/archive/main.zip",
            "github.com",
            "onerandomusername/modmail-addons/archive/main.zip",
            "planet",
        ),
        (
            "https://gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip earth",  # noqa: E501
            "gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip",
            "gitlab.com",
            "onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip",
            "earth",
        ),
        (
            "https://example.com/bleeeep.zip myanmar",
            "example.com/bleeeep.zip",
            "example.com",
            "bleeeep.zip",
            "myanmar",

        ),
        (
            "http://github.com/discord-modmail/addons/archive/bast.zip thebot",
            "github.com/discord-modmail/addons/archive/bast.zip",
            "github.com",
            "discord-modmail/addons/archive/bast.zip",
            "thebot",
        ),
        (
            "rtfd.io/plugs.zip documentation",
            "rtfd.io/plugs.zip",
            "rtfd.io",
            "plugs.zip",
            "documentation",
        ),
        (
            "pages.dev/hiy.zip black",
            "pages.dev/hiy.zip",
            "pages.dev",
            "hiy.zip",
            "black",
        ),
    ]
)
# fmt: on
@pytest.mark.dependency(name="zip_regex")
def test_zip_regex(entry: str, url: str, domain: str, path: str, addon: str) -> None:
    """Test the repo regex to ensure that it matches what it should."""
    match = ZIP_REGEX.fullmatch(entry)
    assert match is not None
    assert match.group("url") == url
    assert match.group("domain") == domain
    assert match.group("path") == path
    assert match.group("addon") == addon


# fmt: off
@pytest.mark.parametrize(
    "entry, name, source_type",
    [
        (
            "onerandomusername/addons planet",
            "planet", SourceTypeEnum.REPO
        ),
        (
            "github onerandomusername/addons planet @master",
            "planet", SourceTypeEnum.REPO
        ),
        (
            "gitlab onerandomusername/repo planet @v1.0.2",
            "planet", SourceTypeEnum.REPO
        ),
        (
            "github onerandomusername/repo planet @master",
            "planet", SourceTypeEnum.REPO
        ),
        (
            "gitlab onerandomusername/repo planet @main",
            "planet", SourceTypeEnum.REPO
        ),
        (
            "https://github.com/onerandomusername/repo planet",
            "planet", SourceTypeEnum.REPO
        ),
        (
            "https://gitlab.com/onerandomusername/repo planet",
            "planet", SourceTypeEnum.REPO
        ),
        (
            "https://github.com/psf/black black @21.70b",
            "black", SourceTypeEnum.REPO
        ),
        (
            "github.com/onerandomusername/modmail-addons/archive/main.zip earth",
            "earth", SourceTypeEnum.ZIP
        ),
        (
            "https://github.com/onerandomusername/modmail-addons/archive/main.zip planet",
            "planet", SourceTypeEnum.ZIP
        ),
        (
            "https://gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip earth",  # noqa: E501
            "earth", SourceTypeEnum.ZIP
        ),
        (
            "https://example.com/bleeeep.zip myanmar",
            "myanmar", SourceTypeEnum.ZIP
        ),
        (
            "http://github.com/discord-modmail/addons/archive/bast.zip thebot",
            "thebot", SourceTypeEnum.ZIP
        ),
        (
            "rtfd.io/plugs.zip documentation",
            "documentation", SourceTypeEnum.ZIP
        ),
        (
            "pages.dev/hiy.zip black",
            "black", SourceTypeEnum.ZIP
        ),
        (
            "@local earth",
            "earth", SourceTypeEnum.LOCAL
        ),
        pytest.param(
            "the world exists.",
            None, None,
            marks=pytest.mark.raises(exception=BadArgument)
        ),
    ],
)
@pytest.mark.dependency(depends_on=["repo_regex", "zip_regex"])
@pytest.mark.asyncio
# fmt: on
async def test_plugin_with_source_converter(entry: str, name: str, source_type: SourceTypeEnum) -> None:
    """Test the Plugin converter works, and successfully converts a plugin with its source."""
    plugin, source = await SourceAndPluginConverter().convert(None, entry)
    assert plugin.name == name
    assert source.source_type == source_type
