from discord import Embed, Message


class ThreadEmbed:
    """Create embeds for threads."""

    @staticmethod
    def _create_generic_embed_to_user(message: Message, **kwargs) -> Embed:
        """
        Create a generic discord embed object to be sent to the user.

        This contains configuration and special types which should be in nearly all embed creation methods.
        """
        raise NotImplementedError

    @staticmethod
    def _create_generic_embed_to_guild(message: Message, **kwargs) -> Embed:
        """
        Create a generic discord embed object to be sent to the guild.

        This contains configuration and special types which should be in nearly all embed creation methods.
        """
        raise NotImplementedError

    @staticmethod
    def create_inital_embed_to_user(message: Message, **kwargs) -> Embed:
        """Create a discord embed object to be sent to the user in reply to their inital dm."""
        raise NotImplementedError

    @staticmethod
    def create_inital_embed_to_guild(message: Message, **kwargs) -> Embed:
        """
        Create a discord embed object to be sent to the guild on inital dm.

        This is used in the relay_channel, in order to share that there is a new ticket.
        """
        return Embed(author=message.author, description=message.content)

    @staticmethod
    def create_message_embed_to_user(
        message: Message,
        contents: str,
        **kwargs,
    ) -> Embed:
        """Given information, return an embed to be sent to the user."""
        return Embed(
            description=contents,
            timestamp=message.created_at,
            color=message.author.color,
            author=message.author,
            **kwargs,
        )

    @staticmethod
    def create_message_embed_to_guild(message: Message, **kwargs) -> Embed:
        """Given information, return an embed object to be sent to the server."""
        return Embed(
            title=f"{message.author.name}#{message.author.discriminator}({message.author.id})",
            description=str(f"{message.content}"),
            author=message.author,
            timestamp=message.created_at,
            footer_text=f"Message ID: {message.id}",
            **kwargs,
        )

    @staticmethod
    def create_edited_message_embed_to_user(message: Message, **kwargs) -> Embed:
        """Creates a new embed from an edited message by staff, to be sent to the end user."""
        raise NotImplementedError

    @staticmethod
    def create_edited_message_embed_to_guild(message: Message, **kwargs) -> Embed:
        """Creates a new embed to be sent in guild from an edited message."""
        raise NotImplementedError

    @staticmethod
    def create_close_embed_to_user(message: Message, **kwargs) -> Embed:
        """Create a discord embed object to be sent to the user on thread close."""
        raise NotImplementedError

    @staticmethod
    def create_close_embed_to_guild(message: Message, **kwargs) -> Embed:
        """Create a discord embed object to be sent to the guild on thread close."""
        raise NotImplementedError