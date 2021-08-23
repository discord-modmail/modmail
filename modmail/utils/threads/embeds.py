from __future__ import annotations

from discord import Embed, Guild, Message, User


class ThreadEmbed:
    """Create embeds for tickets."""

    def _create_generic_embed_to_user(self, message: Message, **kwargs) -> Embed:
        """
        Create a generic discord embed object to be sent to the user.

        This contains configuration and special types which should be in nearly all embed creation methods.
        """
        raise NotImplementedError

    def _create_generic_embed_to_guild(self, message: Message, **kwargs) -> Embed:
        """
        Create a generic discord embed object to be sent to the guild.

        This contains configuration and special types which should be in nearly all embed creation methods.
        """
        raise NotImplementedError

    def create_inital_embed_to_user(self, message: Message, guild: Guild, **kwargs) -> Embed:
        """Create a discord embed object to be sent to the user in reply to their inital dm."""
        return Embed(
            title="Ticket Opened",
            description=f"Thanks for dming {guild.name}! A member of our staff will be with you shortly!",
            timestamp=message.created_at,
        )

    def create_inital_embed_to_guild(
        self, message: Message, content: str = None, was_command: bool = False, user: User = None, **kwargs
    ) -> Embed:
        """
        Create a discord embed object to be sent to the guild on inital dm.

        This is used in the relay_channel, in order to share that there is a new ticket.
        """
        if was_command:
            # ticket was created by a command, which means the message is a staff message
            return Embed(author=user, description=content)
        return Embed(author=message.author, description=message.content)

    def create_message_embed_to_user(self, message: Message, contents: str, author: User = None) -> Embed:
        """Given information, return an embed to be sent to the user."""
        if author is None:
            author = message.author
        return Embed(description=contents, timestamp=message.created_at, color=author.color, author=author)

    def create_message_embed_to_guild(self, message: Message, **kwargs) -> Embed:
        """Given information, return an embed object to be sent to the server."""
        return Embed(
            title=f"{message.author.name}#{message.author.discriminator}({message.author.id})",
            description=str(f"{message.content}"),
            author=message.author,
            timestamp=message.created_at,
            footer_text=f"Message ID: {message.id}",
            **kwargs,
        )

    def create_edited_message_embed_to_user(self, new_content: str, original_message: Message) -> Embed:
        """Creates a new embed from an edited message by staff, to be sent to the end user."""
        embed = original_message.embeds[0]
        embed.description = new_content
        return embed

    def create_edited_message_embed_to_guild(self, new_content: str, original_message: Message) -> Embed:
        """Creates a new embed to be sent in guild from an edited message."""
        embed = original_message.embeds[0]
        embed.description = new_content
        return embed

    def create_close_embed_to_user(self, message: Message, **kwargs) -> Embed:
        """Create a discord embed object to be sent to the user on thread close."""
        raise NotImplementedError

    def create_close_embed_to_guild(self, message: Message, **kwargs) -> Embed:
        """Create a discord embed object to be sent to the guild on thread close."""
        raise NotImplementedError
