"""
Script wrapper for scripts.

This allows scripts to be invoked through the scripts module.

The exposed interface is just running the internal files.
Whatever interface they have, is what is shown.
"""

import functools
import runpy
import sys

import click


# key: alias
# value: tuple of module name, help description
commands: "dict[str, tuple[str, str | None]]" = {
    "export_req": ("scripts.export_requirements", "Export requirements to requirements.txt"),
}


def run_script(module_name: str, *args, **kwargs) -> None:
    """
    Run the provided module, with the provided args and kwargs.

    The provided defaults are what makes the environment nearly the same as if module was invoked directly.
    """
    kwargs.setdefault("run_name", "__main__")
    kwargs.setdefault("alter_sys", True)
    runpy.run_module(module_name, **kwargs)


@click.group()
@click.help_option("-h", "--help")
def cli() -> None:
    """
    Custom scripts which help modmail development.

    All custom scripts should be listed below as a command, with a description.
    In addition, some built in modules may be listed below as well.
    If a custom script is not shown below please open an issue.
    """
    pass


def main(cmd: str = None) -> None:
    """Add the commands and run the cli."""
    if cmd is None:
        cmd = []
    for k, v in commands.items():
        func = functools.partial(run_script, v[0])
        cli.add_command(click.Command(k, help=v[1], callback=func))
    cli.main(cmd, standalone_mode=False)


if __name__ == "__main__":
    try:
        cmd = [sys.argv[1]]
        sys.argv.pop(1)  # pop the first arg out of sys.argv since its being used to get the name
    except IndexError:
        cmd = []
    try:
        main(cmd)
    except click.ClickException as e:
        e.show()
        sys.exit()
