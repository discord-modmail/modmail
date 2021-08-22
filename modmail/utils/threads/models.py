import logging
from enum import IntEnum, auto
from typing import TYPE_CHECKING, Optional, Union

import discord

from modmail.utils.threads.embeds import ThreadEmbed

if TYPE_CHECKING:
    from modmail.log import ModmailLogger
logger: "ModmailLogger" = logging.getLogger(__name__)


class Target(IntEnum):
    """Targets for thread messages."""

    USER = auto()
    MODMAIL = auto()


class MessageDict(dict):
    """A dict that stores every item as a key and as a value."""

    def __setitem__(self, key: discord.Message, value: discord.Message):
        dict.__setitem__(self, key, value)
        dict.__setitem__(self, value, key)


class Ticket:
    """
    Represents a ticket.

    This class represents a ticket for Modmail.  A ticket is a way to send
    messages to a specific user.
    """

    recipient: discord.User
    thread: discord.Thread
    messages: MessageDict
    log_message: discord.Message
    close_after: Optional[int] = None
    last_sent_message: Optional[discord.Message] = None

    def __init__(self, recipient: discord.User, thread: discord.Thread):
        """
        Creates a Ticket instance.

        At least thread and user are required.
        log_message and close_after are automatically gathered from the thread object
        """
        self.thread = thread
        self.recipient = recipient
        self.log_message: Union[
            discord.Message, discord.PartialMessage
        ] = self.thread.parent.get_partial_message(self.thread.id)
        self.messages = MessageDict()
        self.close_after = self.thread.auto_archive_duration
        self.embed_creator: ThreadEmbed = ThreadEmbed()

        logger.trace(f"Created a Ticket object for recipient {recipient} with thread {thread}.")

    async def fetch_log_message(self) -> discord.Message:
        """
        Fetch the log message from the discord api.

        This ensures that log_message is not a PartialMessage, but a full discord.Message.
        """
        self.log_message = await self.thread.parent.fetch_message(self.thread.id)
        return self.log_message
