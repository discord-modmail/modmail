# Contributing Guidelines

Thank you so much for your interest in contributing!. All types of contributions are encouraged and valued. See below for different ways to help, and details about how this project handles them!

Please make sure to read the relevant section before making your contribution! It will make it a lot easier for us maintainers to make the most of it and smooth out the experience for all involved. 💚

> **NOTE**: failing to comply with our guidelines may lead to a rejection of the contribution.
> However, most features that are rejected are able to be written as a plugin, and used on your
> bot, without blocking you from getting updates.

If you are confused by any of these rules, feel free to ask us in the `#support` channel in our  [Discord server.](https://discord.gg/ERteGkedDW)

## How do I...

- Ask or Say Something 🤔🐛😱
  - [Request Support](#request-support)
  - [Report an Error or Bug](#report-an-error-or-bug)
  - [Request a Feature](#request-a-feature)
- Make Something 🤓👩🏽‍💻📜🍳
  - [Project Setup](#project-setup)
  - [Contribute Code](#contribute-code)
- Style Guides ✅🙆🏼💃👔
  - [Git Commit Messages](#git-commit-messages)
  - [Python Styleguide](#python-styleguide)

## Request Support

- You can either ask your question as issue by opening one at https://github.com/discord-modmail/modmail/issues.

- [Join the Modmail Discord Server](https://discord.gg/ERteGkedDW)

  - Even though Discord is a chat service, sometimes it takes several hours for community members to respond — please be patient!
  - Use the `#support` channel for questions or discussion about writing or contributing to Discord Modmail bot.
  - There are many other channels available, check the channel list

## Report an Error or Bug

If you run into an error or bug with the project:

> **Note:** If you find a **Closed** issue that seems like it is the same thing that you're experiencing, open a new issue and include a link to the original issue in the body of your new one.

- Open an Issue at [discord-modmail/modmail/issues](https://github.com/discord-modmail/modmail/issues)
- Explain the problem and include additional details to help maintainers reproduce the problem:
  - **Use a clear and descriptive title** for the issue to identify the problem.
  - **Describe the exact steps which reproduce the problem** in as many details as possible. When listing steps, **don't just say what you did, but explain how you did it**.
  - **Provide specific examples to demonstrate the steps**. Include links to files or GitHub projects, or copy/paste-able snippets, which you use in those examples. If you're providing snippets in the issue, use [Markdown code blocks](https://help.github.com/articles/markdown-basics/#multiple-lines).
  - **Describe the behaviour you observed after following the steps** and point out what exactly is the problem with that behaviour.
  - **Explain which behaviour you expected to see instead and why.**
  - **Include screenshots and animated GIFs** which show you following the described steps and clearly demonstrate the problem. If you use the keyboard while following the steps, **record the GIF with the [Keybinding Resolver](https://github.com/atom/keybinding-resolver) shown**. You can use [this tool](https://www.cockos.com/licecap/) to record GIFs on macOS and Windows, and [this tool](https://github.com/colinkeenan/silentcast) on Linux (ofcourse there are plenty more).

## Request a Feature

If the project doesn't do something you need or want it to do:

- Open an Issue at https://github.com/discord-modmail/modmail/issues
- Provide as much context as you can about what you're running into.
  - **Use a clear and descriptive title** for the issue to identify the suggestion.
  - **Provide a step-by-step description of the suggested enhancement** in as many details as possible.
  - **Provide specific examples to demonstrate the steps**. Include copy/paste-able snippets which you use in those examples, as [Markdown code blocks](https://help.github.com/articles/markdown-basics/#multiple-lines).
  - **Explain why this enhancement would be useful** to Modmail, and would benefit the community members.
- Please try and be clear about why existing features and alternatives would not work for you.

Once it's filed:

- The Maintainers will [label the issue](#label-issues).
- The Maintainers will evaluate the feature request, possibly asking you more questions to understand its purpose and any relevant requirements. If the issue is closed, the team will convey their reasoning and suggest an alternative path forward.
- If the feature request is accepted, it will be marked for implementation with `status: approved`, which can then be done by either by a core team member or by anyone in the community who wants to contribute code.

> **Note**: The team is unlikely to be able to accept every single feature request that is filed. Please understand if they need to say no.

## Project Setup

So you want to contribute some code! That's great! This project uses GitHub Pull Requests to manage contributions, so [read up on how to fork a GitHub project and file a PR](https://guides.github.com/activities/forking) if you've never done it before.

### Test Server and Bot Account

You will need your own test server and bot account on Discord to test your changes to the bot.

1. Create a test server.
1. Create a bot account and invite it to the server you just created.

Note down the IDs for your server, as well as any channels and roles created.
Learn how to obtain the ID of a server, channel or role **[here](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-).**

### Fork the Project

You will need your own remote (online) copy of the project repository, known as a fork.
You will do all your work in the fork rather than directly in the main repository.

You can click [here to fork][fork]

And you should be ready to go!

Once you have your fork you will need to clone the repo to your computer.

```sh
$ git clone https://github.com/<your username>/modmail
...
$ cd modmail
```

or using the [github cli](https://github.com/cli/cli):

```sh
$ gh repo clone <your username>/modmail
...
$ cd modmail
```

> Tip: You can use the github cli to fork the repo as well, just use `gh repo fork discord-modmail/modmail` and it will allow you to clone it directly.

### Install development dependencies

Make sure you are in the project directory.

```sh
# This will install the development and project dependencies.
poetry install
# This will install the pre-commit hooks.
poetry run task precommit
```

### Set up environment variables

1. Create a text file named `.env` in your project root (that's the base folder of your repository):
   - You can also copy the `.env.template` file to `.env`

> Note: The entire file name is literally `.env`

1. Open the file with any text editor.
1. Each environment variable is on its own line, with the variable and the value separated by a `=` sign.

#### The following variables are needed for running Modmail:

| Required | ENV VARIABLE NAME | TYPE    | WHAT IS IT?                                      |
| -------- | ----------------- | ------- | ------------------------------------------------ |
| True     | `TOKEN`           | String  | Bot Token from the Discord developer portal      |
| False    | `DEVELOP`         | Boolean | Enables the developer bot extensions             |
| False    | `PLUGIN_DEV`      | Boolean | Enables plugin-developer friendly bot extensions |

The rest of them can be viewed in our [.env.template](./.env.template)

### Run The Project

To run the project, use the (below) in the project root.

```shell
$ poetry run task start
```

## Contribute Code

We like code commits a lot! They're super handy, and they keep the project going and doing the work it needs to do to be useful to others.

Code contributions of just about any size are acceptable!

To contribute code:

- [Set up the project](#project-setup).
- Make any necessary changes to the source code.
- Write clear, concise commit message(s).
  - A more in-depth guide to writing great commit messages can be found in Chris Beam's [*How to Write a Git Commit Message*](https://chris.beams.io/posts/git-commit/).
- Run `flake8`, `black` and `pre-commit` against your code **before** you push. Your commit will be rejected by the build server if it fails to lint. You can run the lint by executing `poetry run task lint` in your command line.
- Go to [discord-modmail/modmail/pulls](https://github.com/discord-modmail/modmail/pulls) and open a new pull request with your changes.
- If PRing from your own fork, **ensure that "Allow edits from maintainers" is checked**. This permits maintainers to commit changes directly to your fork, speeding up the review process.
- If your PR is connected to an open issue, add a line in your PR's description that says `Closes #123`, where `#123` is the number of the issue you're fixing.

> Pull requests (or PRs for short) are the primary mechanism we use to change modmail. GitHub itself has some [great documentation][about-pull-requests] on using the Pull Request feature. We use the "fork and pull" model [described here][development-models], where contributors push changes to their personal fork and create pull requests to bring those changes into the source repository.

Once you've filed the PR:

- Barring special circumstances, maintainers will not review PRs until lint checks pass (`poetry run task lint`).
- One or more contributors will use GitHub's review feature to review your PR.
- If the maintainer asks for any changes, edit your changes, push, and ask for another review.
- If the maintainer decides to pass on your PR, they will thank you for the contribution and explain why they won't be accepting the changes. That's ok! We still really appreciate you taking the time to do it, and we don't take that lightly. 💚
- If your PR gets accepted, it will be marked as such, and merged into the `main` branch soon after.

## Git Commit Messages

Commit messages must start with a short summary (max. 50 chars)
written in the imperative, followed by an optional, more detailed explanatory
text which is separated from the summary by an empty line.

Commit messages should follow best practices, including explaining the context
of the problem and how it was solved, including caveats or follow up changes
required. They should tell the story of the change and provide readers
understanding of what led to it.

Check out [Conventional commits](https://www.conventionalcommits.org/en/v1.0.0/#summary) for more information.

If you're lost about what this even means, please see [How to Write a Git
Commit Message](http://chris.beams.io/posts/git-commit/) for a start.

In practice, the best approach to maintaining a nice commit message is to
leverage a `git add -p` and `git commit --amend` to formulate a solid
changeset. This allows one to piece together a change, as information becomes
available.

If you squash a series of commits, don't just submit that. Re-write the commit
message, as if the series of commits was a single stroke of brilliance.

That said, there is no requirement to have a single commit for a PR, as long as
each commit tells the story. For example, if there is a feature that requires a
package, it might make sense to have the package in a separate commit then have
a subsequent commit that uses it.

Remember, you're telling part of the story with the commit message. Don't make
your chapter weird.

## Python Styleguide

<!-- TODO: ... -->

## Attribution

This contributing guide is inspired by the [Moby's](https://github.com/moby/moby) and [Atom Text Editor's](https://github.com/atom/atom) contributing guide.

[about-pull-requests]: https://help.github.com/articles/about-pull-requests/
[development-models]: https://help.github.com/articles/about-collaborative-development-models/
[fork]: https://github.com/discord-modmail/modmail/fork
