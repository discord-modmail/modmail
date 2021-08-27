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
