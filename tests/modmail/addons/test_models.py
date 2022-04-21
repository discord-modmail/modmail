from __future__ import annotations

from typing import Optional

import pytest

from modmail.addons.models import Addon, AddonSource, Plugin, SourceTypeEnum


def test_addon_model() -> None:
    """All addons will be of a specific type, so we should not be able to create a generic addon."""
    with pytest.raises(NotImplementedError, match="Inheriting classes need to implement their own init"):
        Addon()


@pytest.mark.parametrize(
    "zip_url, source_type",
    [
        ("github.com/bast0006.zip", SourceTypeEnum.ZIP),
        ("gitlab.com/onerandomusername.zip", SourceTypeEnum.REPO),
        (None, SourceTypeEnum.LOCAL),
    ],
)
def test_addonsource_init(zip_url: str, source_type: SourceTypeEnum) -> None:
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
def test_addonsource_from_repo(user: str, repo: str, reflike: Optional[str], githost: str) -> None:
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
def test_addonsource_from_zip(url: str) -> None:
    """Test an addon source is properly made from a zip url."""
    src = AddonSource.from_zip(url)
    assert src.zip_url == url
    assert src.source_type == SourceTypeEnum.ZIP


class TestPlugin:
    """Test the Plugin class creation."""

    @pytest.mark.parametrize("folder", [("earth"), ("mona-lisa")])
    def test_plugin_init(self, folder: str) -> None:
        """Create a plugin model, and ensure it has the right properties."""
        plugin = Plugin(folder)
        assert isinstance(plugin, Plugin)
        assert plugin.folder_name == folder
