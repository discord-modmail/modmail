# tests.test_bot

Test modmail basics.

- import module
- create a bot object

##
### test_bot_creation
Ensure we can make a ModmailBot instance.

**Markers:**
- asyncio
- dependency  (name=create_bot)
### test_bot_close
Ensure bot closes without error.

**Markers:**
- asyncio
- dependency  (depends=['create_bot'])
### test_bot_main
Import modmail.__main__.

**Markers:**
- dependency  (depends=['create_bot'])
# tests.test_logs
##
### test_create_logging
Modmail logging is importable and sets root logger correctly.

**Markers:**
- dependency  (name=create_logger)
### test_notice_level
Test notice logging level prints a notice response.

**Markers:**
- dependency  (depends=['create_logger'])
### test_trace_level
Test trace logging level prints a trace response.

**Markers:**
- skip
- dependency  (depends=['create_logger'])
# tests.modmail.utils.test_embeds
##
### test_patch_embed
Ensure that the function changes init only after the patch is called.

**Markers:**
- dependency  (name=patch_embed)
### test_create_embed
Test creating an embed with patched parameters works properly.

**Markers:**
- dependency  (depends_on=patch_embed)
### test_create_embed_with_extra_params
Test creating an embed with extra parameters errors properly.

**Markers:**
- dependency  (depends_on=patch_embed)
### test_create_embed_with_description_and_content

    Create an embed while providing both description and content parameters.

    Providing both is ambiguous and should error.


**Markers:**
- dependency  (depends_on=patch_embed)
# tests.modmail.utils.addons.test_converters
##
### test_converter
Convert a user input into a Source.

**Markers:**
- xfail  (reason=Not implemented)
- skip
### test_repo_regex
Test the repo regex to ensure that it matches what it should.

**Markers:**
- parametrize (entry, user, repo, addon, reflike, githost[('onerandomusername/addons planet', 'onerandomusername', 'addons', 'planet', None, None), ('github onerandomusername/addons planet @master', 'onerandomusername', 'addons', 'planet', 'master', 'github'), ('gitlab onerandomusername/repo planet @v1.0.2', 'onerandomusername', 'repo', 'planet', 'v1.0.2', 'gitlab'), ('github onerandomusername/repo planet @master', 'onerandomusername', 'repo', 'planet', 'master', 'github'), ('gitlab onerandomusername/repo planet @main', 'onerandomusername', 'repo', 'planet', 'main', 'gitlab'), ('https://github.com/onerandomusername/repo planet', 'onerandomusername', 'repo', 'planet', None, 'github'), ('https://gitlab.com/onerandomusername/repo planet', 'onerandomusername', 'repo', 'planet', None, 'gitlab'), ('https://github.com/psf/black black @21.70b', 'psf', 'black', 'black', '21.70b', 'github')])
### test_repo_regex
Test the repo regex to ensure that it matches what it should.

**Markers:**
- parametrize (entry, user, repo, addon, reflike, githost[('onerandomusername/addons planet', 'onerandomusername', 'addons', 'planet', None, None), ('github onerandomusername/addons planet @master', 'onerandomusername', 'addons', 'planet', 'master', 'github'), ('gitlab onerandomusername/repo planet @v1.0.2', 'onerandomusername', 'repo', 'planet', 'v1.0.2', 'gitlab'), ('github onerandomusername/repo planet @master', 'onerandomusername', 'repo', 'planet', 'master', 'github'), ('gitlab onerandomusername/repo planet @main', 'onerandomusername', 'repo', 'planet', 'main', 'gitlab'), ('https://github.com/onerandomusername/repo planet', 'onerandomusername', 'repo', 'planet', None, 'github'), ('https://gitlab.com/onerandomusername/repo planet', 'onerandomusername', 'repo', 'planet', None, 'gitlab'), ('https://github.com/psf/black black @21.70b', 'psf', 'black', 'black', '21.70b', 'github')])
### test_repo_regex
Test the repo regex to ensure that it matches what it should.

**Markers:**
- parametrize (entry, user, repo, addon, reflike, githost[('onerandomusername/addons planet', 'onerandomusername', 'addons', 'planet', None, None), ('github onerandomusername/addons planet @master', 'onerandomusername', 'addons', 'planet', 'master', 'github'), ('gitlab onerandomusername/repo planet @v1.0.2', 'onerandomusername', 'repo', 'planet', 'v1.0.2', 'gitlab'), ('github onerandomusername/repo planet @master', 'onerandomusername', 'repo', 'planet', 'master', 'github'), ('gitlab onerandomusername/repo planet @main', 'onerandomusername', 'repo', 'planet', 'main', 'gitlab'), ('https://github.com/onerandomusername/repo planet', 'onerandomusername', 'repo', 'planet', None, 'github'), ('https://gitlab.com/onerandomusername/repo planet', 'onerandomusername', 'repo', 'planet', None, 'gitlab'), ('https://github.com/psf/black black @21.70b', 'psf', 'black', 'black', '21.70b', 'github')])
### test_repo_regex
Test the repo regex to ensure that it matches what it should.

**Markers:**
- parametrize (entry, user, repo, addon, reflike, githost[('onerandomusername/addons planet', 'onerandomusername', 'addons', 'planet', None, None), ('github onerandomusername/addons planet @master', 'onerandomusername', 'addons', 'planet', 'master', 'github'), ('gitlab onerandomusername/repo planet @v1.0.2', 'onerandomusername', 'repo', 'planet', 'v1.0.2', 'gitlab'), ('github onerandomusername/repo planet @master', 'onerandomusername', 'repo', 'planet', 'master', 'github'), ('gitlab onerandomusername/repo planet @main', 'onerandomusername', 'repo', 'planet', 'main', 'gitlab'), ('https://github.com/onerandomusername/repo planet', 'onerandomusername', 'repo', 'planet', None, 'github'), ('https://gitlab.com/onerandomusername/repo planet', 'onerandomusername', 'repo', 'planet', None, 'gitlab'), ('https://github.com/psf/black black @21.70b', 'psf', 'black', 'black', '21.70b', 'github')])
### test_repo_regex
Test the repo regex to ensure that it matches what it should.

**Markers:**
- parametrize (entry, user, repo, addon, reflike, githost[('onerandomusername/addons planet', 'onerandomusername', 'addons', 'planet', None, None), ('github onerandomusername/addons planet @master', 'onerandomusername', 'addons', 'planet', 'master', 'github'), ('gitlab onerandomusername/repo planet @v1.0.2', 'onerandomusername', 'repo', 'planet', 'v1.0.2', 'gitlab'), ('github onerandomusername/repo planet @master', 'onerandomusername', 'repo', 'planet', 'master', 'github'), ('gitlab onerandomusername/repo planet @main', 'onerandomusername', 'repo', 'planet', 'main', 'gitlab'), ('https://github.com/onerandomusername/repo planet', 'onerandomusername', 'repo', 'planet', None, 'github'), ('https://gitlab.com/onerandomusername/repo planet', 'onerandomusername', 'repo', 'planet', None, 'gitlab'), ('https://github.com/psf/black black @21.70b', 'psf', 'black', 'black', '21.70b', 'github')])
### test_repo_regex
Test the repo regex to ensure that it matches what it should.

**Markers:**
- parametrize (entry, user, repo, addon, reflike, githost[('onerandomusername/addons planet', 'onerandomusername', 'addons', 'planet', None, None), ('github onerandomusername/addons planet @master', 'onerandomusername', 'addons', 'planet', 'master', 'github'), ('gitlab onerandomusername/repo planet @v1.0.2', 'onerandomusername', 'repo', 'planet', 'v1.0.2', 'gitlab'), ('github onerandomusername/repo planet @master', 'onerandomusername', 'repo', 'planet', 'master', 'github'), ('gitlab onerandomusername/repo planet @main', 'onerandomusername', 'repo', 'planet', 'main', 'gitlab'), ('https://github.com/onerandomusername/repo planet', 'onerandomusername', 'repo', 'planet', None, 'github'), ('https://gitlab.com/onerandomusername/repo planet', 'onerandomusername', 'repo', 'planet', None, 'gitlab'), ('https://github.com/psf/black black @21.70b', 'psf', 'black', 'black', '21.70b', 'github')])
### test_repo_regex
Test the repo regex to ensure that it matches what it should.

**Markers:**
- parametrize (entry, user, repo, addon, reflike, githost[('onerandomusername/addons planet', 'onerandomusername', 'addons', 'planet', None, None), ('github onerandomusername/addons planet @master', 'onerandomusername', 'addons', 'planet', 'master', 'github'), ('gitlab onerandomusername/repo planet @v1.0.2', 'onerandomusername', 'repo', 'planet', 'v1.0.2', 'gitlab'), ('github onerandomusername/repo planet @master', 'onerandomusername', 'repo', 'planet', 'master', 'github'), ('gitlab onerandomusername/repo planet @main', 'onerandomusername', 'repo', 'planet', 'main', 'gitlab'), ('https://github.com/onerandomusername/repo planet', 'onerandomusername', 'repo', 'planet', None, 'github'), ('https://gitlab.com/onerandomusername/repo planet', 'onerandomusername', 'repo', 'planet', None, 'gitlab'), ('https://github.com/psf/black black @21.70b', 'psf', 'black', 'black', '21.70b', 'github')])
### test_repo_regex
Test the repo regex to ensure that it matches what it should.

**Markers:**
- parametrize (entry, user, repo, addon, reflike, githost[('onerandomusername/addons planet', 'onerandomusername', 'addons', 'planet', None, None), ('github onerandomusername/addons planet @master', 'onerandomusername', 'addons', 'planet', 'master', 'github'), ('gitlab onerandomusername/repo planet @v1.0.2', 'onerandomusername', 'repo', 'planet', 'v1.0.2', 'gitlab'), ('github onerandomusername/repo planet @master', 'onerandomusername', 'repo', 'planet', 'master', 'github'), ('gitlab onerandomusername/repo planet @main', 'onerandomusername', 'repo', 'planet', 'main', 'gitlab'), ('https://github.com/onerandomusername/repo planet', 'onerandomusername', 'repo', 'planet', None, 'github'), ('https://gitlab.com/onerandomusername/repo planet', 'onerandomusername', 'repo', 'planet', None, 'gitlab'), ('https://github.com/psf/black black @21.70b', 'psf', 'black', 'black', '21.70b', 'github')])
### test_zip_regex
Test the repo regex to ensure that it matches what it should.

**Markers:**
- parametrize (entry, url, domain, path, addon[('https://github.com/onerandomusername/modmail-addons/archive/main.zip planet', 'github.com/onerandomusername/modmail-addons/archive/main.zip', 'github.com', 'onerandomusername/modmail-addons/archive/main.zip', 'planet'), ('https://gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip earth', 'gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'gitlab.com', 'onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'earth'), ('https://example.com/bleeeep.zip myanmar', 'example.com/bleeeep.zip', 'example.com', 'bleeeep.zip', 'myanmar'), ('http://github.com/discord-modmail/addons/archive/bast.zip thebot', 'github.com/discord-modmail/addons/archive/bast.zip', 'github.com', 'discord-modmail/addons/archive/bast.zip', 'thebot'), ('rtfd.io/plugs.zip documentation', 'rtfd.io/plugs.zip', 'rtfd.io', 'plugs.zip', 'documentation'), ('pages.dev/hiy.zip black', 'pages.dev/hiy.zip', 'pages.dev', 'hiy.zip', 'black')])
### test_zip_regex
Test the repo regex to ensure that it matches what it should.

**Markers:**
- parametrize (entry, url, domain, path, addon[('https://github.com/onerandomusername/modmail-addons/archive/main.zip planet', 'github.com/onerandomusername/modmail-addons/archive/main.zip', 'github.com', 'onerandomusername/modmail-addons/archive/main.zip', 'planet'), ('https://gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip earth', 'gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'gitlab.com', 'onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'earth'), ('https://example.com/bleeeep.zip myanmar', 'example.com/bleeeep.zip', 'example.com', 'bleeeep.zip', 'myanmar'), ('http://github.com/discord-modmail/addons/archive/bast.zip thebot', 'github.com/discord-modmail/addons/archive/bast.zip', 'github.com', 'discord-modmail/addons/archive/bast.zip', 'thebot'), ('rtfd.io/plugs.zip documentation', 'rtfd.io/plugs.zip', 'rtfd.io', 'plugs.zip', 'documentation'), ('pages.dev/hiy.zip black', 'pages.dev/hiy.zip', 'pages.dev', 'hiy.zip', 'black')])
### test_zip_regex
Test the repo regex to ensure that it matches what it should.

**Markers:**
- parametrize (entry, url, domain, path, addon[('https://github.com/onerandomusername/modmail-addons/archive/main.zip planet', 'github.com/onerandomusername/modmail-addons/archive/main.zip', 'github.com', 'onerandomusername/modmail-addons/archive/main.zip', 'planet'), ('https://gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip earth', 'gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'gitlab.com', 'onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'earth'), ('https://example.com/bleeeep.zip myanmar', 'example.com/bleeeep.zip', 'example.com', 'bleeeep.zip', 'myanmar'), ('http://github.com/discord-modmail/addons/archive/bast.zip thebot', 'github.com/discord-modmail/addons/archive/bast.zip', 'github.com', 'discord-modmail/addons/archive/bast.zip', 'thebot'), ('rtfd.io/plugs.zip documentation', 'rtfd.io/plugs.zip', 'rtfd.io', 'plugs.zip', 'documentation'), ('pages.dev/hiy.zip black', 'pages.dev/hiy.zip', 'pages.dev', 'hiy.zip', 'black')])
### test_zip_regex
Test the repo regex to ensure that it matches what it should.

**Markers:**
- parametrize (entry, url, domain, path, addon[('https://github.com/onerandomusername/modmail-addons/archive/main.zip planet', 'github.com/onerandomusername/modmail-addons/archive/main.zip', 'github.com', 'onerandomusername/modmail-addons/archive/main.zip', 'planet'), ('https://gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip earth', 'gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'gitlab.com', 'onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'earth'), ('https://example.com/bleeeep.zip myanmar', 'example.com/bleeeep.zip', 'example.com', 'bleeeep.zip', 'myanmar'), ('http://github.com/discord-modmail/addons/archive/bast.zip thebot', 'github.com/discord-modmail/addons/archive/bast.zip', 'github.com', 'discord-modmail/addons/archive/bast.zip', 'thebot'), ('rtfd.io/plugs.zip documentation', 'rtfd.io/plugs.zip', 'rtfd.io', 'plugs.zip', 'documentation'), ('pages.dev/hiy.zip black', 'pages.dev/hiy.zip', 'pages.dev', 'hiy.zip', 'black')])
### test_zip_regex
Test the repo regex to ensure that it matches what it should.

**Markers:**
- parametrize (entry, url, domain, path, addon[('https://github.com/onerandomusername/modmail-addons/archive/main.zip planet', 'github.com/onerandomusername/modmail-addons/archive/main.zip', 'github.com', 'onerandomusername/modmail-addons/archive/main.zip', 'planet'), ('https://gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip earth', 'gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'gitlab.com', 'onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'earth'), ('https://example.com/bleeeep.zip myanmar', 'example.com/bleeeep.zip', 'example.com', 'bleeeep.zip', 'myanmar'), ('http://github.com/discord-modmail/addons/archive/bast.zip thebot', 'github.com/discord-modmail/addons/archive/bast.zip', 'github.com', 'discord-modmail/addons/archive/bast.zip', 'thebot'), ('rtfd.io/plugs.zip documentation', 'rtfd.io/plugs.zip', 'rtfd.io', 'plugs.zip', 'documentation'), ('pages.dev/hiy.zip black', 'pages.dev/hiy.zip', 'pages.dev', 'hiy.zip', 'black')])
### test_zip_regex
Test the repo regex to ensure that it matches what it should.

**Markers:**
- parametrize (entry, url, domain, path, addon[('https://github.com/onerandomusername/modmail-addons/archive/main.zip planet', 'github.com/onerandomusername/modmail-addons/archive/main.zip', 'github.com', 'onerandomusername/modmail-addons/archive/main.zip', 'planet'), ('https://gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip earth', 'gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'gitlab.com', 'onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'earth'), ('https://example.com/bleeeep.zip myanmar', 'example.com/bleeeep.zip', 'example.com', 'bleeeep.zip', 'myanmar'), ('http://github.com/discord-modmail/addons/archive/bast.zip thebot', 'github.com/discord-modmail/addons/archive/bast.zip', 'github.com', 'discord-modmail/addons/archive/bast.zip', 'thebot'), ('rtfd.io/plugs.zip documentation', 'rtfd.io/plugs.zip', 'rtfd.io', 'plugs.zip', 'documentation'), ('pages.dev/hiy.zip black', 'pages.dev/hiy.zip', 'pages.dev', 'hiy.zip', 'black')])
# tests.modmail.utils.addons.test_models
##
### test_addon_model
All addons will be of a specific type, so we should not be able to create a generic addon.
### test_addonsource_init
Test the AddonSource init sets class vars appropiately.

**Markers:**
- parametrize (zip_url, source_type[('github.com/bast0006.zip', <SourceTypeEnum.ZIP: 0>), ('gitlab.com/onerandomusername.zip', <SourceTypeEnum.REPO: 1>)])
### test_addonsource_init
Test the AddonSource init sets class vars appropiately.

**Markers:**
- parametrize (zip_url, source_type[('github.com/bast0006.zip', <SourceTypeEnum.ZIP: 0>), ('gitlab.com/onerandomusername.zip', <SourceTypeEnum.REPO: 1>)])
### test_addonsource_from_repo
Test an addon source is properly made from repository information.

**Markers:**
- parametrize (user, repo, reflike, githost[('onerandomusername', 'addons', None, 'github'), ('onerandomusername', 'addons', 'master', 'github'), ('onerandomusername', 'repo', 'v1.0.2', 'gitlab'), ('onerandomusername', 'repo', 'master', 'github'), ('onerandomusername', 'repo', 'main', 'gitlab'), ('onerandomusername', 'repo', None, 'github'), ('onerandomusername', 'repo', None, 'gitlab'), ('psf', 'black', '21.70b', 'github')])
### test_addonsource_from_repo
Test an addon source is properly made from repository information.

**Markers:**
- parametrize (user, repo, reflike, githost[('onerandomusername', 'addons', None, 'github'), ('onerandomusername', 'addons', 'master', 'github'), ('onerandomusername', 'repo', 'v1.0.2', 'gitlab'), ('onerandomusername', 'repo', 'master', 'github'), ('onerandomusername', 'repo', 'main', 'gitlab'), ('onerandomusername', 'repo', None, 'github'), ('onerandomusername', 'repo', None, 'gitlab'), ('psf', 'black', '21.70b', 'github')])
### test_addonsource_from_repo
Test an addon source is properly made from repository information.

**Markers:**
- parametrize (user, repo, reflike, githost[('onerandomusername', 'addons', None, 'github'), ('onerandomusername', 'addons', 'master', 'github'), ('onerandomusername', 'repo', 'v1.0.2', 'gitlab'), ('onerandomusername', 'repo', 'master', 'github'), ('onerandomusername', 'repo', 'main', 'gitlab'), ('onerandomusername', 'repo', None, 'github'), ('onerandomusername', 'repo', None, 'gitlab'), ('psf', 'black', '21.70b', 'github')])
### test_addonsource_from_repo
Test an addon source is properly made from repository information.

**Markers:**
- parametrize (user, repo, reflike, githost[('onerandomusername', 'addons', None, 'github'), ('onerandomusername', 'addons', 'master', 'github'), ('onerandomusername', 'repo', 'v1.0.2', 'gitlab'), ('onerandomusername', 'repo', 'master', 'github'), ('onerandomusername', 'repo', 'main', 'gitlab'), ('onerandomusername', 'repo', None, 'github'), ('onerandomusername', 'repo', None, 'gitlab'), ('psf', 'black', '21.70b', 'github')])
### test_addonsource_from_repo
Test an addon source is properly made from repository information.

**Markers:**
- parametrize (user, repo, reflike, githost[('onerandomusername', 'addons', None, 'github'), ('onerandomusername', 'addons', 'master', 'github'), ('onerandomusername', 'repo', 'v1.0.2', 'gitlab'), ('onerandomusername', 'repo', 'master', 'github'), ('onerandomusername', 'repo', 'main', 'gitlab'), ('onerandomusername', 'repo', None, 'github'), ('onerandomusername', 'repo', None, 'gitlab'), ('psf', 'black', '21.70b', 'github')])
### test_addonsource_from_repo
Test an addon source is properly made from repository information.

**Markers:**
- parametrize (user, repo, reflike, githost[('onerandomusername', 'addons', None, 'github'), ('onerandomusername', 'addons', 'master', 'github'), ('onerandomusername', 'repo', 'v1.0.2', 'gitlab'), ('onerandomusername', 'repo', 'master', 'github'), ('onerandomusername', 'repo', 'main', 'gitlab'), ('onerandomusername', 'repo', None, 'github'), ('onerandomusername', 'repo', None, 'gitlab'), ('psf', 'black', '21.70b', 'github')])
### test_addonsource_from_repo
Test an addon source is properly made from repository information.

**Markers:**
- parametrize (user, repo, reflike, githost[('onerandomusername', 'addons', None, 'github'), ('onerandomusername', 'addons', 'master', 'github'), ('onerandomusername', 'repo', 'v1.0.2', 'gitlab'), ('onerandomusername', 'repo', 'master', 'github'), ('onerandomusername', 'repo', 'main', 'gitlab'), ('onerandomusername', 'repo', None, 'github'), ('onerandomusername', 'repo', None, 'gitlab'), ('psf', 'black', '21.70b', 'github')])
### test_addonsource_from_repo
Test an addon source is properly made from repository information.

**Markers:**
- parametrize (user, repo, reflike, githost[('onerandomusername', 'addons', None, 'github'), ('onerandomusername', 'addons', 'master', 'github'), ('onerandomusername', 'repo', 'v1.0.2', 'gitlab'), ('onerandomusername', 'repo', 'master', 'github'), ('onerandomusername', 'repo', 'main', 'gitlab'), ('onerandomusername', 'repo', None, 'github'), ('onerandomusername', 'repo', None, 'gitlab'), ('psf', 'black', '21.70b', 'github')])
### test_addonsource_from_zip
Test an addon source is properly made from a zip url.

**Markers:**
- parametrize (url['github.com/onerandomusername/modmail-addons/archive/main.zip', 'gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'example.com/bleeeep.zip', 'github.com/discord-modmail/addons/archive/bast.zip', 'rtfd.io/plugs.zip', 'pages.dev/hiy.zip'])
### test_addonsource_from_zip
Test an addon source is properly made from a zip url.

**Markers:**
- parametrize (url['github.com/onerandomusername/modmail-addons/archive/main.zip', 'gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'example.com/bleeeep.zip', 'github.com/discord-modmail/addons/archive/bast.zip', 'rtfd.io/plugs.zip', 'pages.dev/hiy.zip'])
### test_addonsource_from_zip
Test an addon source is properly made from a zip url.

**Markers:**
- parametrize (url['github.com/onerandomusername/modmail-addons/archive/main.zip', 'gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'example.com/bleeeep.zip', 'github.com/discord-modmail/addons/archive/bast.zip', 'rtfd.io/plugs.zip', 'pages.dev/hiy.zip'])
### test_addonsource_from_zip
Test an addon source is properly made from a zip url.

**Markers:**
- parametrize (url['github.com/onerandomusername/modmail-addons/archive/main.zip', 'gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'example.com/bleeeep.zip', 'github.com/discord-modmail/addons/archive/bast.zip', 'rtfd.io/plugs.zip', 'pages.dev/hiy.zip'])
### test_addonsource_from_zip
Test an addon source is properly made from a zip url.

**Markers:**
- parametrize (url['github.com/onerandomusername/modmail-addons/archive/main.zip', 'gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'example.com/bleeeep.zip', 'github.com/discord-modmail/addons/archive/bast.zip', 'rtfd.io/plugs.zip', 'pages.dev/hiy.zip'])
### test_addonsource_from_zip
Test an addon source is properly made from a zip url.

**Markers:**
- parametrize (url['github.com/onerandomusername/modmail-addons/archive/main.zip', 'gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'example.com/bleeeep.zip', 'github.com/discord-modmail/addons/archive/bast.zip', 'rtfd.io/plugs.zip', 'pages.dev/hiy.zip'])
## TestPlugin
Test the Plugin class creation.
### test_plugin_init
Create a plugin model, and ensure it has the right properties.

**Markers:**
- parametrize (name['earth', 'mona-lisa'])
### test_plugin_init
Create a plugin model, and ensure it has the right properties.

**Markers:**
- parametrize (name['earth', 'mona-lisa'])
### test_plugin_from_repo_match
Test that a plugin can be created from a repo.

**Markers:**
- parametrize (user, repo, name, reflike, githost[('onerandomusername', 'addons', 'planet', None, 'github'), ('onerandomusername', 'addons', 'planet', 'master', 'github'), ('onerandomusername', 'repo', 'planet', 'v1.0.2', 'gitlab'), ('onerandomusername', 'repo', 'planet', 'master', 'github'), ('onerandomusername', 'repo', 'planet', 'main', 'gitlab'), ('onerandomusername', 'repo', 'planet', None, 'github'), ('onerandomusername', 'repo', 'planet', None, 'gitlab'), ('psf', 'black', 'black', '21.70b', 'github')])
### test_plugin_from_repo_match
Test that a plugin can be created from a repo.

**Markers:**
- parametrize (user, repo, name, reflike, githost[('onerandomusername', 'addons', 'planet', None, 'github'), ('onerandomusername', 'addons', 'planet', 'master', 'github'), ('onerandomusername', 'repo', 'planet', 'v1.0.2', 'gitlab'), ('onerandomusername', 'repo', 'planet', 'master', 'github'), ('onerandomusername', 'repo', 'planet', 'main', 'gitlab'), ('onerandomusername', 'repo', 'planet', None, 'github'), ('onerandomusername', 'repo', 'planet', None, 'gitlab'), ('psf', 'black', 'black', '21.70b', 'github')])
### test_plugin_from_repo_match
Test that a plugin can be created from a repo.

**Markers:**
- parametrize (user, repo, name, reflike, githost[('onerandomusername', 'addons', 'planet', None, 'github'), ('onerandomusername', 'addons', 'planet', 'master', 'github'), ('onerandomusername', 'repo', 'planet', 'v1.0.2', 'gitlab'), ('onerandomusername', 'repo', 'planet', 'master', 'github'), ('onerandomusername', 'repo', 'planet', 'main', 'gitlab'), ('onerandomusername', 'repo', 'planet', None, 'github'), ('onerandomusername', 'repo', 'planet', None, 'gitlab'), ('psf', 'black', 'black', '21.70b', 'github')])
### test_plugin_from_repo_match
Test that a plugin can be created from a repo.

**Markers:**
- parametrize (user, repo, name, reflike, githost[('onerandomusername', 'addons', 'planet', None, 'github'), ('onerandomusername', 'addons', 'planet', 'master', 'github'), ('onerandomusername', 'repo', 'planet', 'v1.0.2', 'gitlab'), ('onerandomusername', 'repo', 'planet', 'master', 'github'), ('onerandomusername', 'repo', 'planet', 'main', 'gitlab'), ('onerandomusername', 'repo', 'planet', None, 'github'), ('onerandomusername', 'repo', 'planet', None, 'gitlab'), ('psf', 'black', 'black', '21.70b', 'github')])
### test_plugin_from_repo_match
Test that a plugin can be created from a repo.

**Markers:**
- parametrize (user, repo, name, reflike, githost[('onerandomusername', 'addons', 'planet', None, 'github'), ('onerandomusername', 'addons', 'planet', 'master', 'github'), ('onerandomusername', 'repo', 'planet', 'v1.0.2', 'gitlab'), ('onerandomusername', 'repo', 'planet', 'master', 'github'), ('onerandomusername', 'repo', 'planet', 'main', 'gitlab'), ('onerandomusername', 'repo', 'planet', None, 'github'), ('onerandomusername', 'repo', 'planet', None, 'gitlab'), ('psf', 'black', 'black', '21.70b', 'github')])
### test_plugin_from_repo_match
Test that a plugin can be created from a repo.

**Markers:**
- parametrize (user, repo, name, reflike, githost[('onerandomusername', 'addons', 'planet', None, 'github'), ('onerandomusername', 'addons', 'planet', 'master', 'github'), ('onerandomusername', 'repo', 'planet', 'v1.0.2', 'gitlab'), ('onerandomusername', 'repo', 'planet', 'master', 'github'), ('onerandomusername', 'repo', 'planet', 'main', 'gitlab'), ('onerandomusername', 'repo', 'planet', None, 'github'), ('onerandomusername', 'repo', 'planet', None, 'gitlab'), ('psf', 'black', 'black', '21.70b', 'github')])
### test_plugin_from_repo_match
Test that a plugin can be created from a repo.

**Markers:**
- parametrize (user, repo, name, reflike, githost[('onerandomusername', 'addons', 'planet', None, 'github'), ('onerandomusername', 'addons', 'planet', 'master', 'github'), ('onerandomusername', 'repo', 'planet', 'v1.0.2', 'gitlab'), ('onerandomusername', 'repo', 'planet', 'master', 'github'), ('onerandomusername', 'repo', 'planet', 'main', 'gitlab'), ('onerandomusername', 'repo', 'planet', None, 'github'), ('onerandomusername', 'repo', 'planet', None, 'gitlab'), ('psf', 'black', 'black', '21.70b', 'github')])
### test_plugin_from_repo_match
Test that a plugin can be created from a repo.

**Markers:**
- parametrize (user, repo, name, reflike, githost[('onerandomusername', 'addons', 'planet', None, 'github'), ('onerandomusername', 'addons', 'planet', 'master', 'github'), ('onerandomusername', 'repo', 'planet', 'v1.0.2', 'gitlab'), ('onerandomusername', 'repo', 'planet', 'master', 'github'), ('onerandomusername', 'repo', 'planet', 'main', 'gitlab'), ('onerandomusername', 'repo', 'planet', None, 'github'), ('onerandomusername', 'repo', 'planet', None, 'gitlab'), ('psf', 'black', 'black', '21.70b', 'github')])
### test_plugin_from_zip
Test that a plugin can be created from a zip url.

**Markers:**
- parametrize (url, addon[('github.com/onerandomusername/modmail-addons/archive/main.zip', 'planet'), ('gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'earth'), ('example.com/bleeeep.zip', 'myanmar'), ('github.com/discord-modmail/addons/archive/bast.zip', 'thebot'), ('rtfd.io/plugs.zip', 'documentation'), ('pages.dev/hiy.zip', 'black')])
### test_plugin_from_zip
Test that a plugin can be created from a zip url.

**Markers:**
- parametrize (url, addon[('github.com/onerandomusername/modmail-addons/archive/main.zip', 'planet'), ('gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'earth'), ('example.com/bleeeep.zip', 'myanmar'), ('github.com/discord-modmail/addons/archive/bast.zip', 'thebot'), ('rtfd.io/plugs.zip', 'documentation'), ('pages.dev/hiy.zip', 'black')])
### test_plugin_from_zip
Test that a plugin can be created from a zip url.

**Markers:**
- parametrize (url, addon[('github.com/onerandomusername/modmail-addons/archive/main.zip', 'planet'), ('gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'earth'), ('example.com/bleeeep.zip', 'myanmar'), ('github.com/discord-modmail/addons/archive/bast.zip', 'thebot'), ('rtfd.io/plugs.zip', 'documentation'), ('pages.dev/hiy.zip', 'black')])
### test_plugin_from_zip
Test that a plugin can be created from a zip url.

**Markers:**
- parametrize (url, addon[('github.com/onerandomusername/modmail-addons/archive/main.zip', 'planet'), ('gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'earth'), ('example.com/bleeeep.zip', 'myanmar'), ('github.com/discord-modmail/addons/archive/bast.zip', 'thebot'), ('rtfd.io/plugs.zip', 'documentation'), ('pages.dev/hiy.zip', 'black')])
### test_plugin_from_zip
Test that a plugin can be created from a zip url.

**Markers:**
- parametrize (url, addon[('github.com/onerandomusername/modmail-addons/archive/main.zip', 'planet'), ('gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'earth'), ('example.com/bleeeep.zip', 'myanmar'), ('github.com/discord-modmail/addons/archive/bast.zip', 'thebot'), ('rtfd.io/plugs.zip', 'documentation'), ('pages.dev/hiy.zip', 'black')])
### test_plugin_from_zip
Test that a plugin can be created from a zip url.

**Markers:**
- parametrize (url, addon[('github.com/onerandomusername/modmail-addons/archive/main.zip', 'planet'), ('gitlab.com/onerandomusername/modmail-addons/-/archive/main/modmail-addons-main.zip', 'earth'), ('example.com/bleeeep.zip', 'myanmar'), ('github.com/discord-modmail/addons/archive/bast.zip', 'thebot'), ('rtfd.io/plugs.zip', 'documentation'), ('pages.dev/hiy.zip', 'black')])
