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

    @pytest.mark.parametrize(
        "user, repo, name, reflike, githost",
        [
            ("onerandomusername", "addons", "planet", None, "github"),
            ("onerandomusername", "addons", "planet", "master", "github"),
            ("onerandomusername", "repo", "planet", "v1.0.2", "gitlab"),
            ("onerandomusername", "repo", "planet", "master", "github"),
            ("onerandomusername", "repo", "planet", "main", "gitlab"),
            ("onerandomusername", "repo", "planet", None, "github"),
            ("onerandomusername", "repo", "planet", None, "gitlab"),
            ("psf", "black", "black", "21.70b", "github"),
        ],
    )
    def test_plugin_from_repo_match(self, user, repo, name, reflike, githost):
        """Test that a plugin can be created from a repo."""
        plug = Plugin.from_repo(name, user, repo, reflike, githost)
        assert plug.name == name
        assert plug.source.user == user
        assert plug.source.repo == repo
        assert plug.source.reflike == reflike
        assert plug.source.githost == githost
        assert plug.source.source_type == SourceTypeEnum.REPO

    @pytest.mark.parametrize(
        "url, addon",
        [
            ("github.com/onerandomusername/modmail-addons/archive/main.zip", "planet"),
            ("gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip", "earth"),
            ("example.com/bleeeep.zip", "myanmar"),
            ("github.com/discord-modmail/addons/archive/bast.zip", "thebot"),
            ("rtfd.io/plugs.zip", "documentation"),
            ("pages.dev/hiy.zip", "black"),
        ],
    )
    def test_plugin_from_zip(self, url, addon):
        """Test that a plugin can be created from a zip url."""
        plug = Plugin.from_zip(addon, url)
        assert plug.name == addon
        assert plug.source.zip_url == url
        assert plug.source.source_type == SourceTypeEnum.ZIP
