#  Contributing to Modmail

Welcome to Modmail, and thank you for your interest in contributing!

## Note
We recommend checking open issues for something you would like to work on. If something is interesting, leave a comment and wait for a person to assign you, otherwise someone else may already be working on the same thing.

## Installation

To get started, you need:

- git
- python 3.8 or higher
- poetry

These are the bare minimum requirements, as poetry is used to install everything needed by our project. You can find installation instructions on [poetry's website][poetry-install].

If you have write access to this repo, you may make a new branch and push changes to it here. Otherwise, make a [fork][], and clone it locally to push your changes to. Be sure to push your changes to a new branch.


To install all dependencies, run the following command.
```sh
poetry install
```
This will create a venv for our project, and install everything to the venv.


Next, install our pre-commit hook, which will help ensure all commits follow our coding guidelines.

```sh
poetry run task precommit
```

This installs [pre-commit][] to git's hooks, and all of the tools too.

## Testing

We use pytest for our testing framework, and to run our tests.

If you are adding features, we expect tests to be written, and passing.

To run the entire test suite, use
```sh
poetry run task test
```
If you would like to run just a specific file's test, use
```sh
poetry run task test {file}
```

## Run the bot

To run the bot, use:
```sh
poetry run task run
```

## Tasks

We use [taskipy][] to run a bunch of our common commands. These are subject to change, but you can always get an up to date list by running the following:
```sh
poetry run task --list
```

## A note on Poetry

All of the commands in this page use `poetry run` for the sake of clarity. However, it is possible to use **`poetry shell`** to enter the venv and therefore not require `poetry run` before every command.

-------

## Submit Changes

To submit your changes, go to the [pulls][] page, select your branch, and create a new pull request pointed towards our repository.
We recommend creating a pull request even while it is in progress, so we can see it as it goes on.

[fork]: https://github.com/discord-modmail/modmail/fork
[poetry-install]: https://python-poetry.org/docs#installation
[pre-commit]: https://pre-commit.com/
[pulls]: https://github.com/discord-modmail/modmail/pulls
[taskipy]: https://pypi.org/project/taskipy/
