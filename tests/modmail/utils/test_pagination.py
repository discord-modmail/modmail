from typing import List, Union

import pytest

from modmail.utils.pagination import ButtonPaginator


@pytest.mark.asyncio
async def test_paginator_init() -> None:
    """Test that we can safely create a paginator."""
    content = ["content"]
    paginator = ButtonPaginator(content, prefix="", suffix="", linesep="")
    assert paginator.pages == content


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content, footer_text",
    [
        (["5"], "Snap, crackle, pop"),
        (["Earthly"], "world"),
        ("There are no plugins installed.", None),
    ],
)
async def test_paginator_footer(content: Union[str, List[str]], footer_text: str) -> None:
    """Test the paginator footer matches what is passed."""
    pag = ButtonPaginator(content, footer_text=footer_text)
    print("index:", pag.index)
    print("page len: ", len(pag.pages))
    assert footer_text == pag.footer_text
    if isinstance(content, str):
        content = [content]

    if footer_text is not None:
        assert pag.get_footer().endswith(f"{len(content)})")
        assert pag.get_footer().startswith(footer_text)

    else:
        assert pag.get_footer().endswith(f"{len(content)}")
