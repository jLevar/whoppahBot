import discord
from discord.ext import commands

import settings

from models.base import db
from models.base import BaseModel
from models.account import Account

from models.assets import Assets

logger = settings.logging.getLogger("bot")


def run():
    db.connect()
    db.create_tables([Account, Assets])

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    bot = commands.Bot(command_prefix="!", intents=intents)
    BaseModel.bot = bot

    @bot.event
    async def on_ready():
        logger.info(f"User: {bot.user} (ID: {bot.user.id})")
        print("_________")
        for cog_file in settings.COGS_DIR.glob("*.py"):
            if cog_file.name != "__init__.py":
                await bot.load_extension(f"cogs.{cog_file.name[:-3]}")
        await bot.change_presence(activity=discord.Game('!help'))

    @bot.event
    async def on_command_error(ctx, error):
        logger.info(f"Error: [{type(error)}\t{error}] is being handled globally")
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("`Error: Missing Argument`", mention_author=False)
        elif isinstance(error, commands.errors.NotOwner):
            await ctx.reply("`Error: Invalid Permissions`", mention_author=False)
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(f"`Cooldown expires in {error.retry_after:.3f}s`", mention_author=False)
        elif isinstance(error, commands.CommandNotFound):
            await ctx.reply(f"`Error: Unknown Command`", mention_author=False)
        elif isinstance(error, commands.errors.BadArgument):
            await ctx.reply(f"`Error: Invalid Argument Type`", mention_author=False)
        elif isinstance(error, commands.errors.CommandInvokeError):
            await ctx.reply(f"`Error: Command Invoke Error`", mention_author=False)
        else:
            await ctx.reply(f"`Error`")

    bot.run(settings.DISCORD_API_SECRET, root_logger=True)


if __name__ == "__main__":
    run()
