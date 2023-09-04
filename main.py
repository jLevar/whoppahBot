import settings
import discord
from discord.ext import commands

logger = settings.logging.getLogger("bot")


def run():
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        logger.info(f"User: {bot.user} (ID: {bot.user.id})")
        print("_________")

    @bot.command(
        aliases=['p'],
        help="To use ping, simply type !ping or !p",
        description="When pinged, the bot will respond with a pong",
        brief="Responds with pong",
        enabled=True
    )
    async def ping(ctx):
        await ctx.send("pong")

    @bot.command()
    async def joke(ctx):
        await ctx.send("<dev>Insert joke here")

    bot.run(settings.DISCORD_API_SECRET, root_logger=True)


if __name__ == "__main__":
    run()
