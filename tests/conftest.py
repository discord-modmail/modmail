import aiohttp
import aioresponses
import pytest


@pytest.fixture
def aioresponse():
    """Fixture to mock aiohttp responses."""
    with aioresponses.aioresponses() as aioresponse:
        yield aioresponse


@pytest.fixture
@pytest.mark.asyncio
async def http_session(aioresponse) -> aiohttp.ClientSession:
    """
    Fixture function for a aiohttp.ClientSession.

    Requests fixture aioresponse to ensure that all client sessions do not make actual requests.
    """
    resolver = aiohttp.AsyncResolver()
    connector = aiohttp.TCPConnector(resolver=resolver)
    client_session = aiohttp.ClientSession(connector=connector)

    yield client_session

    await client_session.close()
    await connector.close()
    await resolver.close()
