from typing import List

import pytest

from modmail.utils.pagination import ButtonPaginator


@pytest.mark.asyncio
async def test_paginator_init():
    """Test that we can safely create a paginator."""
    content = ["content"]
    paginator = ButtonPaginator(content, prefix="", suffix="", linesep="")
    assert paginator.pages == content


@pytest.mark.xfail("Currently broken.")
@pytest.mark.parametrize("content, footer_text", [(["5"], "Snap, crackle, pop"), (["Earthly"], "world")])
@pytest.mark.asyncio
async def test_paginator_footer(content, footer_text):
    """Test the paginator footer matches what is passed."""
    pag = ButtonPaginator(content, footer_text=footer_text)
    print("index:", pag.index)
    print("page len: ", len(pag.pages))
    assert pag.footer_text == footer_text
    if footer_text is not None:
        assert pag.get_footer().endswith(f"{len(content)})")
    else:
        assert pag.get_footer().endswith(f"{len(content)})")
    assert pag.get_footer().startswith(footer_text)
