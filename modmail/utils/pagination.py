import logging
import typing as t

import discord
import dislash
from discord.ext.commands import Context, Paginator
from dislash import ActionRow, Button, ButtonStyle, ClickListener

from modmail.log import ModmailLogger

JUMP_FIRST_EMOJI = "\u23EE"  # [:track_previous:]
BACK_EMOJI = "\u2B05"  # [:arrow_left:]
FORWARD_EMOJI = "\u27A1"  # [:arrow_right:]
JUMP_LAST_EMOJI = "\u23ED"  # [:track_next:]
STOP_PAGINATE_EMOJI = "\u274c"  # [:x:]

logger: ModmailLogger = logging.getLogger(__name__)
ephermals = True


class ButtonPaginator(Paginator):
    """A paginator that has a set of buttons to jump to other pages."""

    def __init__(self, prefix: str = "", suffix: str = "", max_size: int = 4000, linesep: str = "\n"):
        logger.trace("Created a paginator in __init__.")
        self.prefix = prefix
        self.suffix = suffix
        self.max_size = max_size
        self.linesep = linesep
        self.clear()

    @classmethod
    async def paginate(
        cls, ctx: Context, lines: t.List[str], *, embed: discord.Embed = None, starting_page: int = 0
    ) -> None:
        """Paginate the entries into pages."""
        paginator = cls()
        if embed is not None:
            paginator.embed = embed
        else:
            paginator.embed = discord.Embed()
        logger.trace("Created a paginator.")

        # add provided lines to the paginator
        for line in lines:
            # TODO: Handle errors when the a runtime error is raised
            paginator.add_line(line)

        row = ActionRow(
            Button(style=ButtonStyle.blurple, emoji=JUMP_FIRST_EMOJI, label="", custom_id="jump_to_first"),
            Button(style=ButtonStyle.blurple, emoji=BACK_EMOJI, label="", custom_id="prev_page"),
            Button(style=ButtonStyle.blurple, emoji=FORWARD_EMOJI, label="", custom_id="next_page"),
            Button(style=ButtonStyle.blurple, emoji=JUMP_LAST_EMOJI, label="", custom_id="jump_to_last"),
            Button(style=ButtonStyle.gray, emoji=STOP_PAGINATE_EMOJI, label="", custom_id="stop_pagination"),
        )
        logger.trace("Created an action row")

        if len(paginator.pages) <= 2:
            # disable buttons to jump pages since there are only two pages
            row.disable_buttons(0, 3)
            logger.trace("Disabled jump buttons")

        paginator.embed.description = paginator.pages[starting_page]

        if len(paginator.pages) == 1:
            logger.debug("Sending without pagination as its only one page.")
            try:
                msg = await ctx.send(embeds=[paginator.embed])
            except Exception as e:
                print(e)
                logger.error("Failed to send message to channel.", exc_info=True)
        else:
            msg = await ctx.send(embeds=[paginator.embed], components=[row])

        # Time out pagination after 180 seconds
        # This will fire an event at the end of the listener
        # and allow us to edit the message to delete the interactions
        on_click: ClickListener = msg.create_click_listener(timeout=180)

        # @on_click.from_user(ctx.author, cancel_others=True)
        @on_click.matching_id("jump_to_first", cancel_others=True)
        async def _jump_to_first(inter: dislash.MessageInteraction) -> None:
            logger.debug("_jump_to_first")
            await inter.reply(content=inter.button.custom_id, ephemeral=ephermals)

        @on_click.matching_id("prev_page", cancel_others=True)
        # @on_click.from_user(ctx.author, cancel_others=True)
        async def _prev_page(inter: dislash.MessageInteraction) -> None:
            logger.debug("_prev_page")
            await inter.reply(content=inter.button.custom_id, ephemeral=ephermals)

        # @on_click.from_user(ctx.author, cancel_others=True)
        @on_click.matching_id("next_page", cancel_others=True)
        async def _next_page(inter: dislash.MessageInteraction) -> None:
            logger.debug("_next_page")
            await inter.reply(content=inter.button.custom_id, ephemeral=ephermals)

        # @on_click.from_user(ctx.author, cancel_others=True)
        @on_click.matching_id("jump_to_last", cancel_others=True)
        async def _jump_to_last(inter: dislash.MessageInteraction) -> None:
            logger.debug("_jump_to_last")
            await inter.reply(content=inter.button.custom_id, ephemeral=ephermals)

        @on_click.timeout
        async def on_timeout() -> None:
            # remove all components once we stop listening
            await msg.edit(components=[])

        # @on_click.from_user(ctx.author)
        @on_click.matching_id("stop_pagination", cancel_others=True)
        async def drop_pagnation(inter: dislash.MessageInteraction) -> None:
            logger.debug("drop_pagnation")
            await msg.edit(components=[])
