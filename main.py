import discord
from starlette.applications import Starlette

from modmail.bot import ModmailBot
from website import site

bot = ModmailBot(intents=discord.Intents.all())

app = Starlette(
    debug=True,
    routes=site.routes,
    on_startup=[bot.nonblocking_start],
    on_shutdown=[bot.close],
)
