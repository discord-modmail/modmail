# tests.test_bot

Test modmail basics.

- import module
- create a bot object

##
### test_bot_creation
Create discord bot.

**Markers:**
- asyncio
- dependency  (name=create_bot)
### test_bot_aiohttp
Test aiohttp client session creates and closes without warnings.

**Markers:**
- asyncio
- dependency  (depends=['create_bot'])
### test_bot_close
Close bot.

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
Import logging from modmail.log.

**Markers:**
- dependency  (name=create_logger)
### test_notice_level
Test notice logging level.

**Markers:**
- dependency  (depends=['create_logger'])
### test_trace_level
Test trace logging level.

**Markers:**
- skip
- dependency  (depends=['create_logger'])
