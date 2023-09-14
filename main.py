import random
import settings
import discord
from discord.ext import commands
from models.account import accounts_db
from models.account import Account

logger = settings.logging.getLogger("bot")


def run():
    accounts_db.create_tables([Account])
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        logger.info(f"User: {bot.user} (ID: {bot.user.id})")
        print("_________")
        for cmd_file in settings.CMDS_DIR.glob("*.py"):
            if cmd_file.name != "__init.py__":
                await bot.load_extension(f"cmds.{cmd_file.name[:-3]}")
        for cog_file in settings.COGS_DIR.glob("*.py"):
            if cog_file.name != "__init__.py":
                await bot.load_extension(f"cogs.{cog_file.name[:-3]}")

    @bot.event
    async def on_command_error(ctx, error):
        logger.info(f"Error: {type(error)}\t{error} | is being handled globally")
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Error: Missing Argument!")
        if isinstance(error, commands.errors.NotOwner):
            await ctx.send("Error: Invalid Permissions!")

    bot.run(settings.DISCORD_API_SECRET, root_logger=True)


if __name__ == "__main__":
    run()

