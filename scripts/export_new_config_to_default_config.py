"""
Exports the configuration to the configuration default files.

This is intented to be used as a local pre-commit hook, which runs if the modmail/config.py file is changed.
"""
import sys

import atoml  # noqa: F401
import yaml  # noqa: F401

import modmail.config


if __name__ == "__main__":
    print("Exporting configuration to default files. If they exist, overwriting their contents.")
    sys.exit(modmail.config.export_default_conf(export_yaml=True))
