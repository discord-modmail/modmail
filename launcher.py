import discord
from starlette.applications import Starlette

from modmail.bot import ModmailBot
from website import main

bot = ModmailBot(intents=discord.Intents.all())

app = Starlette(
    debug=True,
    routes=main.routes,
    on_startup=[bot.nonblocking_start],
    on_shutdown=[bot.close],
)
