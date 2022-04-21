import pytest

from modmail.utils.pagination import ButtonPaginator


@pytest.mark.asyncio
async def test_paginator_init() -> None:
    """Test that we can safely create a paginator."""
    content = ["content"]
    paginator = ButtonPaginator(content, prefix="", suffix="", linesep="")
    assert paginator.pages == content
