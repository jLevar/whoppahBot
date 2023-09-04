import random
import settings
import discord
from discord.ext import commands

logger = settings.logging.getLogger("bot")


class Slapper(commands.Converter):

    def __init__(self, *, use_nicknames) -> None:
        self.use_nicknames = use_nicknames

    async def convert(self, ctx, argument):
        someone = random.choice(ctx.guild.members)
        name = ctx.author
        if self.use_nicknames:
            name = ctx.author.nick
        return f"{name} slaps {someone} with {argument}"


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

    @bot.command()
    async def say(ctx, *what):
        if what == ():
            await ctx.send("Error: Command \"say\" requires a nonzero amount of arguments")
        else:
            await ctx.send(" ".join(what))

    # IMPROPER ERROR HANDLING
    @bot.command()
    async def add(ctx, a: int, b: int):
        await ctx.send(a + b)

    @bot.command()
    async def joined(ctx, who: discord.Member):
        await ctx.send(who.joined_at)

    @bot.command()
    async def slap(ctx, reason: Slapper(use_nicknames=True)):
        await ctx.send(reason)

    bot.run(settings.DISCORD_API_SECRET, root_logger=True)


if __name__ == "__main__":
    run()
