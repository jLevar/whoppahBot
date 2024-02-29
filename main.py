import discord
from discord.ext import commands

import settings
from models.account import Account
from models.account import accounts_db

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
        for cog_file in settings.COGS_DIR.glob("*.py"):
            if cog_file.name != "__init__.py":
                await bot.load_extension(f"cogs.{cog_file.name[:-3]}")
        await bot.change_presence(activity=discord.Game('!tutorial'))

    @bot.event
    async def on_command_error(ctx, error):
        logger.info(f"Error: {type(error)}\t{error} | is being handled globally")
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Error: Missing Argument!")
        if isinstance(error, commands.errors.NotOwner):
            await ctx.send("Error: Invalid Permissions!")
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Cooldown expires in {error.retry_after:.3f}s")
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"Error: Unknown Command!")
        if isinstance(error, commands.errors.BadArgument):
            await ctx.send(f"Error: Invalid Argument Type")

    bot.run(settings.DISCORD_API_SECRET, root_logger=True)


if __name__ == "__main__":
    run()
