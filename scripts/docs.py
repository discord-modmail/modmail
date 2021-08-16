"""
Helper module to work with documentation of discord modmail.

@author Tiangolo tiangolo@gmail.com
@licence MIT

Refactored code:
    - according to our needs
    - agree to _black_ and follows PEP8
    - made some sections more pythonic
"""

import os
import shutil
from http.server import HTTPServer, SimpleHTTPRequestHandler
from multiprocessing import Pool
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import mkdocs.commands.build
import mkdocs.commands.serve
import mkdocs.config
import mkdocs.utils
import typer
import yaml

app = typer.Typer()

mkdocs_config = "mkdocs.yml"
missing_translation_snippet = """
!!! warning
        The current page still doesn't have a translation for this language.
        But you can help to translate it: [Contributing](https://abcabc.com/).
"""
url_base = "http://127.0.0.1:8000/discord-modmail/modmail/"
docs_path = Path("docs")
en_docs_path = Path("docs/en")
en_config_path: Path = en_docs_path / mkdocs_config


def get_en_config() -> dict:
    """Load english translation's mkdocs config and return parsed config."""
    return mkdocs.utils.yaml_load(en_config_path.read_text(encoding="utf-8"))


def get_lang_config(path: Path) -> dict:
    """Load `path` as mkdocs config and return parsed config."""
    return mkdocs.utils.yaml_load(path.read_text(encoding="utf-8"))


def get_lang_paths() -> list[Path]:
    """Return all translations for discord modmail as a list of their paths."""
    return sorted(docs_path.iterdir())


def lang_callback(lang: Optional[str]) -> Optional[str]:
    """
    Validating argument handler for typer argument.

    Checks if the `lang` is a valid language code for documentation.
    """
    if lang is None:
        return
    if not lang.isalpha() or len(lang) != 2:
        typer.echo("Use a 2 letter language code, like: es", color=typer.colors.RED)
        raise typer.Abort()
    lang = lang.lower()
    return lang


def complete_existing_lang(incomplete: str) -> None:
    """Autocompletion handler for typer argument."""
    lang_path: Path
    for lang_path in get_lang_paths():
        if lang_path.is_dir() and lang_path.name.startswith(incomplete):
            yield lang_path.name


def get_base_lang_config(lang: str) -> dict:
    """Generate a basic mkdocs config from the english translation mkdocs config."""
    en_config = get_en_config()

    new_config = en_config.copy()
    new_config["site_url"] = en_config["site_url"] + f"{lang}/"
    new_config["theme"]["logo"] = url_base + en_config["theme"]["logo"]
    new_config["theme"]["favicon"] = url_base + en_config["theme"]["favicon"]
    new_config["theme"]["language"] = lang
    new_config["nav"] = en_config["nav"][:2]
    new_config["extra_css"] = [
        f"{'' if css.startswith('http') else url_base}{css}" for css in en_config["extra_css"]
    ]
    new_config["extra_javascript"] = [
        f"{'' if js.startswith('http') else url_base}{js}" for js in en_config["extra_javascript"]
    ]
    return new_config


@app.command()
def new_lang(lang: str = typer.Argument(..., callback=lang_callback)) -> None:
    """
    Generate a new docs translation directory for the language LANG.

    LANG should be a 2-letter language code, like: en, es, de, pt, etc.
    """
    new_path: Path = Path("docs") / lang
    if new_path.exists():
        typer.echo(f"The language was already created: {lang}", color=typer.colors.RED)
        return

    new_path.mkdir()
    new_config = get_base_lang_config(lang)
    new_config_path: Path = Path(new_path) / mkdocs_config
    new_config_path.write_text(
        yaml.dump(new_config, sort_keys=False, width=200, allow_unicode=True),
        encoding="utf-8",
    )
    new_config_docs_path: Path = new_path / "docs"
    new_config_docs_path.mkdir()

    en_index_path: Path = en_docs_path / "docs" / "index.md"
    new_index_path: Path = new_config_docs_path / "index.md"

    en_index_content = en_index_path.read_text(encoding="utf-8")
    new_index_content = f"{missing_translation_snippet}\n\n{en_index_content}"

    new_index_path.write_text(new_index_content, encoding="utf-8")

    typer.secho(f"Successfully initialized: {new_path}", color=typer.colors.GREEN)
    update_languages(lang=None)


@app.command()
def build_lang(
    lang: str = typer.Argument(..., callback=lang_callback, autocompletion=complete_existing_lang)
) -> None:
    """Build the docs for a language, filling missing pages with translation notifications."""
    lang_path: Path = Path("docs") / lang
    if not lang_path.is_dir():
        typer.echo(f"The language translation doesn't seem to exist yet: {lang}", color=typer.colors.RED)
        return

    typer.echo(f"Building docs_for: {lang}", color=typer.colors.BLUE)
    build_dir_path = Path("docs_dir")
    build_dir_path.mkdir(exist_ok=True)
    build_lang_path = build_dir_path / lang

    en_lang_path = Path("docs/en")
    site_path = Path("site").absolute()
    dist_path: Path = site_path if lang == "en" else site_path / lang

    shutil.rmtree(build_lang_path, ignore_errors=True)
    shutil.copytree(lang_path, build_lang_path)

    overrides_src = en_docs_path / "overrides"
    overrides_dest = build_lang_path / "overrides"

    for path in overrides_src.iterdir():
        dest_path = overrides_dest / path.name
        if not dest_path.exists():
            shutil.copy(path, dest_path)

    en_config = get_en_config()
    nav = en_config["nav"]
    lang_config = get_lang_config(lang_path / mkdocs_config)
    lang_nav = lang_config["nav"]

    # Exclude first 2 entries DiscordModmail and Languages, for custom handling
    use_nav, lang_use_nav = nav[2:], lang_nav[2:]
    file_to_nav = get_file_to_nav_map(use_nav)
    sections = get_sections(use_nav)
    lang_file_to_nav = get_file_to_nav_map(lang_use_nav)
    use_lang_file_to_nav = get_file_to_nav_map(lang_use_nav)

    for file in file_to_nav:
        file_path = Path(file)
        lang_file_path: Path = build_lang_path / "docs" / file_path
        en_file_path: Path = en_lang_path / "docs" / file_path
        lang_file_path.parent.mkdir(parents=True, exist_ok=True)

        if not lang_file_path.is_file():
            en_text = en_file_path.read_text(encoding="utf-8")
            lang_text = get_text_with_translate_missing(en_text)
            lang_file_path.write_text(lang_text, encoding="utf-8")
            file_key = file_to_nav[file]
            use_lang_file_to_nav[file] = file_key

            if file_key:
                composite_key = ()
                new_key = ()
                for key_part in file_key:
                    composite_key += (key_part,)
                    key_first_file = sections[composite_key]
                    if key_first_file in lang_file_to_nav:
                        new_key = lang_file_to_nav[key_first_file]
                    else:
                        new_key += (key_part,)
                use_lang_file_to_nav[file] = new_key

    key_to_section = {(): []}
    for file, orig_file_key in file_to_nav.items():
        file_key = use_lang_file_to_nav[file] if file in use_lang_file_to_nav else orig_file_key
        section = get_key_section(key_to_section=key_to_section, key=file_key)
        section.append(file)

    new_nav = key_to_section[()]
    lang_config["nav"] = [lang_nav[0], nav[1]] + new_nav  # Export language navbar
    build_lang_config_path: Path = build_lang_path / mkdocs_config
    build_lang_config_path.write_text(
        yaml.dump(lang_config, sort_keys=False, width=200, allow_unicode=True),
        encoding="utf-8",
    )

    current_dir = os.getcwd()
    os.chdir(build_lang_path)
    mkdocs.commands.build.build(mkdocs.config.load_config(site_dir=str(dist_path)))
    os.chdir(current_dir)
    typer.secho(f"Successfully built docs for: {lang}", color=typer.colors.GREEN)


def read_readme_content() -> str:
    """Read english translation's index.md."""
    en_index = en_docs_path / "docs" / "index.md"
    return en_index.read_text("utf-8")


@app.command()
def generate_readme() -> None:
    """Generate README.md content from main index.md!"""
    typer.echo("Generating README", color=typer.colors.BLUE)
    readme_path = Path("README.md")
    new_content = read_readme_content()
    readme_path.write_text(new_content, encoding="utf-8")


@app.command()
def verify_readme() -> None:
    """Verify README.md content from main index.md!"""
    typer.echo("Verifying README", color=typer.colors.BLUE)
    readme_path = Path("README.md")
    generated_content = read_readme_content()
    readme_content = readme_path.read_text("utf-8")
    if generated_content != readme_content:
        typer.secho("README.md outdated from the latest index.md", color=typer.colors.RED)
        raise typer.Abort()
    typer.echo("Valid README ✅", color=typer.colors.GREEN)


@app.command()
def build_all() -> None:
    """Build mkdocs site for each language inside, result at ./site/!"""
    site_path = Path("site").absolute()
    update_languages(lang=None)
    current_dir = os.getcwd()
    os.chdir(en_docs_path)
    typer.echo("Building docs for: en", color=typer.colors.BLUE)
    mkdocs.commands.build.build(mkdocs.config.load_config(site_dir=str(site_path)))
    os.chdir(current_dir)
    langs = [lang.name for lang in get_lang_paths() if lang == en_docs_path or not lang.is_dir()]

    cpu_count = os.cpu_count() or 1
    with Pool(cpu_count * 2) as p:
        p.map(build_lang, langs)


def update_single_lang(lang: str) -> None:
    """Update mkdocs.yml config for a particular `lang` only."""
    lang_path = docs_path / lang
    typer.echo(f"Updating {lang_path.name}", color=typer.colors.BLUE)
    update_config(lang_path.name)


@app.command()
def update_languages(
    lang: str = typer.Argument(None, callback=lang_callback, autocompletion=complete_existing_lang)
) -> None:
    """
    Update the mkdocs.yml file Languages section including all the available languages.

    The LANG argument is a 2-letter language code. If it's not provided, update all the
    mkdocs.yml files (for all the languages).
    """
    if lang is None:
        for lang_path in get_lang_paths():
            if lang_path.is_dir():
                update_single_lang(lang_path.name)
    else:
        update_single_lang(lang)


@app.command()
def serve() -> None:
    """
    A quick server to preview a built site with translations.

    For development, prefer the command live (or just mkdocs serve).

    This is here only to preview a site with translations already built.

    Make sure you run the build-all command first.
    """
    typer.echo("Make sure you run the build-all command first.", color=typer.colors.RED)
    os.chdir("site")
    server_address = ("", 8008)
    server = HTTPServer(server_address, SimpleHTTPRequestHandler)
    typer.echo("Serving at: http://127.0.0.1:8008", color=typer.colors.GREEN)
    server.serve_forever()


@app.command()
def live(
    lang: str = typer.Argument("en", callback=lang_callback, autocompletion=complete_existing_lang)
) -> None:
    """
    Serve with livereload a docs site for a specific language.

    This only shows the actual translated files, not the placeholders created with
    build-all.

    Takes an optional LANG argument with the name of the language to serve, by default
    en.
    """
    lang_path: Path = docs_path / lang
    os.chdir(lang_path)
    typer.echo("Serving at: http://127.0.0.1:8008/discord-modmail/modmail/", color=typer.colors.GREEN)
    mkdocs.commands.serve.serve(dev_addr="127.0.0.1:8008")


def update_config(lang: str) -> None:
    """Add new language paths to extra.alternate by looping through docs directory."""
    lang_path: Path = docs_path / lang
    config_path: Path = lang_path / mkdocs_config
    current_config = get_lang_config(config_path)

    if lang == "en":
        config = get_en_config()
    else:
        config = get_base_lang_config(lang)
        config["nav"] = current_config["nav"]
        config["theme"]["language"] = current_config["theme"]["language"]

    languages = [{"en": "/"}]
    alternate: List[Dict[str, str]] = config["extra"].get("alternate", [])
    alternate_dict = {alt["link"]: alt["name"] for alt in alternate}
    new_alternate: List[Dict[str, str]] = []

    for lang_path in get_lang_paths():
        if lang_path.name == "en" or not lang_path.is_dir():
            continue
        languages.append({lang_path.name: f"/{lang_path.name}/"})

    for lang_dict in languages:
        name = list(lang_dict.keys())[0]
        url = lang_dict[name]
        if url not in alternate_dict:
            new_alternate.append({"link": url, "name": name})
        else:
            new_alternate.append({"link": url, "name": alternate_dict[url]})

    config["nav"][1] = {"Languages": languages}
    config["extra"]["alternate"] = new_alternate
    config_path.write_text(
        yaml.dump(config, sort_keys=False, width=200, allow_unicode=True),
        encoding="utf-8",
    )


def get_key_section(*, key_to_section: Dict[Tuple[str, ...], list], key: Tuple[str, ...]) -> list:
    """Get section from keys."""
    if key in key_to_section:
        return key_to_section[key]
    super_key = key[:-1]
    title = key[-1]
    super_section = get_key_section(key_to_section=key_to_section, key=super_key)
    new_section = []
    super_section.append({title: new_section})
    key_to_section[key] = new_section
    return new_section


def get_text_with_translate_missing(text: str) -> str:
    """Get missing translation text for sections whose translations haven't been done yet."""
    lines = text.splitlines()
    lines.insert(1, missing_translation_snippet)
    return "\n".join(lines)


def get_file_to_nav_map(nav: list) -> Dict[str, Tuple[str, ...]]:
    """Generate navbar through file."""
    file_to_nav = {}
    for item in nav:
        if type(item) is str:
            file_to_nav[item] = tuple()
        elif type(item) is dict:
            item_key = list(item.keys())[0]
            sub_nav = item[item_key]
            sub_file_to_nav = get_file_to_nav_map(sub_nav)
            for k, v in sub_file_to_nav.items():
                file_to_nav[k] = (item_key,) + v
    return file_to_nav


def get_sections(nav: list) -> Dict[Tuple[str, ...], str]:
    """Get all page sections to form index through `nav`."""
    sections = {}
    for item in nav:
        if type(item) is str:
            continue
        elif type(item) is dict:
            item_key = list(item.keys())[0]
            sub_nav = item[item_key]
            sections[(item_key,)] = sub_nav[0]
            sub_sections = get_sections(sub_nav)
            for k, v in sub_sections.items():
                sections[(item_key,) + k] = v
    return sections


if __name__ == "__main__":
    app()
