import os
import shutil
import sys
from typing import Any, Optional

from click import Option, UsageError, echo, style


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
    _out(message, nl=nl, **styles)


def err(message: Optional[str] = None, nl: bool = True, **styles: Any) -> None:
    _err(message, nl=nl, **styles)


def find_editor():
    for var in "GIT_EDITOR", "EDITOR":
        editor = os.environ.get(var)
        if editor is not None:
            return editor
    if sys.platform == "win32":
        fallbacks = ["notepad.exe"]
    else:
        fallbacks = ["/etc/alternatives/editor", "nano"]
    for fallback in fallbacks:
        if os.path.isabs(fallback):
            found_path = fallback
        else:
            found_path = shutil.which(fallback)
        if found_path and os.path.exists(found_path):
            return found_path
    err("Oh no! 💥 💔 💥 Could not find an editor! Set the EDITOR environment variable.", fg="red")


class NotRequiredIf(Option):
    def __init__(self, *args, **kwargs):
        self.not_required_if = kwargs.pop("not_required_if")
        assert self.not_required_if, "'not_required_if' parameter required"
        kwargs["help"] = (
            kwargs.get("help", "")
            + " NOTE: This argument is mutually exclusive with %s" % self.not_required_if
        ).strip()
        super(NotRequiredIf, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        we_are_present = self.name in opts
        other_present = self.not_required_if in opts

        if other_present:
            if we_are_present:
                err(
                    "Oh no! 💥 💔 💥 Illegal usage. `%s` is mutually exclusive with `%s`"
                    % (self.name, self.not_required_if),
                    fg="red",
                )
                ctx.exit(code=1)
            else:
                self.prompt = None

        return super(NotRequiredIf, self).handle_parse_result(ctx, opts, args)
