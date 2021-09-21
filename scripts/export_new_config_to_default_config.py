"""
Exports the configuration to the configuration default files.

This is intented to be used as a local pre-commit hook, which runs if the modmail/config.py file is changed.
"""
import json
import pathlib
import sys
import typing
from collections import defaultdict

import atoml
import attr
import dotenv
import yaml

import modmail.config


MODMAIL_CONFIG_DIR = pathlib.Path(modmail.config.__file__).parent
ENV_EXPORT_FILE = MODMAIL_CONFIG_DIR.parent / ".env.template"
APP_JSON_FILE = MODMAIL_CONFIG_DIR.parent / "app.json"

METADATA_TABLE = modmail.config.METADATA_TABLE


class MetadataDict(typing.TypedDict):
    """Typed metadata. This has a possible risk given that the modmail_metadata variable is defined."""

    modmail_metadata: modmail.config.ConfigMetadata
    required: bool


def export_default_conf() -> None:
    """Export default configuration as both toml and yaml to the preconfigured locations."""
    default = modmail.config.get_default_config()
    dump: dict = modmail.config.ConfigurationSchema().dump(default)

    # Sort the dictionary configuration.
    # This is the only place where the order of the config should matter, when exporting in a specific style
    def sort_dict(d: dict) -> dict:
        """Takes a dict and sorts it, recursively."""
        sorted_dict = {x[0]: x[1] for x in sorted(d.items(), key=lambda e: e[0])}

        for k, v in d.items():
            if not isinstance(v, dict):
                continue
            sorted_dict[k] = sort_dict(v)

        return sorted_dict

    dump = sort_dict(dump)
    autogen_gen_notice = f"Directly run scripts/{__file__.rsplit('/',1)[-1]!s} to generate."
    doc = atoml.document()
    doc.add(atoml.comment("This is an autogenerated TOML document."))
    doc.add(atoml.comment(autogen_gen_notice))
    doc.add(atoml.nl())

    doc.update(dump)

    # toml

    with open(MODMAIL_CONFIG_DIR / (modmail.config.AUTO_GEN_FILE_NAME + ".toml"), "w") as f:
        atoml.dump(doc, f)

    # yaml
    with open(MODMAIL_CONFIG_DIR / (modmail.config.AUTO_GEN_FILE_NAME + ".yaml"), "w") as f:
        f.write("# This is an autogenerated YAML document.\n")
        f.write(f"# {autogen_gen_notice}\n")
        yaml.dump(dump, f, indent=4, Dumper=yaml.SafeDumper)


def export_env_and_app_json_conf() -> None:
    """
    Exports required configuration variables to .env.template.

    Does NOT export *all* settable variables!

    Export the *required* environment variables to `.env.template`.
    Required environment variables are any Config.default variables that default to marshmallow.missing
    These can also be configured by using the ConfigMetadata options.
    """
    default = modmail.config.get_default_config()

    # find all environment variables to report
    def get_env_vars(klass: type, env_prefix: str = None) -> typing.Dict[str, MetadataDict]:

        if env_prefix is None:
            env_prefix = modmail.config.ENV_PREFIX

        # exact name, default value
        export: typing.Dict[str, MetadataDict] = dict()  # any missing required vars provide as missing

        for var in attr.fields(klass):
            if attr.has(var.type):
                # var is an attrs class too, run this on it.
                export.update(
                    get_env_vars(
                        var.type,
                        env_prefix=env_prefix + var.name.upper() + "_",
                    )
                )
            else:
                meta: MetadataDict = var.metadata
                # put all values in the dict, we'll iterate through them later.
                export[env_prefix + var.name.upper()] = meta

        return export

    # dotenv modifies currently existing files, but we want to erase the current file
    ENV_EXPORT_FILE.unlink(missing_ok=True)
    ENV_EXPORT_FILE.touch()

    exported = get_env_vars(default.__class__)

    with open(APP_JSON_FILE) as f:
        try:
            app_json: typing.Dict = json.load(f)
        except Exception as e:
            print(
                "Oops! Please ensure the app.json file is valid json! "
                "If you've made manual edits, you may want to revert them."
            )
            raise e

    app_json_env = dict()

    for key, meta in exported.items():
        if meta[METADATA_TABLE].export_to_env_template or meta.get("required", False):

            dotenv.set_key(
                ENV_EXPORT_FILE,
                key,
                meta[METADATA_TABLE].export_environment_prefill or meta["default"],
            )

        if (
            meta[METADATA_TABLE].export_to_app_json
            or meta[METADATA_TABLE].export_to_env_template
            or meta.get("required", False)
        ):

            options = defaultdict(
                str,
                {
                    "description": meta[METADATA_TABLE].description,
                    "required": meta[METADATA_TABLE].app_json_required or meta.get("required", False),
                },
            )
            if (value := meta[modmail.config.METADATA_TABLE].app_json_default) is not None:
                options["value"] = value
            app_json_env[key] = options

    app_json["env"] = app_json_env
    with open(APP_JSON_FILE, "w") as f:
        json.dump(app_json, f, indent=4)
        f.write("\n")


def main() -> None:
    """
    Exports the default configuration.

    There's several parts to this export.
    First, export the default configuration to the default locations.

    Next, export the *required* configuration variables to the .env.template

    In addition, export to app.json when exporting .env.template.
    """
    export_default_conf()

    export_env_and_app_json_conf()


if __name__ == "__main__":
    print("Exporting configuration to default files. If they exist, overwriting their contents.")
    sys.exit(main())
