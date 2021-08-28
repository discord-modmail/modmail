from __future__ import annotations

from re import Match
from textwrap import dedent

import pytest

from modmail.utils.addons.converters import REPO_REGEX, ZIP_REGEX, AddonConverter


@pytest.mark.skip
@pytest.mark.xfail(reason="Not implemented")
def test_converter() -> None:
    """Convert a user input into a Source."""
    addon = AddonConverter().convert(None, "github")  # noqa: F841


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
# fmt: on
def test_repo_regex(entry, user, repo, addon, reflike, githost) -> None:
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
def test_zip_regex(entry, url, domain, path, addon) -> None:
    """Test the repo regex to ensure that it matches what it should."""
    match = ZIP_REGEX.fullmatch(entry)
    assert match is not None
    assert match.group("url") == url
    assert match.group("domain") == domain
    assert match.group("path") == path
    assert match.group("addon") == addon
