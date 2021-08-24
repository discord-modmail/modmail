from __future__ import annotations

from re import Match
from textwrap import dedent

import pytest

import modmail.utils.addons.sources
from modmail.utils.addons.sources import REPO_REGEX, ZIP_REGEX, AddonConverter

ZIP_TEST_CASES_PASS = [
    "https://github.com/onerandomusername/modmail-addons/archive/main.zip",
    "https://gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip",
    "https://example.com/bleeeep.zip",
    "http://github.com/discord-modmail/addons/archive/bast.zip",
    "rtfd.io/plugs.zip",
    "pages.dev/hiy.zip",
    "https://github.com/onerandomusername/modmail-addons/archive/main.zip planet",
    "https://gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip earth",
    "https://example.com/bleeeep.zip myanmar",
    "http://github.com/discord-modmail/addons/archive/bast.zip thebot",
    "rtfd.io/plugs.zip documentation",
    "pages.dev/hiy.zip",
]
REPO_TEST_CASES_PASS = [
    "onerandomusername/repo planet",
    "github onerandomusername/repo planet @master",
    "gitlab onerandomusername/repo planet @v1.0.2",
    "github onerandomusername/repo planet @master",
    "gitlab onerandomusername/repo planet @main",
    "https://github.com/onerandomusername/repo planet",
    "https://gitlab.com/onerandomusername/repo planet",
]


@pytest.mark.skip
@pytest.mark.xfail(reason="Not implemented")
def test_converter() -> None:
    """Convert a user input into a Source."""
    addon = AddonConverter().convert(None, "github")  # noqa: F841


def test_zip_regex() -> None:
    """Test the zip regex correctly gets zip and not the other."""
    for case in ZIP_TEST_CASES_PASS:
        print(case)
        assert isinstance(ZIP_REGEX.fullmatch(case), Match)
    for case in REPO_TEST_CASES_PASS:
        print(case)
        assert ZIP_REGEX.fullmatch(case) is None


def test_repo_regex() -> None:
    """Test the repo regex to ensure that it matches what it should and none of what it shouldn't."""
    for case in REPO_TEST_CASES_PASS:
        print(case)
        assert isinstance(REPO_REGEX.fullmatch(case), Match)
    for case in ZIP_TEST_CASES_PASS:
        print(case)
        assert REPO_REGEX.fullmatch(case) is None
