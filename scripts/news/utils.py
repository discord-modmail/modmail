import base64
import hashlib
from typing import Any, List, Mapping, Optional

import click
from click import Option, echo, style

from . import ERROR_MSG_PREFIX


def nonceify(body: str) -> str:
    """
    Nonceify the changelog body!

    Generate hopefully-unique string of characters meant to prevent filename collisions. by computing the
    MD5 hash of the text, converting it to base64 (using the "urlsafe" alphabet), and taking the first
    6 characters of that.
    """
    digest = hashlib.md5(body.encode("utf-8")).digest()  # noqa: S303
    return base64.urlsafe_b64encode(digest)[0:6].decode("ascii")


def _out(message: Optional[str] = None, nl: bool = True, **styles: Any) -> None:
    if message is not None:
        if "bold" not in styles:
            styles["bold"] = True
        message = style(message, **styles)
    echo(message, nl=nl, err=True)


def _err(message: Optional[str] = None, nl: bool = True, **styles: Any) -> None:
    if message is not None:
        if "fg" not in styles:
            styles["fg"] = "red"
        message = style(message, **styles)
    echo(message, nl=nl, err=True)


def out(message: Optional[str] = None, nl: bool = True, **styles: Any) -> None:
    """Utility function to output a styled message to console."""
    _out(message, nl=nl, **styles)


def err(message: Optional[str] = None, nl: bool = True, **styles: Any) -> None:
    """Utility function to output a styled error message to console."""
    _err(message, nl=nl, **styles)


class NotRequiredIf(Option):
    def __init__(self, *args, **kwargs):
        self.not_required_if = kwargs.pop("not_required_if")
        assert self.not_required_if, "'not_required_if' parameter required"  # noqa: S101
        kwargs["help"] = (
            kwargs.get("help", "")
            + " NOTE: This argument is mutually exclusive with %s" % self.not_required_if
        ).strip()
        super(NotRequiredIf, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx: click.Context, opts: Mapping[str, Any], args: List[str]):
        we_are_present = self.name in opts
        other_present = self.not_required_if in opts

        if other_present:
            if we_are_present:
                err(
                    f"{ERROR_MSG_PREFIX} Illegal usage. `%s` is mutually exclusive with `%s`"
                    % (self.name, self.not_required_if),
                    fg="red",
                )
                ctx.exit(code=1)
            else:
                self.prompt = None

        return super(NotRequiredIf, self).handle_parse_result(ctx, opts, args)
