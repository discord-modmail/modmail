import logging
import typing as t

import discord
import dislash
from discord.ext.commands import Context, Paginator
from dislash import ActionRow, Button, ButtonStyle, ClickListener, ResponseType

from modmail.log import ModmailLogger

JUMP_FIRST_EMOJI = "\u23EE"  # [:track_previous:]
BACK_EMOJI = "\u2B05"  # [:arrow_left:]
FORWARD_EMOJI = "\u27A1"  # [:arrow_right:]
JUMP_LAST_EMOJI = "\u23ED"  # [:track_next:]
STOP_PAGINATE_EMOJI = "\u274c"  # [:x:]

logger: ModmailLogger = logging.getLogger(__name__)
ephermals = False


class ButtonPaginator(Paginator):
    """A paginator that has a set of buttons to jump to other pages."""

    def __init__(self, prefix: str = "", suffix: str = "", max_size: int = 300, linesep: str = "\n"):
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
        paginator.current_page = starting_page
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
            new_page = 0
            logger.trace(new_page >= 0)
            if new_page >= 0:
                paginator.embed.description = paginator.pages[new_page]
                paginator.current_page -= 1
                paginator.embed.set_footer(text=f"Page {new_page + 1}/{len(paginator.pages)}")
                await msg.edit(embeds=[paginator.embed], components=[row])
                await inter.reply(type=ResponseType.DeferredUpdateMessage)
            else:
                # page is out of range
                await inter.reply(content="You're at the first page!", ephemeral=True)

        @on_click.matching_id("prev_page", cancel_others=True)
        # @on_click.from_user(ctx.author, cancel_others=True)
        async def _prev_page(inter: dislash.MessageInteraction) -> None:
            logger.debug("_prev_page")
            new_page = paginator.current_page - 1
            logger.trace(new_page >= 0)
            if new_page >= 0:
                paginator.embed.description = paginator.pages[new_page]
                paginator.current_page -= 1
                paginator.embed.set_footer(text=f"Page {new_page + 1}/{len(paginator.pages)}")
                await msg.edit(embeds=[paginator.embed], components=[row])
                await inter.reply(type=ResponseType.DeferredUpdateMessage)
            else:
                # page is out of range
                await inter.reply(content="You're at the first page!", ephemeral=True)

        # @on_click.from_user(ctx.author, cancel_others=True)
        @on_click.matching_id("next_page", cancel_others=True)
        async def _next_page(inter: dislash.MessageInteraction) -> None:
            logger.debug("_next_page")
            logger.trace(paginator.current_page + 1 < len(paginator.pages))
            if paginator.current_page + 1 < len(paginator.pages):
                paginator.embed.description = paginator.pages[paginator.current_page + 1]
                paginator.current_page += 1
                paginator.embed.set_footer(text=f"Page {paginator.current_page + 1}/{len(paginator.pages)}")
                await msg.edit(embeds=[paginator.embed], components=[row])
                await inter.reply(type=ResponseType.DeferredUpdateMessage)
            else:
                # page is out of range
                await inter.reply(content=f"There's only {len(paginator.pages)} pages!", ephemeral=True)

        # @on_click.from_user(ctx.author, cancel_others=True)
        @on_click.matching_id("jump_to_last", cancel_others=True)
        async def _jump_to_last(inter: dislash.MessageInteraction) -> None:
            logger.debug("_jump_to_last")
            new_page = len(paginator.pages) - 1
            logger.trace(len(paginator.pages))
            if new_page < len(paginator.pages):
                await inter.reply(type=ResponseType.DeferredUpdateMessage)
                paginator.embed.description = paginator.pages[new_page]
                paginator.current_page = new_page
                paginator.embed.set_footer(text=f"Page {new_page + 1}/{len(paginator.pages)}")
                await msg.edit(embeds=[paginator.embed], components=[row])
            else:
                # page is out of range
                await inter.reply(content=f"There's only {len(paginator.pages)} pages!", ephemeral=True)

        @on_click.timeout
        async def on_timeout() -> None:
            # remove all components once we stop listening
            await msg.edit(components=[])

        # @on_click.from_user(ctx.author)
        @on_click.matching_id("stop_pagination", cancel_others=True)
        async def drop_pagnation(inter: dislash.MessageInteraction) -> None:
            logger.debug("drop_pagnation")
            await msg.edit(components=[])
