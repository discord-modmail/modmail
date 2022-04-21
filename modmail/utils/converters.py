import discord


class BetterPartialEmojiConverter(discord.ext.commands.converter.EmojiConverter):
    """
    Converts to a :class:`~discord.PartialEmoji`.

    This is done by extracting the animated flag, name and ID from the emoji.
    """

    async def convert(self, _: discord.ext.commands.context.Context, argument: str) -> discord.PartialEmoji:
        """Convert a provided argument into an emoji object."""
        match = discord.PartialEmoji._CUSTOM_EMOJI_RE.match(argument)
        if match is not None:
            groups = match.groupdict()
            animated = bool(groups["animated"])
            emoji_id = int(groups["id"])
            name = groups["name"]
            return discord.PartialEmoji(name=name, animated=animated, id=emoji_id)

        return discord.PartialEmoji(name=argument)
