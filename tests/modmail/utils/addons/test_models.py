from __future__ import annotations

import pytest

from modmail.utils.addons.models import Addon, AddonSource, Plugin, SourceTypeEnum


def test_addon_model():
    """All addons will be of a specific type, so we should not be able to create a generic addon."""
    with pytest.raises(NotImplementedError, match="Inheriting classes need to implement their own init"):
        Addon()


@pytest.mark.parametrize(
    "zip_url, source_type",
    [
        ("github.com/bast0006.zip", SourceTypeEnum.ZIP),
        ("gitlab.com/onerandomusername.zip", SourceTypeEnum.REPO),
    ],
)
def test_addonsource_init(zip_url, source_type):
    """Test the AddonSource init sets class vars appropiately."""
    addonsrc = AddonSource(zip_url, source_type)
    assert addonsrc.zip_url == zip_url
    assert addonsrc.source_type == source_type


@pytest.mark.parametrize(
    "user, repo, reflike, githost",
    [
        ("onerandomusername", "addons", None, "github"),
        ("onerandomusername", "addons", "master", "github"),
        ("onerandomusername", "repo", "v1.0.2", "gitlab"),
        ("onerandomusername", "repo", "master", "github"),
        ("onerandomusername", "repo", "main", "gitlab"),
        ("onerandomusername", "repo", None, "github"),
        ("onerandomusername", "repo", None, "gitlab"),
        ("psf", "black", "21.70b", "github"),
    ],
)
def test_addonsource_from_repo(user, repo, reflike, githost):
    """Test an addon source is properly made from repository information."""
    src = AddonSource.from_repo(user, repo, reflike, githost)
    assert src.user == user
    assert src.repo == repo
    assert src.reflike == reflike
    assert src.githost == githost
    assert src.source_type == SourceTypeEnum.REPO


@pytest.mark.parametrize(
    "url",
    [
        ("github.com/onerandomusername/modmail-addons/archive/main.zip"),
        ("gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip"),
        ("example.com/bleeeep.zip"),
        ("github.com/discord-modmail/addons/archive/bast.zip"),
        ("rtfd.io/plugs.zip"),
        ("pages.dev/hiy.zip"),
    ],
)
def test_addonsource_from_zip(url):
    """Test an addon source is properly made from a zip url."""
    src = AddonSource.from_zip(url)
    assert src.zip_url == url
    assert src.source_type == SourceTypeEnum.ZIP


@pytest.fixture(name="source_fixture")
def addonsource_fixture():
    """Addonsource fixture for tests. The contents of this source do not matter, as long as they are valid."""
    return AddonSource("github.com/bast0006.zip", SourceTypeEnum.ZIP)


class TestPlugin:
    """Test the Plugin class creation."""

    @pytest.mark.parametrize("name", [("earth"), ("mona-lisa")])
    def test_plugin_init(self, name, source_fixture):
        """Create a plugin model, and ensure it has the right properties."""
        plugin = Plugin(name, source_fixture)
        assert isinstance(plugin, Plugin)
        assert plugin.name == name

    # fmt: off
    @pytest.mark.parametrize(
        "entry, user, repo, name, reflike, githost",
        [
            (
                "github onerandomusername/addons planet",
                "onerandomusername", "addons", "planet", None, "github",
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
    def test_plugin_from_repo_match(self, entry, user, repo, name, reflike, githost):
        """Test that a plugin can be created from a repo."""
        from modmail.utils.addons.converters import REPO_REGEX

        match = REPO_REGEX.match(entry)
        plug = Plugin.from_repo_match(match)
        assert plug.name == name
        assert plug.source.user == user
        assert plug.source.repo == repo
        assert plug.source.reflike == reflike
        assert plug.source.githost == githost
        assert plug.source.source_type == SourceTypeEnum.REPO

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
    def test_plugin_from_zip_match(self, entry, url, domain, path, addon):
        """Test that a plugin can be created from a zip url."""
        from modmail.utils.addons.converters import ZIP_REGEX

        match = ZIP_REGEX.match(entry)
        plug = Plugin.from_zip_match(match)
        assert plug.name == addon
        assert plug.source.zip_url == url
        assert plug.source.source_type == SourceTypeEnum.ZIP
