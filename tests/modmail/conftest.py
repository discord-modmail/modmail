import pytest


def pytest_report_header(config) -> str:
    """Pytest headers."""
    return "package: modmail"


@pytest.fixture(autouse=True, scope="package")
def patch_embeds():
    """Run the patch embed method. This is normally run by modmail.__main__, which is not run for testing."""
    import modmail.utils.embeds

    modmail.utils.embeds.patch_embed()
