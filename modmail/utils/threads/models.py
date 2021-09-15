import logging
from enum import IntEnum, auto
from typing import TYPE_CHECKING, List, Optional, Union

import discord


if TYPE_CHECKING:
    from modmail.log import ModmailLogger
logger: "ModmailLogger" = logging.getLogger(__name__)


class Target(IntEnum):
    """Targets for thread messages."""

    USER = auto()
    MODMAIL = auto()


class MessageDict(dict):
    """
    A dict that stores only discord.Messages as pairs which can be mapped to each other.

    This is implemented by storing the ids as the keys, and the messages as the values.

    Both adding and deleting items will delete both keys,
    so the user does not have to worry about managing that.
    """

    def __setitem__(self, key: discord.Message, value: discord.Message):
        if not isinstance(key, discord.Message) or not isinstance(value, discord.Message):
            raise ValueError("key or value are not of type discord.Message")
        super().__setitem__(key.id, value)
        super().__setitem__(value.id, key)

    def __getitem__(self, key: Union[discord.Message, int]) -> discord.Message:
        return super().__getitem__(getattr(key, "id", key))

    def __delitem__(self, key: Union[discord.Message, int]) -> None:
        super().__delitem__(self.__getitem__(key).id)
        return super().__delitem__(getattr(key, "id", key))


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
    last_sent_messages: List[discord.Message] = list()
    has_sent_initial_message: bool

    def __init__(
        self, recipient: discord.User, thread: discord.Thread, *, has_sent_initial_message: bool = True
    ):
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
        self.has_sent_initial_message = has_sent_initial_message

        logger.trace(f"Created a Ticket object for recipient {recipient} with thread {thread}.")

    async def fetch_log_message(self) -> discord.Message:
        """
        Fetch the log message from the discord api.

        This ensures that log_message is not a PartialMessage, but a full discord.Message.
        """
        self.log_message = await self.thread.parent.fetch_message(self.thread.id)
        return self.log_message
