from __future__ import annotations

from typing import TYPE_CHECKING

import aiohttp
import pytest


if TYPE_CHECKING:
    import aioresponses


class TestSessionFixture:
    """Grouping for aiohttp.ClientSession fixture tests."""

    @pytest.mark.asyncio
    async def test_session_fixture_no_requests(self, http_session: aiohttp.ClientSession):
        """
        Test all requests fail.

        This means that aioresponses is being requested by the http_session fixture.
        """
        url = "https://github.com/"

        with pytest.raises(aiohttp.ClientConnectionError):
            await http_session.get(url)

    @pytest.mark.asyncio
    async def test_session_fixture_mock_requests(
        self, aioresponse: aioresponses.aioresponses, http_session: aiohttp.ClientSession
    ):
        """
        Test all requests fail.

        This means that aioresponses is being requested by the http_session fixture.
        """
        url = "https://github.com/"
        status = 200
        aioresponse.get(url, status=status)

        async with http_session.get(url) as resp:
            assert status == resp.status
